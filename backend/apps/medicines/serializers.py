from rest_framework import serializers

from apps.common.serializers import MasterField

from .models import BranchMedicine, Medicine, MedicineVersion


class MedicineSerializer(serializers.ModelSerializer):
    dosage_form = MasterField("dosage_form")
    dose_unit = MasterField("dose_unit")
    default_timing = MasterField("medicine_timing")
    default_anupana = MasterField("anupana")
    category = MasterField("product_category")
    pack_type = MasterField("pack_type")
    classical_equivalent_name = serializers.CharField(source="classical_equivalent.name", read_only=True, default="")
    # This branch's own settings (filled by the view)
    branch_price = serializers.SerializerMethodField()
    branch_active = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = [
            "id", "kind", "name", "name_gu", "name_hi", "synonyms", "generic_name", "category", "dosage_form",
            "composition", "reference", "pack_type", "units_per_pack", "allow_loose", "selling_price", "barcode",
            "strength", "sku", "notes", "manufacturer", "classical_equivalent", "classical_equivalent_name", "ayush_licence_no", "hsn_code",
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

    def validate_barcode(self, value):
        value = (value or "").strip()
        if value:
            org_id = self.context["request"].user.organization_id
            clash = Medicine.objects.filter(organization_id=org_id, barcode=value)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(f"This barcode is already used for {clash.first().name}.")
        return value

    def validate_sku(self, value):
        value = (value or "").strip().upper()
        if value:
            org_id = self.context["request"].user.organization_id
            clash = Medicine.objects.filter(organization_id=org_id, sku__iexact=value)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(f"This code is already used for {clash.first().name}.")
        return value

    def validate_gst_rate(self, value):
        if not 0 <= value <= 40:
            raise serializers.ValidationError("GST must be between 0 and 40 %.")
        return value

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", "classical"))
        if kind == "classical":
            attrs["classical_equivalent"] = None
        mrp = attrs.get("mrp", getattr(self.instance, "mrp", None))
        selling = attrs.get("selling_price", getattr(self.instance, "selling_price", None))
        if mrp is not None and selling is not None and selling > mrp:
            raise serializers.ValidationError({"selling_price": "Selling price cannot be more than MRP."})
        if attrs.get("allow_loose", getattr(self.instance, "allow_loose", False)) and not attrs.get(
                "units_per_pack", getattr(self.instance, "units_per_pack", None)):
            raise serializers.ValidationError({"units_per_pack": "Enter how many units are in one pack (e.g. 60)."})
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
