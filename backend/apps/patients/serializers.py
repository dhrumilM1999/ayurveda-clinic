import re
from datetime import date, timedelta

from django.db import transaction
from rest_framework import serializers

from apps.accounts.services import user_has_perm
from apps.common.models import MasterValue
from apps.common.utils import mask_phone

from .models import (
    ConsentPurpose, Patient, PatientAllergy, PatientCondition, PatientConsent, PatientDocument,
    PatientMedication, PatientVital,
)

MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def master_dict(value):
    if value is None:
        return None
    return {"id": str(value.id), "code": value.code, "label": value.label,
            "label_gu": value.label_gu, "label_hi": value.label_hi}


class MasterField(serializers.PrimaryKeyRelatedField):
    """A dropdown value from one master list, e.g. MasterField("blood_group")."""

    def __init__(self, category, **kwargs):
        self.category = category
        kwargs.setdefault("queryset", MasterValue.objects.all())
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        org_id = self.context["request"].user.organization_id
        if value.organization_id != org_id or value.category != self.category:
            raise serializers.ValidationError("Unknown value for this list.")
        return value

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return master_dict(value)


def clean_mobile(value, country_code="+91"):
    digits = re.sub(r"\D", "", value or "")
    if country_code == "+91":
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if not MOBILE_RE.match(digits):
            raise serializers.ValidationError("Enter a valid 10-digit Indian mobile number.")
    elif not 6 <= len(digits) <= 15:
        raise serializers.ValidationError("Enter a valid mobile number.")
    return digits


# --- Child rows ------------------------------------------------------------------
class ConditionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    condition = MasterField("medical_condition", allow_null=False, required=True)

    class Meta:
        model = PatientCondition
        fields = ["id", "condition", "since", "notes"]


class AllergySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    allergy_type = MasterField("allergy_type")

    class Meta:
        model = PatientAllergy
        fields = ["id", "allergy_type", "allergen", "severity", "reaction"]


class MedicationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = PatientMedication
        fields = ["id", "name", "dose", "frequency", "since", "notes"]


def sync_children(patient, model, items, actor):
    """Make the patient's child rows match `items`: update by id, add new ones, soft-delete the rest."""
    existing = {str(row.id): row for row in model.objects.filter(patient=patient)}
    keep = set()
    for item in items:
        item = dict(item)
        row_id = str(item.pop("id", "") or "")
        row = existing.get(row_id)
        if row is None:
            row = model.objects.create(
                organization_id=patient.organization_id, patient=patient,
                created_by=actor, updated_by=actor, **item,
            )
        else:
            for key, value in item.items():
                setattr(row, key, value)
            row.updated_by = actor
            row.save()
        keep.add(str(row.id))
    for row_id, row in existing.items():
        if row_id not in keep:
            row.delete(user=actor)


# --- Patient ----------------------------------------------------------------------
class PatientListSerializer(serializers.ModelSerializer):
    """For lists and search results: phone numbers are masked."""

    full_name = serializers.CharField(read_only=True)
    age_years = serializers.IntegerField(read_only=True)
    mobile_masked = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    registered_branch_name = serializers.CharField(source="registered_branch.name", default="", read_only=True)
    has_photo = serializers.SerializerMethodField()
    allergy_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Patient
        fields = [
            "id", "uhid", "title", "full_name", "first_name", "last_name", "gender", "age_years",
            "mobile_masked", "city", "registration_date", "registered_branch_name", "is_vip", "is_foc",
            "has_photo", "allergy_count",
        ]

    def get_mobile_masked(self, obj):
        return mask_phone(obj.mobile)

    def get_title(self, obj):
        return master_dict(obj.title)

    def get_has_photo(self, obj):
        return bool(obj.photo)


MEDICAL_TEXT = ["past_history", "family_history", "surgical_history", "other_notes"]


