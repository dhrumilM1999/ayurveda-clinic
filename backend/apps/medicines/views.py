from django.http import HttpResponse
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet, snapshot as audit_snapshot

from .models import BranchMedicine, Medicine
from .serializers import BranchSettingsSerializer, MedicineSerializer, MedicineVersionSerializer
from .services import import_medicines, import_template_csv, read_rows, save_medicine, search_filter, set_branch_settings


class MedicineViewSet(AuditedModelViewSet):
    """
    The medicine list (shared by all branches). Each branch sees its own price and on/off switch.
    ?q=   search any name / synonym / composition      ?kind=classical|proprietary
    ?for_rx=1  only medicines in use in this branch (for the prescription screen)
    """

    queryset = Medicine.objects.select_related(
        "dosage_form", "dose_unit", "default_timing", "default_anupana", "classical_equivalent",
    )
    serializer_class = MedicineSerializer
    permission_prefix = "medicines"
    branch_required = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = ["kind", "dosage_form", "is_active", "schedule_e1", "contains_metals"]
    ordering_fields = ["name", "updated_at", "mrp"]
    required_permissions = {
        "versions": "medicines.view",
        "import_template": "medicines.manage",
        "import_file": "medicines.manage",
        "branch_settings": "medicines.manage",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("q", "").strip():
            qs = qs.filter(search_filter(params["q"].strip()))
        if params.get("for_rx") == "1":
            off = BranchMedicine.objects.filter(branch=self.request.branch, is_active=False).values("medicine_id")
            qs = qs.filter(is_active=True).exclude(id__in=off)
        return qs.order_by("name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        branch = getattr(self.request, "branch", None)
        if branch is not None:
            context["branch_rows"] = {r.medicine_id: r for r in BranchMedicine.objects.filter(branch=branch)}
        return context

    def perform_create(self, serializer):
        medicine = Medicine(organization_id=self.request.user.organization_id, **serializer.validated_data)
        save_medicine(medicine, self.request.user, is_new=True)
        serializer.instance = medicine
        log_action(self.request, "create", medicine, changes={"name": medicine.name})

    def perform_update(self, serializer):
        medicine = serializer.instance
        fields = list(serializer.validated_data)
        before = audit_snapshot(medicine, fields)
        for key, value in serializer.validated_data.items():
            setattr(medicine, key, value)
        old_version = medicine.version
        save_medicine(medicine, self.request.user, is_new=False)
        after = audit_snapshot(medicine, fields)
        changes = {k: {"from": before.get(k), "to": after.get(k)} for k in after if before.get(k) != after.get(k)}
        if medicine.version != old_version:
            changes["version"] = {"from": old_version, "to": medicine.version}
        if changes:
            log_action(self.request, "update", medicine, changes=changes)

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        medicine = self.get_object()
        return Response(MedicineVersionSerializer(medicine.versions.select_related("created_by"), many=True).data)

    @action(detail=True, methods=["patch"], url_path="branch")
    def branch_settings(self, request, pk=None):
        """This branch's own price and on/off switch."""
        medicine = self.get_object()
        data = BranchSettingsSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        price = data.validated_data.get("price", None) if "price" in request.data else None
        if "price" in request.data and request.data["price"] in (None, ""):
            price = ""
        set_branch_settings(medicine, request.branch, request.user, price=price,
                            is_active=data.validated_data.get("is_active"))
        log_action(request, "update", medicine, changes={"branch": request.branch.name, **{
            k: str(v) for k, v in request.data.items() if k in ("price", "is_active")}})
        return Response(self.get_serializer(medicine).data)

    @action(detail=False, methods=["get"], url_path="import-template")
    def import_template(self, request):
        response = HttpResponse(import_template_csv(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="medicine-list-template.csv"'
        return response

    @action(detail=False, methods=["post"], url_path="import")
    def import_file(self, request):
        """Upload .xlsx / .csv. With dry_run=1 nothing is saved (preview)."""
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "Choose an Excel (.xlsx) or CSV file."})
        dry_run = str(request.data.get("dry_run", "")).lower() in ("1", "true", "yes")
        rows = read_rows(uploaded)
        if len(rows) > 5000:
            raise ValidationError({"file": "At most 5000 medicines per file."})
        result = import_medicines(request.user.organization, rows, request.user, dry_run=dry_run)
        if not dry_run:
            log_action(request, "create", None, object_type="medicines.import", object_repr=uploaded.name[:200],
                       changes={k: result[k] for k in ("created", "updated", "unchanged")})
        return Response({**result, "dry_run": dry_run}, status=http.HTTP_200_OK)
