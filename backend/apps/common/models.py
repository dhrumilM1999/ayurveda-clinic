"""
Base models shared by every module. ASK FIRST before editing.

Every main table gets:
- a UUID id (a long random id that is safe to show in links),
- created_at / updated_at and created_by / updated_by,
- soft delete: rows are only *marked* deleted (is_deleted, deleted_at), never removed.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Bulk delete only marks rows as deleted."""
        return self.update(is_deleted=True, deleted_at=timezone.now())


class ActiveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: hides soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Includes soft-deleted rows. Use only for audits and data-rights requests."""


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", editable=False,
    )
    is_deleted = models.BooleanField(default=False, db_index=True, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, user=None):
        """Soft delete: mark the row as deleted instead of removing it."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        fields = ["is_deleted", "deleted_at", "updated_at"]
        if user is not None:
            self.updated_by = user
            fields.append("updated_by")
        self.save(update_fields=fields)


class OrgScopedModel(BaseModel):
    """A row that belongs to one organization (clinic group)."""

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="+", db_index=True,
    )

    class Meta:
        abstract = True


class BranchScopedModel(OrgScopedModel):
    """A row that belongs to one branch of an organization."""

    branch = models.ForeignKey(
        "organizations.Branch", on_delete=models.PROTECT, related_name="+", db_index=True,
    )

    class Meta:
        abstract = True


class MasterValue(OrgScopedModel):
    """
    One value of a dropdown list (title, blood group, relation, ...), editable by staff.
    The lists and their starting values are in masters_catalog.py.
    """

    category = models.CharField(max_length=50, db_index=True)
    code = models.SlugField(max_length=60)
    label = models.CharField(max_length=150)
    label_gu = models.CharField("Label (Gujarati)", max_length=150, blank=True)
    label_hi = models.CharField("Label (Hindi)", max_length=150, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "sort_order", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "category", "code"],
                condition=models.Q(is_deleted=False),
                name="uniq_master_value_code",
            )
        ]

    def __str__(self):
        return f"{self.category}: {self.label}"
