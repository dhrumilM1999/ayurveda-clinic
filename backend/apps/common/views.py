from rest_framework import serializers

from .masters_catalog import CATEGORIES
from .models import MasterValue
from .viewsets import AuditedModelViewSet


class MasterValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterValue
        fields = ["id", "category", "code", "label", "label_gu", "label_hi", "sort_order", "is_active"]
        read_only_fields = ["id"]

    def validate_category(self, value):
        if value not in CATEGORIES:
            raise serializers.ValidationError("Unknown list.")
        return value


class MasterValueViewSet(AuditedModelViewSet):
    """Dropdown values. Everyone may read; settings.manage may change. ?category=title"""

    queryset = MasterValue.objects.all()
    serializer_class = MasterValueSerializer
    pagination_class = None
    filterset_fields = ["category", "is_active"]
    required_permissions = {
        "list": None, "retrieve": None,
        "create": "settings.manage", "update": "settings.manage",
        "partial_update": "settings.manage", "destroy": "settings.manage",
    }
