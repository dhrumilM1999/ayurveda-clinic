from django.contrib import admin

from .models import ConsentPurpose, Patient, PatientConsent


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Read-only in the technical admin: use the app (it writes the audit log)."""

    list_display = ("uhid", "first_name", "last_name", "gender", "city", "registration_date", "organization")
    search_fields = ("uhid", "first_name", "last_name")
    fields = ("uhid", "first_name", "middle_name", "last_name", "gender", "registration_date", "organization")
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConsentPurpose)
class ConsentPurposeAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "is_required", "version", "is_active", "organization")


@admin.register(PatientConsent)
class PatientConsentAdmin(admin.ModelAdmin):
    list_display = ("patient", "purpose", "granted", "method", "created_at")
    readonly_fields = [f.name for f in PatientConsent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
