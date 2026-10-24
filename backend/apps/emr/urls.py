from rest_framework.routers import DefaultRouter

from .investigations import InvestigationViewSet, LabTestViewSet
from .views import ExamTemplateViewSet, VisitViewSet

router = DefaultRouter()
router.register("visits", VisitViewSet, basename="visit")
router.register("exam-templates", ExamTemplateViewSet, basename="exam-template")
router.register("lab-tests", LabTestViewSet, basename="lab-test")
router.register("investigations", InvestigationViewSet, basename="investigation")

urlpatterns = router.urls
