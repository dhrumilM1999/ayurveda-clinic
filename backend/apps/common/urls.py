from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MasterValueViewSet, TranslateView

router = DefaultRouter()
router.register("masters", MasterValueViewSet, basename="master")

urlpatterns = [path("translate/", TranslateView.as_view(), name="translate")] + router.urls
