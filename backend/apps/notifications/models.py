"""A record of every outgoing message (SMS now; WhatsApp and email later)."""
import uuid

from django.db import models


class OutboundMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    channel = models.CharField(max_length=20, default="sms")
    provider = models.CharField(max_length=50)
    purpose = models.CharField(max_length=50, blank=True)
    to = models.CharField(max_length=50)
    body = models.TextField()
    status = models.CharField(max_length=20, default="sent")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
