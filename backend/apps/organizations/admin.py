from django.contrib import admin

from .models import Branch, BranchFeatureFlag, Organization, Room, RoomType


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "gstin", "phone")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code", "city")


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "sort_order", "is_active")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "room_type", "capacity", "is_active")
    list_filter = ("branch", "room_type", "is_active")


@admin.register(BranchFeatureFlag)
class BranchFeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("branch", "code", "enabled")
    list_filter = ("branch", "code")
