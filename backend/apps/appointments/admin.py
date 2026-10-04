from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Read-only in the technical admin: use the app (it writes the audit log)."""

    list_display = ("date", "start_time", "token_number", "patient", "doctor", "branch", "status")
    list_filter = ("status", "kind", "branch")
    date_hierarchy = "date"
    fields = ("date", "start_time", "end_time", "token_number", "patient", "doctor", "branch", "status", "kind")
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
