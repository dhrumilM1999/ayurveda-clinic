import re
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Enquiry

PHONE = re.compile(r"^[6-9]\d{9}$")


def clean_phone(value: str) -> str:
    """'+91 98250 12345' -> '9825012345'."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not PHONE.match(digits):
        raise serializers.ValidationError("Enter a 10-digit mobile number.")
    return digits


class PublicEnquirySerializer(serializers.ModelSerializer):
    """What a visitor of the clinic website may send. Nothing else is accepted."""

    # Honeypot: real people never see this field (it is hidden); bots fill it
    website = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=200)

    class Meta:
        model = Enquiry
        fields = ["name", "phone", "email", "concern", "message", "preferred_date", "preferred_time", "language",
                  "branch", "consent_contact", "website"]
        extra_kwargs = {"branch": {"required": False, "allow_null": True}}

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Please enter your name.")
        return value

    def validate_phone(self, value):
        return clean_phone(value)

    def validate_preferred_date(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError("Choose today or a later date.")
        if value and value > timezone.localdate() + timedelta(days=180):
            raise serializers.ValidationError("Choose a date within the next 6 months.")
        return value

    def validate_language(self, value):
        return value if value in ("en", "gu", "hi") else "en"

    def validate_consent_contact(self, value):
        if not value:
            raise serializers.ValidationError("Please agree that the clinic may contact you.")
        return value


class EnquirySerializer(serializers.ModelSerializer):
    """The front desk's view of an enquiry."""

    branch_name = serializers.CharField(source="branch.name", read_only=True, default="")
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True, default="")
    patient_uhid = serializers.CharField(source="patient.uhid", read_only=True, default="")
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Enquiry
        fields = ["id", "created_at", "name", "phone", "email", "concern", "message", "preferred_date", "preferred_time",
                  "language", "source", "consent_contact", "status", "status_label", "follow_up_on", "notes", "branch",
                  "branch_name", "assigned_to", "assigned_to_name", "patient", "patient_uhid"]
        read_only_fields = ["id", "created_at", "consent_contact", "branch_name", "assigned_to_name", "patient_uhid", "status_label"]

    def validate_phone(self, value):
        return clean_phone(value)

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Please enter the name.")
        return value
