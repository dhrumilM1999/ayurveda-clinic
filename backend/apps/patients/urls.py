from rest_framework.routers import DefaultRouter

from .views import ConsentPurposeViewSet, ConsentViewSet, DocumentViewSet, PatientViewSet, VitalViewSet

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")
router.register("patient-vitals", VitalViewSet, basename="patient-vital")
router.register("patient-documents", DocumentViewSet, basename="patient-document")
router.register("patient-consents", ConsentViewSet, basename="patient-consent")
router.register("consent-purposes", ConsentPurposeViewSet, basename="consent-purpose")

urlpatterns = router.urls
