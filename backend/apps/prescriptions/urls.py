from rest_framework.routers import DefaultRouter

from .handwriting_views import HandwrittenPrescriptionViewSet
from .views import PrescriptionTemplateViewSet, PrescriptionViewSet

router = DefaultRouter()
router.register("prescriptions", PrescriptionViewSet, basename="prescription")
router.register("handwritten-prescriptions", HandwrittenPrescriptionViewSet, basename="handwritten-prescription")
router.register("prescription-templates", PrescriptionTemplateViewSet, basename="prescription-template")

urlpatterns = router.urls
