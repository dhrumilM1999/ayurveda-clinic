from rest_framework import serializers

from apps.appointments.serializers import patient_summary
from apps.emr.models import Visit
from apps.patients.models import Patient

from .models import Certificate


class CertificateSerializer(serializers.ModelSerializer):
    patient_detail = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "id", "patient", "patient_detail", "doctor", "doctor_name", "visit", "kind", "kind_label", "number",
            "issued_on", "diagnosis", "rest_from", "rest_to", "fit_from", "remarks", "is_cancelled",
            "cancel_reason", "created_at",
        ]
        read_only_fields = ["id", "number", "issued_on", "is_cancelled", "cancel_reason", "created_at"]

    def get_patient_detail(self, obj):
        return patient_summary(obj.patient)

    def validate_patient(self, value: Patient):
        if value.organization_id != self.context["request"].user.organization_id:
            raise serializers.ValidationError("Patient not found.")
        return value

    def validate_doctor(self, value):
        from apps.accounts.services import doctors_in_branch

        if not doctors_in_branch(self.context["request"].branch).filter(pk=value.pk).exists():
            raise serializers.ValidationError("Choose a doctor of this branch.")
        return value

    def validate_visit(self, value: Visit | None):
        if value is not None and value.branch_id != self.context["request"].branch.id:
            raise serializers.ValidationError("Check-up not found.")
        return value

    def validate(self, attrs):
        if attrs.get("rest_from") and attrs.get("rest_to") and attrs["rest_to"] < attrs["rest_from"]:
            raise serializers.ValidationError({"rest_to": "The end date is before the start date."})
        if attrs.get("kind") == "medical" and not attrs.get("rest_from"):
            raise serializers.ValidationError({"rest_from": "Enter from which date rest is advised."})
        if attrs.get("kind") == "fitness" and not attrs.get("fit_from"):
            raise serializers.ValidationError({"fit_from": "Enter from which date the patient is fit."})
        return attrs
