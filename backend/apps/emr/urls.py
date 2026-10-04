from rest_framework.routers import DefaultRouter

from .views import ExamTemplateViewSet, VisitViewSet

router = DefaultRouter()
router.register("visits", VisitViewSet, basename="visit")
router.register("exam-templates", ExamTemplateViewSet, basename="exam-template")

urlpatterns = router.urls
