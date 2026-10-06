from rest_framework import serializers

from apps.appointments.serializers import patient_summary
from apps.common.serializers import MasterField
from apps.medicines.models import Medicine

from .models import DURATION_UNITS, Prescription, PrescriptionItem, PrescriptionTemplate
from .services import warnings_for

MAX_LINES = 40


class PrescriptionItemSerializer(serializers.ModelSerializer):
    medicine_flags = serializers.SerializerMethodField()

    class Meta:
        model = PrescriptionItem
        fields = [
            "id", "medicine", "medicine_name", "medicine_kind", "medicine_version", "dosage_form", "dose",
            "dose_unit", "frequency", "timing", "anupana", "duration", "duration_unit", "quantity",
            "instructions", "medicine_flags",
        ]

    def get_medicine_flags(self, obj):
        m = obj.medicine
        if m is None:
            return []
        return [f for f in ("schedule_e1", "contains_metals", "pregnancy_caution", "child_caution") if getattr(m, f)]


class LineInput(serializers.Serializer):
    """One prescription line as sent by the screen."""

    id = serializers.UUIDField(required=False, allow_null=True)
    medicine = serializers.UUIDField(required=False, allow_null=True)
    medicine_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    dosage_form = serializers.CharField(max_length=100, required=False, allow_blank=True)
    dose = serializers.CharField(max_length=20, required=False, allow_blank=True)
    dose_unit = serializers.CharField(max_length=40, required=False, allow_blank=True)
    frequency = serializers.CharField(max_length=20, required=False, allow_blank=True)
    timing = serializers.CharField(max_length=60, required=False, allow_blank=True)
    anupana = serializers.CharField(max_length=60, required=False, allow_blank=True)
    duration = serializers.IntegerField(min_value=0, max_value=365, required=False, allow_null=True)
    duration_unit = serializers.ChoiceField(choices=DURATION_UNITS, required=False)
    quantity = serializers.CharField(max_length=40, required=False, allow_blank=True)
    instructions = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate(self, attrs):
        org_id = self.context["request"].user.organization_id
        medicine_id = attrs.get("medicine")
        if medicine_id:
            medicine = Medicine.objects.select_related("dosage_form").filter(organization_id=org_id, pk=medicine_id).first()
            if medicine is None:
                raise serializers.ValidationError({"medicine": "Medicine not found."})
            attrs["medicine"] = medicine
        else:
            attrs["medicine"] = None
            if not attrs.get("medicine_name", "").strip():
                raise serializers.ValidationError({"medicine": "Choose a medicine or type its name."})
            attrs["medicine_name"] = attrs["medicine_name"].strip()
        return attrs


def clean_lines(serializer_context, raw) -> list[dict]:
    if not isinstance(raw, list):
        raise serializers.ValidationError({"items": "Must be a list."})
    if len(raw) > MAX_LINES:
        raise serializers.ValidationError({"items": f"At most {MAX_LINES} medicines."})
    lines = LineInput(data=raw, many=True, context=serializer_context)
    lines.is_valid(raise_exception=True)
    return lines.validated_data


class PrescriptionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()
    patient_detail = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    visit_date = serializers.DateField(source="visit.visit_date", read_only=True)

    class Meta:
        model = Prescription
        fields = [
            "id", "visit", "visit_date", "patient", "patient_detail", "doctor", "doctor_name", "branch_name",
            "status", "notes", "medicine_days", "finalized_at", "items", "warnings", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_items(self, obj):
        return PrescriptionItemSerializer(obj.items.select_related("medicine"), many=True).data

    def get_warnings(self, obj):
        return warnings_for(obj)

    def get_patient_detail(self, obj):
        return patient_summary(obj.patient)


class PrescriptionTemplateSerializer(serializers.ModelSerializer):
    diagnosis = MasterField("diagnosis")

    class Meta:
        model = PrescriptionTemplate
        fields = ["id", "name", "diagnosis", "items", "notes", "is_active", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Please give the template a name.")
        return value.strip()

    def validate_items(self, value):
        lines = clean_lines(self.context, value)
        if not lines:
            raise serializers.ValidationError("Add at least one medicine.")
        # Store plain values (medicine as id)
        return [
            {**{k: v for k, v in line.items() if k not in ("id", "medicine")},
             "medicine": str(line["medicine"].id) if line["medicine"] else None,
             "medicine_name": line["medicine"].name if line["medicine"] else line.get("medicine_name", "")}
            for line in lines
        ]
