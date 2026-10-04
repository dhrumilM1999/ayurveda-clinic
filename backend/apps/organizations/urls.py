from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BranchViewSet, CurrentOrganizationView, FeatureFlagViewSet, RoomTypeViewSet, RoomViewSet

router = DefaultRouter()
router.register("branches", BranchViewSet, basename="branch")
router.register("room-types", RoomTypeViewSet, basename="room-type")
router.register("rooms", RoomViewSet, basename="room")
router.register("feature-flags", FeatureFlagViewSet, basename="feature-flag")

urlpatterns = [
    path("organization/", CurrentOrganizationView.as_view(), name="current-organization"),
] + router.urls
