from rest_framework import serializers

from apps.appointments.serializers import patient_summary

from .models import ExamTemplate, Visit, VisitExam, VisitPhoto
from .services import fields_for_version, latest_prakriti

DURATION_UNITS = ("days", "weeks", "months", "years")
SEVERITIES = ("mild", "moderate", "severe")
DIAGNOSIS_KINDS = ("provisional", "final")
CODE_SYSTEMS = ("", "icd10", "icd11", "namaste")
MAX_ITEMS = 50


def _text(item, key, limit, required=False):
    value = str(item.get(key) or "").strip()
    if required and not value:
        raise serializers.ValidationError(f"'{key}' is missing.")
    return value[:limit]


class ExamTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamTemplate
        fields = ["id", "code", "version", "kind", "name", "name_gu", "name_hi", "description", "fields", "sort_order",
                  "is_active", "updated_at"]


class VisitExamSerializer(serializers.ModelSerializer):
    values = serializers.JSONField(read_only=True)
    result = serializers.JSONField(read_only=True)
    # The questions as they were when this exam was filled in (templates can change later)
    template_fields = serializers.SerializerMethodField()

    class Meta:
        model = VisitExam
        fields = ["id", "template", "template_code", "template_version", "values", "result", "template_fields",
                  "updated_at"]

    def get_template_fields(self, obj):
        return fields_for_version(obj.template, obj.template_version)


class VisitPhotoSerializer(serializers.ModelSerializer):
    visit_date = serializers.DateField(source="visit.visit_date", read_only=True)

    class Meta:
        model = VisitPhoto
        fields = ["id", "visit", "visit_date", "kind", "caption", "content_type", "size_bytes", "created_at"]
        read_only_fields = fields


class VisitSerializer(serializers.ModelSerializer):
    patient_detail = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    token_number = serializers.IntegerField(source="appointment.token_number", read_only=True, default=None)
    exams = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    prakriti = serializers.SerializerMethodField()
    complaints = serializers.JSONField(required=False)
    diagnoses = serializers.JSONField(required=False)
    advice = serializers.JSONField(required=False)

    class Meta:
        model = Visit
        fields = [
            "id", "patient", "patient_detail", "doctor", "doctor_name", "branch", "branch_name",
            "appointment", "token_number", "visit_date", "status", "completed_at",
            "complaints", "history_notes", "examination_notes", "diagnoses", "advice", "advice_notes",
            "follow_up_date", "follow_up_notes", "exams", "photos", "prakriti", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "patient", "doctor", "branch", "appointment", "visit_date", "status", "completed_at",
            "created_at", "updated_at",
        ]

    def get_patient_detail(self, obj):
        return patient_summary(obj.patient)

    def get_exams(self, obj):
        return VisitExamSerializer(obj.exams.all(), many=True).data

    def get_photos(self, obj):
        return VisitPhotoSerializer(obj.photos.all(), many=True).data

    def get_prakriti(self, obj):
        return latest_prakriti(obj.patient)

    # --- Checks for each section ---
    def _list(self, value, name):
        if not isinstance(value, list):
            raise serializers.ValidationError(f"{name} must be a list.")
        if len(value) > MAX_ITEMS:
            raise serializers.ValidationError(f"At most {MAX_ITEMS} items.")
        return value

    def validate_complaints(self, value):
        cleaned = []
        for item in self._list(value, "Complaints"):
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each complaint must have a label.")
            duration = item.get("duration")
            if duration not in (None, ""):
                try:
                    duration = int(duration)
                except (TypeError, ValueError):
                    raise serializers.ValidationError("Duration must be a number.")
                if not 0 <= duration <= 999:
                    raise serializers.ValidationError("Duration must be between 0 and 999.")
            else:
                duration = None
            score = item.get("score")
            if score not in (None, ""):
                try:
                    score = int(score)
                except (TypeError, ValueError):
                    raise serializers.ValidationError("Symptom score must be a number from 0 to 10.")
                if not 0 <= score <= 10:
                    raise serializers.ValidationError("Symptom score must be from 0 to 10.")
            else:
                score = None
            unit = item.get("duration_unit") or "days"
            severity = item.get("severity") or ""
            if unit not in DURATION_UNITS or (severity and severity not in SEVERITIES):
                raise serializers.ValidationError("Unknown duration unit or severity.")
            cleaned.append({
                "label": _text(item, "label", 200, required=True), "code": _text(item, "code", 60),
                "duration": duration, "duration_unit": unit, "severity": severity, "score": score,
                "notes": _text(item, "notes", 500),
            })
        return cleaned

    def validate_diagnoses(self, value):
        cleaned = []
        for item in self._list(value, "Diagnoses"):
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each diagnosis must have a label.")
            kind = item.get("kind") or "provisional"
            system = item.get("system") or ""
            if kind not in DIAGNOSIS_KINDS or system not in CODE_SYSTEMS:
                raise serializers.ValidationError("Unknown diagnosis type or code system.")
            cleaned.append({
                "label": _text(item, "label", 200, required=True), "code": _text(item, "code", 30),
                "system": system, "kind": kind, "master": _text(item, "master", 60),
            })
        return cleaned

    def validate_advice(self, value):
        return [str(v).strip()[:300] for v in self._list(value, "Advice") if str(v).strip()]


class VisitListSerializer(serializers.ModelSerializer):
    """Short version for the patient's visit timeline."""

    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    complaints = serializers.SerializerMethodField()
    diagnoses = serializers.SerializerMethodField()
    scores = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = Visit
        fields = [
            "id", "patient", "visit_date", "status", "doctor_name", "branch_name",
            "complaints", "diagnoses", "scores", "photo_count", "follow_up_date",
        ]

    def get_complaints(self, obj):
        return [c.get("label") for c in obj.complaints]

    def get_scores(self, obj):
        """{complaint: score} for the progress table."""
        return {c.get("label"): c.get("score") for c in obj.complaints if c.get("score") is not None}

    def get_diagnoses(self, obj):
        return [d.get("label") for d in obj.diagnoses]

    def get_photo_count(self, obj):
        return len(obj.photos.all())


class StartVisitSerializer(serializers.Serializer):
    patient = serializers.UUIDField(required=False)
    appointment = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if not attrs.get("patient") and not attrs.get("appointment"):
            raise serializers.ValidationError("Choose a patient or an appointment.")
        return attrs
