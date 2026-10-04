from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from django.conf import settings

from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet

from . import otp
from .models import DoctorSchedule, LoginChallenge, Role, User
from .permissions_catalog import PERMISSIONS
from .serializers import (
    ChangePasswordSerializer, DoctorScheduleSerializer, LoginSerializer, LogoutSerializer,
    MeUpdateSerializer, RoleSerializer, SetPasswordSerializer, StaffSerializer, VerifyOtpSerializer,
)
from .services import accessible_branches, branch_permissions, doctors_in_branch, user_requires_2fa
from .throttles import LoginIPThrottle, LoginUserThrottle, OtpThrottle


# --- Login / logout -----------------------------------------------------------
def issue_tokens(request, user):
    refresh = RefreshToken.for_user(user)
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    log_action(request, "login", user, user=user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class LoginView(APIView):
    """Step 1 of login: username + password. Doctors and admins then get an OTP."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginIPThrottle, LoginUserThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"].strip().lower()
        user = authenticate(request, username=username, password=serializer.validated_data["password"])
        if user is None:
            log_action(request, "login_failed", username=username, object_type="accounts.user", object_repr=username)
            return Response({"detail": "Wrong username or password."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.organization_id:
            return Response({"detail": "This account is not linked to a clinic."}, status=status.HTTP_403_FORBIDDEN)

        if user_requires_2fa(user):
            challenge, code = otp.start_challenge(user)
            log_action(request, "otp_sent", user, user=user)
            data = {
                "otp_required": True,
                "challenge_id": str(challenge.id),
                "phone_hint": otp.phone_hint(user),
            }
            if settings.SHOW_DEV_OTP_ON_SCREEN:
                data["dev_otp"] = code
            return Response(data)

        return Response({"otp_required": False, **issue_tokens(request, user)})


class VerifyOtpView(APIView):
    """Step 2 of login for doctors and admins: check the OTP."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OtpThrottle]

    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        challenge = (
            LoginChallenge.objects.filter(id=serializer.validated_data["challenge_id"])
            .select_related("user").first()
        )
        if challenge is None or not challenge.user.is_active or not otp.check_challenge(
            challenge, serializer.validated_data["code"]
        ):
            if challenge is not None:
                log_action(request, "otp_failed", challenge.user, user=challenge.user)
            return Response(
                {"detail": "The OTP is wrong or has expired. Please log in again if it keeps failing."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(issue_tokens(request, challenge.user))


class RefreshView(TokenRefreshView):
    throttle_classes = [OtpThrottle]


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            pass  # already expired or used: the user is logged out anyway
        log_action(request, "logout", request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Who am I, which branches can I use, and what may I do in each one."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        org = user.organization
        branches = []
        roles = {a.branch_id: a.role for a in user.branch_roles.select_related("role")}
        allowed = list(accessible_branches(user))
        if org and not org.multi_branch:
            # Single-branch mode: only the main branch (unless the user does not work there).
            main = org.main_branch()
            if main and any(b.id == main.id for b in allowed):
                allowed = [main]
        for branch in allowed:
            role = roles.get(branch.id)
            branches.append({
                "id": str(branch.id),
                "name": branch.name,
                "code": branch.code,
                "role": {"code": role.code, "name": role.name} if role else None,
                "permissions": sorted(branch_permissions(user, branch)),
            })
        return Response({
            "user": {
                "id": str(user.id),
                "username": user.username,
                "full_name": user.full_name,
                "is_org_admin": user.is_org_admin,
                "is_doctor": user.is_doctor,
                "preferred_language": user.preferred_language,
            },
            "organization": {"id": str(org.id), "name": org.name, "multi_branch": org.multi_branch} if org else None,
            "branches": branches,
            "idle_timeout_minutes": settings.IDLE_TIMEOUT_MINUTES,
        })

    def patch(self, request):
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        log_action(request, "password_change", request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Roles --------------------------------------------------------------------
class RoleViewSet(AuditedModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_prefix = "roles"
    required_permissions = {"catalog": "roles.view"}
    pagination_class = None
    search_fields = ["name", "code"]

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        """All permission codes, grouped by module, for the role editor."""
        return Response([
            {"code": code, "label": label, "group": code.split(".")[0]} for code, label in PERMISSIONS.items()
        ])

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "Built-in roles cannot be deleted. You can change their permissions."})
        if instance.assignments.exists():
            raise ValidationError({"detail": "This role is still given to some staff. Change their role first."})
        super().perform_destroy(instance)


# --- Staff --------------------------------------------------------------------
class StaffViewSet(AuditedModelViewSet):
    queryset = User.objects.all()
    serializer_class = StaffSerializer
    permission_prefix = "staff"
    required_permissions = {"set_password": "staff.manage"}
    search_fields = ["username", "full_name", "phone", "email"]
    filterset_fields = ["is_doctor", "is_active", "is_org_admin"]
    ordering_fields = ["full_name", "created_at", "last_login"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_org_admin:
            # Only staff who work in branches I can see.
            qs = qs.filter(
                branch_roles__branch__in=accessible_branches(user), branch_roles__is_deleted=False,
            ).distinct()
        branch_id = self.request.query_params.get("branch")
        if branch_id:
            qs = qs.filter(branch_roles__branch_id=branch_id, branch_roles__is_deleted=False).distinct()
        return qs

    def perform_destroy(self, instance):
        actor = self.request.user
        if instance.pk == actor.pk:
            raise ValidationError({"detail": "You cannot remove your own account."})
        if instance.is_org_admin and not actor.is_org_admin:
            raise ValidationError({"detail": "Only organization admins can remove an organization admin."})
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        user = self.get_object()
        if user.is_org_admin and not request.user.is_org_admin:
            self.permission_denied(request, message="Only organization admins can do this.")
        serializer = SetPasswordSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        log_action(request, "password_change", user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Doctor schedules ---------------------------------------------------------
class DoctorScheduleViewSet(AuditedModelViewSet):
    """Doctor timings in the current branch."""

    queryset = DoctorSchedule.objects.select_related("doctor")
    serializer_class = DoctorScheduleSerializer
    permission_prefix = "schedules"
    branch_scoped = True
    required_permissions = {"doctors": "schedules.view"}
    filterset_fields = ["doctor", "weekday", "is_active"]
    pagination_class = None

    @action(detail=False, methods=["get"])
    def doctors(self, request):
        """Doctors who work in the current branch (for dropdowns)."""
        doctors = (
            doctors_in_branch(request.branch)
            .annotate(schedule_count=Count("schedules", filter=Q(schedules__branch=request.branch, schedules__is_deleted=False)))
        )
        return Response([
            {"id": str(d.id), "full_name": d.full_name, "schedule_count": d.schedule_count} for d in doctors
        ])
