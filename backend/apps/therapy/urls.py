from rest_framework.routers import DefaultRouter

from .views import TherapyPlanViewSet, TherapySessionViewSet, TherapyTypeViewSet

router = DefaultRouter()
router.register("therapies", TherapyTypeViewSet, basename="therapy")
router.register("therapy-plans", TherapyPlanViewSet, basename="therapy-plan")
router.register("therapy-sessions", TherapySessionViewSet, basename="therapy-session")

urlpatterns = router.urls
