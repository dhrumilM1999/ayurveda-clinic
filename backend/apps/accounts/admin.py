from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import DoctorSchedule, Role, User, UserBranchRole


class UserBranchRoleInline(admin.TabularInline):
    model = UserBranchRole
    fk_name = "user"
    fields = ("branch", "role", "organization")
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("full_name",)
    list_display = ("username", "full_name", "organization", "is_doctor", "is_org_admin", "is_active")
    list_filter = ("organization", "is_doctor", "is_org_admin", "is_active")
    search_fields = ("username", "full_name", "phone", "email")
    inlines = [UserBranchRoleInline]
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Person", {"fields": ("full_name", "email", "phone", "preferred_language", "designation")}),
        ("Doctor", {"fields": ("is_doctor", "qualification", "registration_number")}),
        ("Access", {"fields": ("organization", "is_org_admin", "is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {"fields": ("username", "full_name", "organization", "password1", "password2")}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "requires_2fa", "is_system")
    list_filter = ("organization",)


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ("doctor", "branch", "weekday", "start_time", "end_time", "slot_minutes", "is_active")
    list_filter = ("branch", "weekday")