class PatientSerializer(serializers.ModelSerializer):
    """Full patient details (register / view / edit)."""

    full_name = serializers.CharField(read_only=True)
    age_years = serializers.IntegerField(read_only=True)
    age = serializers.IntegerField(write_only=True, required=False, allow_null=True, min_value=0, max_value=120,
                                   help_text="Use when the date of birth is not known")
    title = MasterField("title")
    blood_group = MasterField("blood_group")
    marital_status = MasterField("marital_status")
    referral_source = MasterField("referral_source")
    emergency_relation = MasterField("relation")
    registered_branch_name = serializers.CharField(source="registered_branch.name", default="", read_only=True)
    has_photo = serializers.SerializerMethodField()
    conditions = ConditionSerializer(many=True, required=False)
    allergies = AllergySerializer(many=True, required=False)
    medications = MedicationSerializer(many=True, required=False)
    created_by_name = serializers.CharField(source="created_by.full_name", default="", read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "uhid", "registration_date", "registered_branch", "registered_branch_name", "has_photo",
            "title", "first_name", "middle_name", "last_name", "full_name",
            "date_of_birth", "dob_is_estimated", "age", "age_years", "gender", "blood_group", "marital_status",
            "preferred_language", "occupation", "guardian_name",
            "country_code", "mobile", "alternate_mobile", "email",
            "house", "society", "area", "pincode", "city", "state", "country",
            "referral_source", "referred_by_name", "referred_by_phone",
            "emergency_name", "emergency_relation", "emergency_phone",
            "is_vip", "is_foc",
            "past_history", "family_history", "surgical_history", "other_notes",
            "conditions", "allergies", "medications",
            "created_at", "updated_at", "created_by_name",
        ]
        read_only_fields = ["id", "uhid", "registered_branch", "dob_is_estimated", "created_at", "updated_at"]

    def get_has_photo(self, obj):
        return bool(obj.photo)

    # --- who may see / write the medical part ---
    def _can(self, code):
        request = self.context["request"]
        return user_has_perm(request.user, code, getattr(request, "branch", None))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["conditions"] = ConditionSerializer(
            instance.conditions.select_related("condition"), many=True, context=self.context).data
        data["allergies"] = AllergySerializer(
            instance.allergies.select_related("allergy_type"), many=True, context=self.context).data
        data["medications"] = MedicationSerializer(instance.medications.all(), many=True, context=self.context).data
        if not self._can("emr.view"):
            # Full medical history only for doctors (emr.view). Allergies and current medicines
            # stay visible to everyone who can see the patient, for safety.
            for key in MEDICAL_TEXT + ["conditions"]:
                data.pop(key, None)
            data["medical_history_hidden"] = True
        return data

    # --- validation ---
    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Please enter the first name.")
        return value

    def validate_pincode(self, value):
        if value and not re.fullmatch(r"\d{6}", value.strip()):
            raise serializers.ValidationError("PIN code must be 6 digits.")
        return value.strip()

    def validate_date_of_birth(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        if value and value < date.today() - timedelta(days=365 * 125):
            raise serializers.ValidationError("Please check the date of birth.")
        return value

    def validate(self, attrs):
        code = attrs.get("country_code", getattr(self.instance, "country_code", "+91"))
        for field in ["mobile", "alternate_mobile", "emergency_phone", "referred_by_phone"]:
            if attrs.get(field):
                try:
                    attrs[field] = clean_mobile(attrs[field], code if field != "referred_by_phone" else "+91")
                except serializers.ValidationError as error:
                    raise serializers.ValidationError({field: error.detail})
        if self.instance is None and not attrs.get("mobile"):
            raise serializers.ValidationError({"mobile": "Mobile number is required."})

        age = attrs.pop("age", None)
        if attrs.get("date_of_birth"):
            attrs["dob_is_estimated"] = False
        elif age is not None:
            today = date.today()
            attrs["date_of_birth"] = date(today.year - age, 7, 1) if age else today
            attrs["dob_is_estimated"] = True
        elif self.instance is None:
            raise serializers.ValidationError({"date_of_birth": "Enter the date of birth or the age."})

        # Medical history: anyone registering may enter it; later changes need emr.edit.
        if self.instance is not None and not self._can("emr.edit"):
            for key in MEDICAL_TEXT + ["conditions"]:
                if key in attrs:
                    raise serializers.ValidationError({key: "You don't have permission to change medical history."})
        return attrs

    # --- saving ---
    @transaction.atomic
    def create(self, validated_data):
        from .services import next_uhid

        children = {key: validated_data.pop(key, []) for key in ["conditions", "allergies", "medications"]}
        request = self.context["request"]
        organization = request.user.organization
        patient = Patient.objects.create(uhid=next_uhid(organization), registered_branch=request.branch, **validated_data)
        self._save_children(patient, children)
        return patient

    @transaction.atomic
    def update(self, instance, validated_data):
        children = {key: validated_data.pop(key) for key in ["conditions", "allergies", "medications"] if key in validated_data}
        instance = super().update(instance, validated_data)
        self._save_children(instance, children)
        return instance

    def _save_children(self, patient, children):
        actor = self.context["request"].user
        models = {"conditions": PatientCondition, "allergies": PatientAllergy, "medications": PatientMedication}
        for key, items in children.items():
            sync_children(patient, models[key], items, actor)


class DuplicateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age_years = serializers.IntegerField(read_only=True)
    mobile_masked = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ["id", "uhid", "full_name", "gender", "age_years", "mobile_masked", "city"]

    def get_mobile_masked(self, obj):
        return mask_phone(obj.mobile)


# --- Vitals ---------------------------------------------------------------------
class VitalSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    recorded_by_name = serializers.CharField(source="created_by.full_name", default="", read_only=True)

    class Meta:
        model = PatientVital
        fields = [
            "id", "patient", "recorded_at", "bp_systolic", "bp_diastolic", "pulse", "temperature_f", "spo2",
            "respiratory_rate", "weight_kg", "height_cm", "bmi", "notes", "branch_name", "recorded_by_name",
        ]
        read_only_fields = ["id", "bmi", "branch_name", "recorded_by_name"]
        extra_kwargs = {"recorded_at": {"required": False}}

    LIMITS = {
        "bp_systolic": (50, 260), "bp_diastolic": (30, 160), "pulse": (25, 250),
        "temperature_f": (90, 110), "spo2": (50, 100), "respiratory_rate": (5, 60),
        "weight_kg": (0.5, 300), "height_cm": (30, 250),
    }

    def validate_patient(self, value):
        if value.organization_id != self.context["request"].user.organization_id:
            raise serializers.ValidationError("Unknown patient.")
        return value

    def validate(self, attrs):
        for field, (low, high) in self.LIMITS.items():
            value = attrs.get(field)
            if value is not None and not low <= float(value) <= high:
                raise serializers.ValidationError({field: f"Please check this value (expected {low}–{high})."})
        measured = [f for f in self.LIMITS if attrs.get(f) is not None]
        if not measured:
            raise serializers.ValidationError("Enter at least one measurement.")
        return attrs


# --- Documents ------------------------------------------------------------------
class DocumentSerializer(serializers.ModelSerializer):
    document_type = MasterField("document_type")
    file = serializers.FileField(write_only=True)
    uploaded_by_name = serializers.CharField(source="created_by.full_name", default="", read_only=True)
    branch_name = serializers.CharField(source="branch.name", default="", read_only=True)

    class Meta:
        model = PatientDocument
        fields = [
            "id", "patient", "document_type", "title", "document_date", "notes", "file",
            "original_name", "content_type", "size_bytes", "created_at", "uploaded_by_name", "branch_name",
        ]
        read_only_fields = ["id", "original_name", "content_type", "size_bytes", "created_at"]

    def validate_patient(self, value):
        if value.organization_id != self.context["request"].user.organization_id:
            raise serializers.ValidationError("Unknown patient.")
        return value


# --- Consent ----------------------------------------------------------------------
class ConsentPurposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentPurpose
        fields = [
            "id", "code", "title", "title_gu", "title_hi", "description", "description_gu",
            "description_hi", "is_required", "version",
        ]


class ConsentSerializer(serializers.ModelSerializer):
    purpose_code = serializers.CharField(source="purpose.code", read_only=True)
    purpose_title = serializers.CharField(source="purpose.title", read_only=True)
    recorded_by_name = serializers.CharField(source="created_by.full_name", default="", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = PatientConsent
        fields = [
            "id", "patient", "purpose", "purpose_code", "purpose_title", "purpose_version", "granted",
            "method", "language", "given_by", "notes", "created_at", "recorded_by_name", "branch_name",
        ]
        read_only_fields = ["id", "purpose_version", "created_at"]

    def validate(self, attrs):
        org_id = self.context["request"].user.organization_id
        if attrs["patient"].organization_id != org_id or attrs["purpose"].organization_id != org_id:
            raise serializers.ValidationError("Unknown patient or purpose.")
        return attrs
