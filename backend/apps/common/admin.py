from django.contrib import admin

from .models import MasterValue


@admin.register(MasterValue)
class MasterValueAdmin(admin.ModelAdmin):
    list_display = ("category", "label", "label_gu", "label_hi", "code", "sort_order", "is_active", "organization")
    list_filter = ("category", "is_active", "organization")
    search_fields = ("label", "label_gu", "label_hi", "code")
