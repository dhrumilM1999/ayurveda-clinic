"""
log_action(): the one function every module calls to write an audit log entry.

Example:
    log_action(request, "view", patient)
    log_action(request, "print", prescription, changes={"copy": "duplicate"})
"""
from apps.common.utils import client_ip

from .models import AuditLog


def log_action(request, action, obj=None, *, user=None, organization=None, branch=None,
               changes=None, object_type="", object_repr="", username=""):
    if user is None and request is not None and getattr(request, "user", None) is not None:
        user = request.user if request.user.is_authenticated else None
    if organization is None and user is not None:
        organization = user.organization
    if branch is None and request is not None:
        branch = getattr(request, "branch", None)
    if branch is None and obj is not None and hasattr(obj, "branch_id"):
        branch = getattr(obj, "branch", None)

    if obj is not None:
        object_type = object_type or obj._meta.label_lower
        object_repr = object_repr or str(obj)

    changes = dict(changes or {})
    # Link records about a patient (vitals, documents, consent...) to that patient,
    # so the patient's "Activity" tab can show them.
    if obj is not None and getattr(obj, "patient_id", None):
        changes.setdefault("patient", str(obj.patient_id))

    meta = request.META if request is not None else {}
    return AuditLog.objects.create(
        organization=organization,
        branch=branch,
        user=user,
        username=(user.username if user else username)[:150],
        action=action,
        object_type=object_type,
        object_id=str(obj.pk) if obj is not None else "",
        object_repr=object_repr[:255],
        changes=changes,
        ip_address=client_ip(request),
        user_agent=meta.get("HTTP_USER_AGENT", "")[:255],
    )
