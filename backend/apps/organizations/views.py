from rest_framework import viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BranchPermission
from apps.accounts.services import accessible_branches, user_has_perm
from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet

from .features_catalog import ADDITIONAL_CHOICES, ADDITIONAL_FEATURES, FEATURES
from .models import Branch, BranchFeatureFlag, Organization, OrganizationChoice, OrganizationFeature, Room, RoomType
from .serializers import (
    BranchSerializer, FeatureFlagSerializer, OrganizationSerializer, RoomSerializer, RoomTypeSerializer,
)
from .services import branch_features, organization_choices, organization_features


class CurrentOrganizationView(APIView):
    """GET / PATCH the logged-in user's organization (clinic name, GSTIN, ...)."""

    permission_classes = [IsAuthenticated, BranchPermission]

    def get(self, request):
        return Response(OrganizationSerializer(request.user.organization).data)

    def patch(self, request):
        if not user_has_perm(request.user, "settings.manage"):
            self.permission_denied(request)
        org = request.user.organization
        serializer = OrganizationSerializer(org, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        log_action(request, "update", org, changes={"fields": sorted(serializer.validated_data)})
        return Response(serializer.data)


class OrganizationLogoView(APIView):
    """
    The clinic logo printed on prescriptions, certificates, reports and bills (Settings -> Clinic).
    GET = the image, POST (field "file": PNG or JPG, up to 2 MB) = upload / change, DELETE = remove.
    """

    permission_classes = [IsAuthenticated, BranchPermission]

    def get(self, request):
        from django.http import FileResponse

        org = request.user.organization
        if not org.logo:
            raise NotFound("No logo uploaded.")
        return FileResponse(org.logo.open("rb"))

    def post(self, request):
        if not user_has_perm(request.user, "settings.manage"):
            self.permission_denied(request)
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": "Choose an image."})
        if upload.size > 2 * 1024 * 1024:
            raise ValidationError({"file": "The logo must be smaller than 2 MB."})
        try:
            from PIL import Image

            image = Image.open(upload)
            image.verify()
            if image.format not in ("PNG", "JPEG"):
                raise ValueError
        except Exception:
            raise ValidationError({"file": "Use a PNG or JPG image."})
        upload.seek(0)
        org = request.user.organization
        if org.logo:
            org.logo.delete(save=False)
        org.logo.save(upload.name, upload, save=False)
        org.updated_by = request.user
        org.save(update_fields=["logo", "updated_by", "updated_at"])
        log_action(request, "update", org, changes={"logo": "uploaded"})
        return Response({"has_logo": True})

    def delete(self, request):
        if not user_has_perm(request.user, "settings.manage"):
            self.permission_denied(request)
        org = request.user.organization
        if org.logo:
            org.logo.delete(save=False)
        org.logo = ""
        org.save(update_fields=["logo", "updated_at"])
        log_action(request, "update", org, changes={"logo": "removed"})
        return Response({"has_logo": False})


class BranchViewSet(AuditedModelViewSet):
    """Branches. Branches are never deleted — switch them off with is_active instead."""

    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_prefix = "branches"
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    search_fields = ["name", "code", "city"]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_org_admin:
            qs = qs.filter(id__in=accessible_branches(user).values("id"))
        return qs


class RoomTypeViewSet(AuditedModelViewSet):
    """Master list for the room-type dropdown (organization-wide)."""

    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer
    permission_prefix = "rooms"
    pagination_class = None
    filterset_fields = ["is_active"]


class RoomViewSet(AuditedModelViewSet):
    """Rooms of the current branch."""

    queryset = Room.objects.select_related("room_type")
    serializer_class = RoomSerializer
    permission_prefix = "rooms"
    branch_scoped = True
    search_fields = ["name", "notes"]
    filterset_fields = ["is_active", "room_type"]


class FeatureFlagViewSet(viewsets.ViewSet):
    """Module on/off switches for the current branch. Anyone may read; settings.manage may change."""

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True
    required_permissions = {"partial_update": "settings.manage", "update": "settings.manage"}
    lookup_field = "code"

    def _rows(self, branch):
        values = branch_features(branch)
        return [{"code": code, "label": info["label"], "enabled": values[code]} for code, info in FEATURES.items()]

    def list(self, request):
        return Response(FeatureFlagSerializer(self._rows(request.branch), many=True).data)

    def partial_update(self, request, code=None):
        if code not in FEATURES:
            raise NotFound("Unknown feature.")
        serializer = FeatureFlagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enabled = serializer.validated_data["enabled"]
        flag, created = BranchFeatureFlag.objects.get_or_create(
            organization_id=request.user.organization_id, branch=request.branch, code=code,
            defaults={"enabled": enabled, "created_by": request.user, "updated_by": request.user},
        )
        if not created:
            flag.enabled = enabled
            flag.updated_by = request.user
            flag.save(update_fields=["enabled", "updated_by", "updated_at"])
        log_action(request, "update", flag, changes={"code": code, "enabled": enabled})
        return Response({"code": code, "label": FEATURES[code]["label"], "enabled": enabled})

    update = partial_update


class AdditionalFeatureViewSet(viewsets.ViewSet):
    """
    Optional extra features for the whole organization ("Additional settings").
    Everyone logged in may read them (the screens use them); only organization admins may switch them.
    """

    permission_classes = [IsAuthenticated, BranchPermission]
    lookup_field = "code"

    def _rows(self, organization_id):
        effective = organization_features(organization_id)
        saved = dict(OrganizationFeature.objects.filter(organization_id=organization_id).values_list("code", "enabled"))
        return [{
            "code": code, "group": info["group"], "label": info["label"], "requires": info.get("requires", ""),
            "switched_on": saved.get(code, info["default"]), "enabled": effective[code],
        } for code, info in ADDITIONAL_FEATURES.items()]

    def list(self, request):
        return Response(self._rows(request.user.organization_id))

    def partial_update(self, request, code=None):
        if not (request.user.is_org_admin and user_has_perm(request.user, "settings.manage")):
            self.permission_denied(request, message="Only an organization admin can change additional settings.")
        if code not in ADDITIONAL_FEATURES:
            raise NotFound("Unknown feature.")
        serializer = FeatureFlagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enabled = serializer.validated_data["enabled"]
        flag, created = OrganizationFeature.objects.get_or_create(
            organization_id=request.user.organization_id, code=code,
            defaults={"enabled": enabled, "created_by": request.user, "updated_by": request.user},
        )
        if not created:
            flag.enabled = enabled
            flag.updated_by = request.user
            flag.save(update_fields=["enabled", "updated_by", "updated_at"])
        log_action(request, "update", flag, changes={"code": code, "enabled": enabled})
        return Response(self._rows(request.user.organization_id))

    update = partial_update


class AdditionalChoiceViewSet(viewsets.ViewSet):
    """Additional settings that are a choice (e.g. the default label format). Read: everyone; change: org admins."""

    permission_classes = [IsAuthenticated, BranchPermission]
    lookup_field = "code"

    def _rows(self, organization_id):
        chosen = organization_choices(organization_id)
        return [{"code": code, "group": info["group"], "label": info["label"], "options": info["options"],
                 "requires": info.get("requires", ""), "value": chosen[code]} for code, info in ADDITIONAL_CHOICES.items()]

    def list(self, request):
        return Response(self._rows(request.user.organization_id))

    def partial_update(self, request, code=None):
        if not (request.user.is_org_admin and user_has_perm(request.user, "settings.manage")):
            self.permission_denied(request, message="Only an organization admin can change additional settings.")
        info = ADDITIONAL_CHOICES.get(code)
        if info is None:
            raise NotFound("Unknown setting.")
        value = request.data.get("value")
        if value not in info["options"]:
            raise ValidationError({"value": f"Choose one of: {', '.join(info['options'])}."})
        row, _ = OrganizationChoice.objects.update_or_create(
            organization_id=request.user.organization_id, code=code,
            defaults={"value": value, "updated_by": request.user, "created_by": request.user},
        )
        log_action(request, "update", row, changes={"code": code, "value": value})
        return Response(self._rows(request.user.organization_id))

    update = partial_update
