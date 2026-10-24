"""
Handwritten prescriptions (digital pad).
POST /handwritten-prescriptions/   multipart: visit (id), ink (PNG, transparent), paper (a5 | a4, optional)
GET  /handwritten-prescriptions/?visit=<id> | ?patient=<id>      the pages (never the pictures themselves)
GET  /handwritten-prescriptions/<id>/image/?kind=combined|ink   the picture (private, audit-logged)
DELETE /handwritten-prescriptions/<id>/                          marks a page as removed (the file is kept)
"""
from django.http import FileResponse
from rest_framework import mixins, status as http, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.audit.services import log_action
from apps.emr.models import Visit

from .handwriting import save_handwriting
from .models import HandwrittenPrescription


def page_data(page: HandwrittenPrescription) -> dict:
    return {
        "id": str(page.id), "visit": str(page.visit_id), "patient": str(page.patient_id), "paper": page.paper,
        "number": page.number, "created_at": page.created_at, "width_px": page.width_px, "height_px": page.height_px,
        "doctor_name": page.doctor.full_name,
    }


class HandwrittenPrescriptionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                                     mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, BranchPermission]
    parser_classes = [MultiPartParser, FormParser]
    branch_scoped = True
    pagination_class = None
    permission_prefix = "prescriptions"
    # The doctor writes; the pharmacy and others who may see prescriptions only read
    required_permissions = {"create": "prescriptions.create", "destroy": "prescriptions.create",
                            "list": "prescriptions.view", "retrieve": "prescriptions.view", "image": "prescriptions.view"}

    def get_queryset(self):
        qs = HandwrittenPrescription.objects.filter(
            organization_id=self.request.user.organization_id, branch=self.request.branch,
        ).select_related("doctor", "visit", "patient")
        params = self.request.query_params
        if params.get("visit"):
            qs = qs.filter(visit_id=params["visit"])
        if params.get("patient"):
            qs = qs.filter(patient_id=params["patient"])
        return qs

    def list(self, request, *args, **kwargs):
        if not (request.query_params.get("visit") or request.query_params.get("patient")):
            raise ValidationError({"visit": "Choose a check-up or a patient."})
        pages = self.get_queryset()
        log_action(request, "view", None, object_type="prescriptions.handwritten", object_repr="list",
                   changes={"count": len(pages)})
        return Response([page_data(p) for p in pages])

    def retrieve(self, request, *args, **kwargs):
        return Response(page_data(self.get_object()))

    def create(self, request, *args, **kwargs):
        visit = Visit.objects.filter(organization_id=request.user.organization_id, branch=request.branch,
                                     pk=request.data.get("visit")).select_related("branch", "patient", "doctor").first()
        if visit is None:
            raise NotFound("Check-up not found in this branch.")
        page = save_handwriting(visit, request.user, request.FILES.get("ink"), request.data.get("paper") or None)
        log_action(request, "create", page, changes={"patient": str(page.patient_id), "paper": page.paper})
        return Response(page_data(page), status=http.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        page = self.get_object()
        page.delete(user=request.user)  # soft delete: the files are kept
        log_action(request, "delete", page, changes={"patient": str(page.patient_id)})
        return Response(status=http.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def image(self, request, pk=None):
        page = self.get_object()
        which = request.query_params.get("kind", "combined")
        if which not in ("combined", "ink"):
            raise ValidationError({"kind": "Choose combined or ink."})
        field = page.ink if which == "ink" else page.image
        if not field:
            raise NotFound("Picture not found.")
        log_action(request, "view", page, changes={"picture": which, "patient": str(page.patient_id)})
        response = FileResponse(field.open("rb"), content_type="image/png")
        response["Cache-Control"] = "no-store"
        return response
