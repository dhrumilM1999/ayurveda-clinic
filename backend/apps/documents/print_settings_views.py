"""
PDF settings API (Settings -> PDF settings). Needs "settings.manage", except /print-settings/paper-defaults/
which every signed-in user may read (the print windows start with the paper chosen here).

GET  /print-settings/                  everything saved + the list of documents + the built-in defaults
PUT  /print-settings/                  {scope: "org"|"branch", doc_type: "all"|"prescription"|..., values: {...}}
                                       saves that place; empty values = back to default
POST /print-settings/preview/          the real PDF with settings that are not saved yet
GET  /print-settings/paper-defaults/   {doc_type: paper} for the current branch
"""
from django.http import HttpResponse
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BranchPermission
from apps.accounts.services import user_has_perm
from apps.audit.services import log_action

from . import print_settings as ps_service
from .models import PrintSetting
from .print_preview import preview_pdf
from .serializers import PrintPreviewSerializer, PrintSettingSaveSerializer


def _manage(request):
    if not user_has_perm(request.user, "settings.manage", request.branch):
        raise PermissionDenied()


class PrintSettingsView(APIView):
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_required = True

    def get(self, request):
        _manage(request)
        branch = request.branch
        rows = PrintSetting.objects.filter(organization_id=branch.organization_id)
        saved = {"org": {}, "branch": {}}
        for row in rows:
            if row.branch_id is None:
                saved["org"][row.doc_type] = row.values
            elif row.branch_id == branch.id:
                saved["branch"][row.doc_type] = row.values
        return Response({**ps_service.catalog(), "saved": saved, "branch": {"id": str(branch.id), "name": branch.name},
                         "multi_branch": branch.organization.multi_branch})

    def put(self, request):
        _manage(request)
        data = PrintSettingSaveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        branch = request.branch
        values = ps_service.save(
            organization=branch.organization, branch=branch if data.validated_data["scope"] == "branch" else None,
            doc_type=data.validated_data["doc_type"], values=data.validated_data["values"], user=request.user)
        log_action(request, "update", object_type="documents.printsetting", object_repr=data.validated_data["doc_type"],
                   changes={"scope": data.validated_data["scope"], "values": values})
        return Response({"scope": data.validated_data["scope"], "doc_type": data.validated_data["doc_type"], "values": values})


class PrintPreviewView(APIView):
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_required = True

    def post(self, request):
        _manage(request)
        data = PrintPreviewSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        content, source = preview_pdf(
            branch=request.branch, doc_type=d["doc_type"], paper=d.get("paper") or None, lang=d.get("lang") or None,
            drafts=d["drafts"], duplicate=d["duplicate"], user=request.user)
        if source == "real":  # a real patient's record was shown on screen: write it to the audit log
            log_action(request, "view", object_type="documents.printsetting", object_repr=d["doc_type"],
                       changes={"preview": True, "document": d["doc_type"]})
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="preview.pdf"'
        response["X-Preview-Source"] = source
        return response


class PaperDefaultsView(APIView):
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_required = True

    def get(self, request):
        return Response(ps_service.paper_defaults(request.branch))
