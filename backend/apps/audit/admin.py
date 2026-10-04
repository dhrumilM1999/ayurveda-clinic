from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only: audit logs can never be changed or deleted."""

    list_display = ("created_at", "username", "action", "object_type", "object_repr", "branch", "ip_address")
    list_filter = ("action", "object_type", "branch")
    search_fields = ("username", "object_repr", "object_id")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
