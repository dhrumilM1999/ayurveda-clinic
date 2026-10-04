from django.contrib import admin

from .models import OutboundMessage


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "channel", "provider", "purpose", "to", "status")
    list_filter = ("channel", "provider", "status")
    readonly_fields = [f.name for f in OutboundMessage._meta.fields]
