"""
Lab tests and investigations.
GET/POST/PATCH /lab-tests/                the clinic's list of tests (search with ?q=); POST /lab-tests/load-sample/ adds the starting list
GET  /investigations/?visit=&patient=&status=    tests advised (and their reports)
POST /investigations/                     {visit, test | test_name, note}   the doctor advises a test
PATCH /investigations/<id>/               {status, result_text, reported_on, document, note}   report received / not needed
DELETE /investigations/<id>/              marks it removed (never really deleted)
Needs emr.view to read and emr.edit to change (the doctor). Every change is in the audit log.
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.viewsets import AuditedModelViewSet

from .lab_catalog import LAB_TESTS
from .models import LabTest, Visit, VisitInvestigation


def load_sample_lab_tests(organization) -> int:
    """Add the starting list of tests (skips names that already exist). Returns how many were added."""
    existing = set(LabTest.objects.filter(organization=organization).values_list("name", flat=True))
    added = 0
    for order, (category, name, gu, hi) in enumerate(LAB_TESTS):
        if name in existing:
            continue
        LabTest.objects.create(organization=organization, name=name, name_gu=gu, name_hi=hi, category=category,
                               sort_order=order, is_sample=True)
        added += 1
    return added


class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = ["id", "name", "name_gu", "name_hi", "category", "is_active", "sort_order", "is_sample"]
        read_only_fields = ["id", "is_sample"]

    def validate_name(self, value):
        value = value.strip()
        same = LabTest.all_objects.filter(organization_id=self.context["request"].user.organization_id, name__iexact=value)
        if self.instance is not None:
            same = same.exclude(pk=self.instance.pk)
        if same.exists():
            raise serializers.ValidationError("This test is already in the list.")
        return value


class InvestigationSerializer(serializers.ModelSerializer):
    test_name_gu = serializers.CharField(source="test.name_gu", read_only=True, default="")
    test_name_hi = serializers.CharField(source="test.name_hi", read_only=True, default="")
    category = serializers.CharField(source="test.category", read_only=True, default="other")
    document_title = serializers.CharField(source="document.title", read_only=True, default="")
    visit_date = serializers.DateField(source="visit.visit_date", read_only=True)

    class Meta:
        model = VisitInvestigation
        fields = ["id", "visit", "visit_date", "patient", "test", "test_name", "test_name_gu", "test_name_hi", "category", "status",
                  "advised_on", "note", "result_text", "reported_on", "document", "document_title", "created_at"]
        read_only_fields = ["id", "patient", "advised_on", "created_at"]
        extra_kwargs = {"test_name": {"required": False, "allow_blank": True}, "visit": {"required": False}}

    def validate(self, attrs):
        org_id = self.context["request"].user.organization_id
        visit = attrs.get("visit") or getattr(self.instance, "visit", None)
        if visit is None or visit.organization_id != org_id:
            raise serializers.ValidationError({"visit": "Check-up not found."})
        test = attrs.get("test")
        if test is not None and test.organization_id != org_id:
            raise serializers.ValidationError({"test": "Test not found."})
        document = attrs.get("document")
        if document is not None and (document.organization_id != org_id or document.patient_id != visit.patient_id):
            raise serializers.ValidationError({"document": "This file belongs to another patient."})
        if self.instance is None:
            name = (attrs.get("test_name") or (test.name if test else "")).strip()
            if not name:
                raise serializers.ValidationError({"test_name": "Choose a test or type its name."})
            attrs["test_name"] = name
        if attrs.get("reported_on") and attrs["reported_on"] > timezone.localdate():
            raise serializers.ValidationError({"reported_on": "The report date cannot be in the future."})
        return attrs


class LabTestViewSet(AuditedModelViewSet):
    """The clinic's list of tests. The doctor may add and edit; nothing is ever deleted (switch a test off instead)."""

    queryset = LabTest.objects.all()
    serializer_class = LabTestSerializer
    permission_prefix = "emr"
    branch_required = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None
    required_permissions = {"list": "emr.view", "retrieve": "emr.view", "create": "emr.edit", "partial_update": "emr.edit", "update": "emr.edit", "destroy": "emr.edit", "load_sample": "emr.edit"}

    def get_queryset(self):
        qs = super().get_queryset()
        text = self.request.query_params.get("q", "").strip()
        if text:
            qs = qs.filter(Q(name__icontains=text) | Q(name_gu__icontains=text) | Q(name_hi__icontains=text))
        if self.request.query_params.get("all") != "1":
            qs = qs.filter(is_active=True)
        return qs

    @action(detail=False, methods=["post"], url_path="load-sample")
    def load_sample(self, request):
        return Response({"added": load_sample_lab_tests(request.user.organization)})


class InvestigationViewSet(AuditedModelViewSet):
    queryset = VisitInvestigation.objects.select_related("test", "visit", "document")
    serializer_class = InvestigationSerializer
    permission_prefix = "emr"
    branch_required = True
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    pagination_class = None
    required_permissions = {"list": "emr.view", "retrieve": "emr.view", "create": "emr.edit", "partial_update": "emr.edit", "update": "emr.edit", "destroy": "emr.edit"}
    audit_redact_fields = {"result_text"}

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("visit"):
            qs = qs.filter(visit_id=p["visit"])
        if p.get("patient"):
            qs = qs.filter(patient_id=p["patient"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        elif self.action == "list":
            qs = qs.exclude(status="cancelled")
        if self.action == "list" and not (p.get("visit") or p.get("patient")):
            raise ValidationError({"visit": "Choose a check-up or a patient."})
        return qs

    def perform_create(self, serializer):
        visit = serializer.validated_data["visit"]
        if self.request.branch.id != visit.branch_id:
            raise ValidationError({"visit": "This check-up belongs to another branch."})
        serializer.validated_data["patient"] = visit.patient
        serializer.validated_data["advised_on"] = visit.visit_date
        if serializer.validated_data.get("test") is not None:
            serializer.validated_data.setdefault("test_name", serializer.validated_data["test"].name)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        data = serializer.validated_data
        # A report (file or result) means the test is done; the date is today unless told otherwise
        if ("document" in data and data["document"]) or data.get("result_text"):
            if "status" not in data and serializer.instance.status == "advised":
                data["status"] = "done"
            data.setdefault("reported_on", timezone.localdate())
        super().perform_update(serializer)
