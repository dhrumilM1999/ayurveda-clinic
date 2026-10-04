from django.contrib import admin

from .models import ExamTemplate, Visit


@admin.register(ExamTemplate)
class ExamTemplateAdmin(admin.ModelAdmin):
    """Templates can be switched off or renamed here. Editing the questions needs care (see templates_catalog.py)."""

    list_display = ("name", "code", "version", "kind", "is_active", "organization")
    list_filter = ("kind", "is_active")


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    """Read-only in the technical admin: medical notes are only shown in the app (with the audit log)."""

    list_display = ("visit_date", "patient", "doctor", "branch", "status")
    list_filter = ("status", "branch")
    fields = ("visit_date", "patient", "doctor", "branch", "status", "follow_up_date")
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
