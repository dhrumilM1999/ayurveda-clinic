from django.contrib import admin

from .models import Certificate, IssuedDocument


@admin.register(IssuedDocument)
class IssuedDocumentAdmin(admin.ModelAdmin):
    list_display = ("kind", "number", "branch", "issued_on", "print_count", "is_cancelled")
    list_filter = ("kind", "branch", "is_cancelled")
    readonly_fields = ("token",)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("number", "kind", "branch", "issued_on", "is_cancelled")
    list_filter = ("kind", "branch", "is_cancelled")
