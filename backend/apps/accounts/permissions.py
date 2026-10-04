"""
The shared permission check used by every API screen. ASK FIRST before editing.

How it works:
1. The React app sends the chosen branch in the "X-Branch-ID" header.
2. We check the user is allowed in that branch (otherwise: 403 Forbidden).
3. We work out which permission code the action needs, e.g. "rooms.manage",
   and check the user's role in that branch has it.
"""
import uuid

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .services import accessible_branches, user_has_perm

BRANCH_HEADER = "X-Branch-ID"


def resolve_request_branch(request):
    """Return the branch named in the X-Branch-ID header (or None if not sent)."""
    raw = request.headers.get(BRANCH_HEADER)
    if not raw:
        return None
    try:
        branch_id = uuid.UUID(raw)
    except ValueError:
        raise ValidationError({"detail": "X-Branch-ID is not a valid id."})
    branch = accessible_branches(request.user).filter(id=branch_id).first()
    if branch is None:
        raise PermissionDenied("You do not have access to this branch.")
    return branch


def required_permission(view, request) -> str | tuple | None:
    """The permission code an action needs. A tuple means "any one of these codes"."""
    action = getattr(view, "action", None)
    explicit = getattr(view, "required_permissions", {}) or {}
    if action in explicit:
        return explicit[action]
    prefix = getattr(view, "permission_prefix", None)
    if not prefix:
        return None
    return f"{prefix}.view" if request.method in SAFE_METHODS else f"{prefix}.manage"


class BranchPermission(BasePermission):
    message = "You do not have permission to do this in this branch."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.organization_id:
            return False
        branch = resolve_request_branch(request)
        request.branch = branch
        # branch_scoped: rows belong to a branch (filtered by it).
        # branch_required: rows are organization-wide (e.g. patients), but the permission is
        # checked against the user's role in the current branch.
        in_branch = getattr(view, "branch_scoped", False) or getattr(view, "branch_required", False)
        if in_branch and branch is None:
            raise ValidationError({"detail": "Please choose a branch first (X-Branch-ID header missing)."})
        code = required_permission(view, request)
        if code is None:
            return True
        codes = code if isinstance(code, (tuple, list)) else (code,)
        return any(user_has_perm(request.user, c, branch if in_branch else None) for c in codes)
