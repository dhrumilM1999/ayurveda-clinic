from django.urls import path

from .views import TodayDashboardView

urlpatterns = [path("dashboard/today/", TodayDashboardView.as_view(), name="dashboard-today")]
