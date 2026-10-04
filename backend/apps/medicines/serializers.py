from rest_framework import serializers

from apps.common.serializers import MasterField

from .models import BranchMedicine, Medicine, MedicineVersion


class MedicineSerializer(serializers.ModelSerializer):
    dosage_form = MasterField("dosage_form")
    dose_unit = MasterField("dose_unit")
    default_timing = MasterField("medicine_timing")
    default_anupana = MasterField("anupana")
    classical_equivalent_name = serializers.CharField(source="classical_equivalent.name", read_only=True, default="")
    # This branch's own settings (filled by the view)
    branch_price = serializers.SerializerMethodField()
    branch_active = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = [
            "id", "kind", "name", "name_gu", "name_hi", "synonyms", "dosage_form", "composition", "reference",
            "manufacturer", "classical_equivalent", "classical_equivalent_name", "ayush_licence_no", "hsn_code",
            "gst_rate", "mrp", "pack_size", "default_dose", "dose_unit", "default_frequency", "default_timing",
            "default_anupana", "schedule_e1", "contains_metals", "pregnancy_caution", "child_caution",
            "safety_notes", "is_sample", "is_active", "version", "branch_price", "branch_active", "updated_at",
        ]
        read_only_fields = ["id", "is_sample", "version", "updated_at"]

    def _branch_row(self, obj) -> BranchMedicine | None:
        rows = self.context.get("branch_rows")
        return rows.get(obj.id) if rows is not None else None

    def get_branch_price(self, obj):
        row = self._branch_row(obj)
        price = row.price if row and row.price is not None else obj.mrp
        return str(price) if price is not None else None

    def get_branch_active(self, obj):
        row = self._branch_row(obj)
        return row.is_active if row else True

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Please enter the name.")
        return value

    def validate_classical_equivalent(self, value):
        if value and (value.kind != "classical" or value.organization_id != self.context["request"].user.organization_id):
            raise serializers.ValidationError("Choose a classical medicine.")
        return value

    def validate_gst_rate(self, value):
        if not 0 <= value <= 40:
            raise serializers.ValidationError("GST must be between 0 and 40 %.")
        return value

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", "classical"))
        if kind == "classical":
            attrs["classical_equivalent"] = None
        name = attrs.get("name", getattr(self.instance, "name", ""))
        org_id = self.context["request"].user.organization_id
        clash = Medicine.objects.filter(organization_id=org_id, kind=kind, name__iexact=name)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"name": "A medicine with this name already exists."})
        return attrs


class MedicineVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta:
        model = MedicineVersion
        fields = ["version", "data", "created_at", "created_by_name"]


class BranchSettingsSerializer(serializers.Serializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=0)
    is_active = serializers.BooleanField(required=False)
