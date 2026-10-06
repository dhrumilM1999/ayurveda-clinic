from django.urls import path

from .views import ReportView, TodayDashboardView

urlpatterns = [
    path("dashboard/today/", TodayDashboardView.as_view(), name="dashboard-today"),
    path("reports/<str:code>/", ReportView.as_view(), name="report"),
]
