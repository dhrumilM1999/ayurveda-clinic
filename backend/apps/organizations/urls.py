from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdditionalChoiceViewSet, AdditionalFeatureViewSet, BranchLetterheadImageView, BranchViewSet, CurrentOrganizationView, FeatureFlagViewSet,
    OrganizationLogoView, PublicBrandingLogoView, PublicBrandingView, RoomTypeViewSet, RoomViewSet,
)

router = DefaultRouter()
router.register("branches", BranchViewSet, basename="branch")
router.register("room-types", RoomTypeViewSet, basename="room-type")
router.register("rooms", RoomViewSet, basename="room")
router.register("feature-flags", FeatureFlagViewSet, basename="feature-flag")
router.register("additional-features", AdditionalFeatureViewSet, basename="additional-feature")
router.register("additional-choices", AdditionalChoiceViewSet, basename="additional-choice")

urlpatterns = [
    path("branding/", PublicBrandingView.as_view(), name="public-branding"),
    path("branding/logo/", PublicBrandingLogoView.as_view(), name="public-branding-logo"),
    path("organization/", CurrentOrganizationView.as_view(), name="current-organization"),
    path("organization/logo/", OrganizationLogoView.as_view(), name="organization-logo"),
    path("branches/<str:pk>/letterhead-image/", BranchLetterheadImageView.as_view(), name="branch-letterhead-image"),
] + router.urls
