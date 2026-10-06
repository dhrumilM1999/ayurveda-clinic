from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CertificateViewSet, DocumentPdfView, PrescriptionShareView, VerifyView

router = DefaultRouter()
router.register("certificates", CertificateViewSet, basename="certificate")

urlpatterns = [
    path("documents/prescription/<uuid:pk>/whatsapp/", PrescriptionShareView.as_view(), name="prescription-whatsapp"),
    path("documents/<slug:kind>/<uuid:pk>/", DocumentPdfView.as_view(), name="document-pdf"),
    path("verify/<str:token>/", VerifyView.as_view(), name="verify-document"),
] + router.urls
