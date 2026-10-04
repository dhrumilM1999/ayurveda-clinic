"""Serializer pieces shared by all modules."""
from rest_framework import serializers

from .models import MasterValue


def master_dict(value):
    if value is None:
        return None
    return {"id": str(value.id), "code": value.code, "label": value.label,
            "label_gu": value.label_gu, "label_hi": value.label_hi}


class MasterField(serializers.PrimaryKeyRelatedField):
    """A dropdown value from one master list, e.g. MasterField("blood_group")."""

    def __init__(self, category, **kwargs):
        self.category = category
        kwargs.setdefault("queryset", MasterValue.objects.all())
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        org_id = self.context["request"].user.organization_id
        if value.organization_id != org_id or value.category != self.category:
            raise serializers.ValidationError("Unknown value for this list.")
        return value

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return master_dict(value)
