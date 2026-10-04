from django.contrib import admin

from .models import Prescription


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """Read-only: prescriptions are written and read in the app (audit log)."""

    list_display = ("created_at", "patient", "doctor", "branch", "status")
    list_filter = ("status", "branch")
    fields = ("patient", "doctor", "branch", "status", "finalized_at")
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
