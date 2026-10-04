from rest_framework import serializers

from .models import Branch, Organization, Room, RoomType


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id", "name", "short_name", "legal_name", "gstin", "phone", "email",
            "address", "logo", "default_language", "uhid_prefix", "multi_branch", "updated_at",
        ]
        read_only_fields = ["id", "logo", "updated_at"]

    def validate_multi_branch(self, value):
        if self.instance and value != self.instance.multi_branch and not self.context["request"].user.is_org_admin:
            raise serializers.ValidationError("Only the organization admin (owner) can change this.")
        return value

    def validate_uhid_prefix(self, value):
        value = value.strip().upper()
        if not value.isalnum():
            raise serializers.ValidationError("Use only letters and numbers, e.g. AY.")
        return value


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id", "name", "code", "address", "city", "state", "pincode",
            "phone", "email", "gstin", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value):
        value = value.strip().upper()
        org_id = self.context["request"].user.organization_id
        clash = Branch.objects.filter(organization_id=org_id, code=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("Another branch already uses this code.")
        return value


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = ["id", "name", "is_active", "sort_order"]
        read_only_fields = ["id"]


class RoomSerializer(serializers.ModelSerializer):
    room_type_name = serializers.CharField(source="room_type.name", default="", read_only=True)

    class Meta:
        model = Room
        fields = [
            "id", "name", "room_type", "room_type_name", "capacity", "notes", "is_active",
            "branch", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "branch", "created_at", "updated_at"]

    def validate_room_type(self, value):
        if value and value.organization_id != self.context["request"].user.organization_id:
            raise serializers.ValidationError("Unknown room type.")
        return value


class FeatureFlagSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    enabled = serializers.BooleanField()
