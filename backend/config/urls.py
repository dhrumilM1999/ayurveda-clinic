"""Top-level URL map. Every module's API lives under /api/v1/."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({"status": "ok"})


admin.site.site_header = "Ayurveda Clinic — Admin"
admin.site.site_title = "Ayurveda Clinic Admin"

api_v1 = [
    path("health/", health, name="health"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.organizations.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.common.urls")),
    path("", include("apps.patients.urls")),
    path("", include("apps.appointments.urls")),
    path("", include("apps.emr.urls")),
    path("", include("apps.medicines.urls")),
    path("", include("apps.prescriptions.urls")),
    path("", include("apps.pharmacy.urls")),
    path("", include("apps.billing.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.documents.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
