from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from apps.audit.services import log_action
from apps.organizations.models import Branch

from .models import DoctorSchedule, Role, User, UserBranchRole
from .permissions_catalog import ALL_PERMISSION_CODES
from .services import user_has_perm


# --- Login --------------------------------------------------------------------
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class VerifyOtpSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    code = serializers.CharField(max_length=10)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "The current password is wrong."})
        validate_password(attrs["new_password"], user)
        return attrs


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["preferred_language"]


# --- Roles --------------------------------------------------------------------
class RoleSerializer(serializers.ModelSerializer):
    code = serializers.SlugField(required=False, allow_blank=True)
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "name", "code", "description", "permissions", "requires_2fa", "is_system", "user_count"]
        read_only_fields = ["id", "is_system", "user_count"]

    def get_user_count(self, obj):
        return obj.assignments.count()

    def validate_permissions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of permission codes.")
        unknown = set(value) - ALL_PERMISSION_CODES
        if unknown:
            raise serializers.ValidationError(f"Unknown permission codes: {', '.join(sorted(unknown))}")
        return sorted(set(value))

    def validate(self, attrs):
        org_id = self.context["request"].user.organization_id
        if self.instance is not None and self.instance.is_system:
            attrs.pop("code", None)  # system role codes never change
        elif self.instance is None or "code" in attrs:
            name = attrs.get("name") or self.instance.name
            attrs["code"] = (attrs.get("code") or slugify(name))[:50]
        code = attrs.get("code")
        if code:
            clash = Role.objects.filter(organization_id=org_id, code=code)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError({"code": "Another role already uses this code."})
        return attrs


# --- Staff --------------------------------------------------------------------
class BranchRoleSerializer(serializers.Serializer):
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)


class StaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    branch_roles = BranchRoleSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "full_name", "email", "phone", "preferred_language", "designation",
            "is_doctor", "qualification", "registration_number", "is_org_admin", "is_active",
            "last_login", "created_at", "password", "branch_roles",
        ]
        read_only_fields = ["id", "last_login", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["branch_roles"] = BranchRoleSerializer(
            instance.branch_roles.select_related("branch", "role"), many=True
        ).data
        return data

    # --- validation ---
    def validate_username(self, value):
        value = value.strip().lower()
        clash = User.all_objects.filter(username=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_branch_roles(self, value):
        org_id = self.context["request"].user.organization_id
        seen = set()
        for item in value:
            if item["branch"].organization_id != org_id or item["role"].organization_id != org_id:
                raise serializers.ValidationError("Unknown branch or role.")
            if item["branch"].id in seen:
                raise serializers.ValidationError("A user can have only one role per branch.")
            seen.add(item["branch"].id)
        return value

    def validate(self, attrs):
        actor = self.context["request"].user
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "A password is required for a new user."})
        if attrs.get("password"):
            candidate = User(username=attrs.get("username", getattr(self.instance, "username", "")),
                             full_name=attrs.get("full_name", getattr(self.instance, "full_name", "")))
            try:
                validate_password(attrs["password"], candidate)
            except DjangoValidationError as error:
                raise serializers.ValidationError({"password": list(error.messages)})
        if not actor.is_org_admin:
            if "is_org_admin" in attrs and attrs["is_org_admin"] != getattr(self.instance, "is_org_admin", False):
                raise serializers.ValidationError({"is_org_admin": "Only organization admins can change this."})
            if self.instance is not None and self.instance.is_org_admin:
                raise serializers.ValidationError("Only organization admins can edit an organization admin.")
            if "branch_roles" in attrs:
                old = set()
                if self.instance is not None:
                    old = {(a.branch_id, a.role_id) for a in self.instance.branch_roles.all()}
                new = {(i["branch"].id, i["role"].id) for i in attrs["branch_roles"]}
                for branch_id, _ in old ^ new:
                    branch = Branch.objects.get(pk=branch_id)
                    if not user_has_perm(actor, "staff.manage", branch):
                        raise serializers.ValidationError(
                            {"branch_roles": f"You cannot change roles in branch {branch.name}."}
                        )
        return attrs

    # --- saving ---
    @transaction.atomic
    def create(self, validated_data):
        roles = validated_data.pop("branch_roles", [])
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        self._apply_roles(user, roles)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        roles = validated_data.pop("branch_roles", None)
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        if roles is not None:
            self._apply_roles(instance, roles)
        return instance

    def _apply_roles(self, user, roles):
        request = self.context["request"]
        actor = request.user
        existing = {a.branch_id: a for a in user.branch_roles.all()}
        wanted = {item["branch"].id: item["role"] for item in roles}
        changes = []
        for branch_id, role in wanted.items():
            current = existing.get(branch_id)
            if current is None:
                UserBranchRole.objects.create(
                    organization_id=user.organization_id, user=user, branch_id=branch_id, role=role,
                    created_by=actor, updated_by=actor,
                )
                changes.append({"branch": str(branch_id), "role": role.code, "change": "added"})
            elif current.role_id != role.id:
                current.role = role
                current.updated_by = actor
                current.save(update_fields=["role", "updated_by", "updated_at"])
                changes.append({"branch": str(branch_id), "role": role.code, "change": "changed"})
        for branch_id, assignment in existing.items():
            if branch_id not in wanted:
                assignment.delete(user=actor)
                changes.append({"branch": str(branch_id), "role": assignment.role.code, "change": "removed"})
        if changes:
            log_action(request, "update", user, changes={"branch_roles": changes})


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False)

    def validate_password(self, value):
        validate_password(value, self.context.get("user"))
        return value


# --- Doctor schedules ---------------------------------------------------------
class DoctorScheduleSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = [
            "id", "doctor", "doctor_name", "weekday", "start_time", "end_time",
            "slot_minutes", "is_active", "branch",
        ]
        read_only_fields = ["id", "branch"]

    def validate_doctor(self, value):
        if value.organization_id != self.context["request"].user.organization_id or not value.is_doctor:
            raise serializers.ValidationError("Please choose a doctor.")
        return value

    def validate_slot_minutes(self, value):
        if not 5 <= value <= 120:
            raise serializers.ValidationError("Slot length must be between 5 and 120 minutes.")
        return value

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        doctor = attrs.get("doctor", getattr(self.instance, "doctor", None))
        weekday = attrs.get("weekday", getattr(self.instance, "weekday", None))
        # A doctor cannot sit in two places at the same time (checked across all branches).
        overlap = DoctorSchedule.objects.filter(
            doctor=doctor, weekday=weekday, is_active=True, start_time__lt=end, end_time__gt=start,
        )
        if self.instance:
            overlap = overlap.exclude(pk=self.instance.pk)
        if overlap.exists():
            raise serializers.ValidationError("This time overlaps another schedule of the same doctor.")
        return attrs
