from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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


class TranslateView(APIView):
    """
    POST /translate/ {text: "Triphala Churna", targets: ["gu", "hi"]} -> {"gu": "...", "hi": "..."}
    A suggestion only (the screen fills the boxes and the user edits). 503 "AI is offline" when Ollama is not running.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from rest_framework.exceptions import ValidationError

        from .translate import LANGUAGE_NAMES, TranslateUnavailable, translate

        text = str(request.data.get("text", "")).strip()
        targets = [t for t in request.data.get("targets", ["gu", "hi"]) if t in LANGUAGE_NAMES]
        if not text or len(text) > 300 or not targets:
            raise ValidationError({"text": "Write the English text first (at most 300 letters)."})
        try:
            return Response(translate(text, targets))
        except TranslateUnavailable as error:
            return Response({"detail": str(error)}, status=503)
