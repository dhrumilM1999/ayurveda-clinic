from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EnquiryViewSet, PublicEnquiryFormView, PublicEnquiryView

router = DefaultRouter()
router.register("enquiries", EnquiryViewSet, basename="enquiry")

urlpatterns = [
    path("public/enquiry-form/", PublicEnquiryFormView.as_view(), name="public-enquiry-form"),
    path("public/enquiries/", PublicEnquiryView.as_view(), name="public-enquiry"),
] + router.urls
