from django.contrib import admin

from .models import Medicine


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    """Use the app's Medicines screen to edit (it keeps the version history and audit log)."""

    list_display = ("name", "kind", "dosage_form", "mrp", "schedule_e1", "contains_metals", "is_active", "version")
    list_filter = ("kind", "is_active", "schedule_e1", "contains_metals")
    search_fields = ("name", "synonyms")
    readonly_fields = [f.name for f in Medicine._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
