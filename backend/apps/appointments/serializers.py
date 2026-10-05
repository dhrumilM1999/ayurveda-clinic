from django.utils import timezone
from rest_framework import serializers

from apps.accounts.services import doctors_in_branch
from apps.common.utils import mask_phone

from .models import Appointment
from .services import patient_has_active_appointment, slot_end


def patient_summary(patient) -> dict:
    """The few patient details an appointment list needs (phone masked)."""
    return {
        "id": str(patient.id),
        "uhid": patient.uhid,
        "full_name": patient.full_name,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "gender": patient.gender,
        "age_years": patient.age_years,
        "mobile_masked": mask_phone(patient.mobile),
        "is_vip": patient.is_vip,
    }


class OpdBillFieldMixin:
    """Adds `opd_bill` (short OPD bill status) for staff who may see or make bills."""

    def _can_see_bills(self) -> bool:
        if "can_see_bills" not in self.context:
            from apps.accounts.services import user_has_perm

            request, branch = self.context.get("request"), self.context.get("branch")
            self.context["can_see_bills"] = bool(request and branch and any(
                user_has_perm(request.user, code, branch) for code in ("billing.view", "billing.charge")))
        return self.context["can_see_bills"]

    def get_opd_bill(self, obj):
        if not obj.pk or not self._can_see_bills():
            return None
        from apps.billing.opd import opd_bill_summary

        return opd_bill_summary(obj)


class AppointmentSerializer(OpdBillFieldMixin, serializers.ModelSerializer):
    patient_detail = serializers.SerializerMethodField()
    # Short OPD bill status (only for staff who may see or make bills)
    opd_bill = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id", "patient", "patient_detail", "doctor", "doctor_name", "branch", "branch_name",
            "date", "start_time", "end_time", "kind", "status", "token_number", "reason", "notes",
            "checked_in_at", "consultation_started_at", "completed_at", "cancelled_at", "cancel_reason",
            "reschedule_count", "created_at", "opd_bill",
        ]
        read_only_fields = [
            "id", "branch", "end_time", "status", "token_number", "checked_in_at",
            "consultation_started_at", "completed_at", "cancelled_at", "cancel_reason",
            "reschedule_count", "created_at",
        ]
        extra_kwargs = {"date": {"required": False}}

    def get_patient_detail(self, obj):
        return patient_summary(obj.patient)


    def validate_patient(self, value):
        if value.organization_id != self.context["request"].user.organization_id:
            raise serializers.ValidationError("Patient not found.")
        return value

    def validate_doctor(self, value):
        branch = self.context["branch"]
        if not doctors_in_branch(branch).filter(pk=value.pk).exists():
            raise serializers.ValidationError("This doctor does not work in this branch.")
        return value

    def validate(self, attrs):
        if self.instance is not None:
            # Editing only changes reason/notes. Date and time change through "reschedule".
            return {k: v for k, v in attrs.items() if k in ("reason", "notes")}
        branch = self.context["branch"]
        today = timezone.localdate()
        kind = attrs.get("kind", "booked")
        if kind == "walk_in":
            # A walk-in is always for today and has no fixed time.
            attrs["date"] = today
            attrs["start_time"] = None
        else:
            day = attrs.get("date")
            start = attrs.get("start_time")
            if not day:
                raise serializers.ValidationError({"date": "Please choose a date."})
            if day < today:
                raise serializers.ValidationError({"date": "The date has already passed."})
            if not start:
                raise serializers.ValidationError({"start_time": "Please choose a time."})
            attrs["end_time"] = slot_end(branch, attrs["doctor"], day, start)
        if patient_has_active_appointment(attrs["patient"], attrs["doctor"], attrs["date"]):
            raise serializers.ValidationError(
                {"patient": "This patient already has an appointment with this doctor on this day."}
            )
        return attrs


class RescheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()

    def validate(self, attrs):
        appointment = self.context["appointment"]
        if attrs["date"] < timezone.localdate():
            raise serializers.ValidationError({"date": "The date has already passed."})
        if patient_has_active_appointment(appointment.patient, appointment.doctor, attrs["date"],
                                          exclude_id=appointment.pk):
            raise serializers.ValidationError(
                {"date": "This patient already has an appointment with this doctor on this day."}
            )
        attrs["end_time"] = slot_end(appointment.branch, appointment.doctor, attrs["date"], attrs["start_time"])
        return attrs


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)


class QueueItemSerializer(OpdBillFieldMixin, serializers.ModelSerializer):
    """One line on the queue screen. display_name is short, for the TV screen in the waiting room."""

    patient_detail = serializers.SerializerMethodField()
    opd_bill = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id", "token_number", "status", "kind", "start_time", "checked_in_at",
            "consultation_started_at", "patient_detail", "display_name", "reason", "opd_bill",
        ]

    def get_patient_detail(self, obj):
        return patient_summary(obj.patient)

    def get_display_name(self, obj):
        # Privacy on a public screen: first name + first letter of surname, e.g. "Ramesh P."
        last = obj.patient.last_name
        return f"{obj.patient.first_name} {last[0]}." if last else obj.patient.first_name

