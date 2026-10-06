from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdditionalChoiceViewSet, AdditionalFeatureViewSet, BranchViewSet, CurrentOrganizationView, FeatureFlagViewSet,
    OrganizationLogoView, RoomTypeViewSet, RoomViewSet,
)

router = DefaultRouter()
router.register("branches", BranchViewSet, basename="branch")
router.register("room-types", RoomTypeViewSet, basename="room-type")
router.register("rooms", RoomViewSet, basename="room")
router.register("feature-flags", FeatureFlagViewSet, basename="feature-flag")
router.register("additional-features", AdditionalFeatureViewSet, basename="additional-feature")
router.register("additional-choices", AdditionalChoiceViewSet, basename="additional-choice")

urlpatterns = [
    path("organization/", CurrentOrganizationView.as_view(), name="current-organization"),
    path("organization/logo/", OrganizationLogoView.as_view(), name="organization-logo"),
] + router.urls
