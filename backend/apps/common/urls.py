from rest_framework.routers import DefaultRouter

from .views import MasterValueViewSet

router = DefaultRouter()
router.register("masters", MasterValueViewSet, basename="master")

urlpatterns = router.urls
