from rest_framework.routers import DefaultRouter

from .views import PrescriptionTemplateViewSet, PrescriptionViewSet

router = DefaultRouter()
router.register("prescriptions", PrescriptionViewSet, basename="prescription")
router.register("prescription-templates", PrescriptionTemplateViewSet, basename="prescription-template")

urlpatterns = router.urls
