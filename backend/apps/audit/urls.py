from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import AuditLogViewSet, ErrorLogViewSet, ErrorReportView

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("error-logs", ErrorLogViewSet, basename="error-log")

# The report address comes first so it is not mistaken for an error-log id
urlpatterns = [path("error-logs/report/", ErrorReportView.as_view(), name="error-report")] + router.urls
