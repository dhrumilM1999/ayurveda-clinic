from django.urls import path
from rest_framework.routers import DefaultRouter

from .print_settings_views import PaperDefaultsView, PrintPreviewView, PrintSettingsView
from .views import CertificateViewSet, DocumentPdfView, PrescriptionShareView, VerifyView

router = DefaultRouter()
router.register("certificates", CertificateViewSet, basename="certificate")

urlpatterns = [
    path("print-settings/", PrintSettingsView.as_view(), name="print-settings"),
    path("print-settings/preview/", PrintPreviewView.as_view(), name="print-settings-preview"),
    path("print-settings/paper-defaults/", PaperDefaultsView.as_view(), name="print-paper-defaults"),
    path("documents/prescription/<uuid:pk>/whatsapp/", PrescriptionShareView.as_view(), name="prescription-whatsapp"),
    path("documents/<slug:kind>/<uuid:pk>/", DocumentPdfView.as_view(), name="document-pdf"),
    path("verify/<str:token>/", VerifyView.as_view(), name="verify-document"),
] + router.urls
