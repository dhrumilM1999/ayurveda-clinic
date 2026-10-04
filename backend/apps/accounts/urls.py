from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ChangePasswordView, DoctorScheduleViewSet, LoginView, LogoutView, MeView, RefreshView,
    RoleViewSet, StaffViewSet, VerifyOtpView,
)

router = DefaultRouter()
router.register("roles", RoleViewSet, basename="role")
router.register("staff", StaffViewSet, basename="staff")
router.register("doctor-schedules", DoctorScheduleViewSet, basename="doctor-schedule")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/verify-otp/", VerifyOtpView.as_view(), name="auth-verify-otp"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
] + router.urls
