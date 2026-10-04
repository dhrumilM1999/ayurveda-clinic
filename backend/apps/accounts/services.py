"""
Functions other modules use to ask "can this user do X in this branch?".
ASK FIRST before editing.
"""
from apps.organizations.models import Branch

from .models import Role, UserBranchRole
from .permissions_catalog import ALL_PERMISSION_CODES, DEFAULT_ROLES


def accessible_branches(user):
    """Active branches the user may work in. Organization admins get all of them."""
    if not user or not user.is_authenticated or not user.organization_id:
        return Branch.objects.none()
    qs = Branch.objects.filter(organization_id=user.organization_id, is_active=True)
    if user.is_org_admin:
        return qs
    return qs.filter(
        user_roles__user=user, user_roles__is_deleted=False, user_roles__role__is_deleted=False,
    ).distinct()


def branch_permissions(user, branch) -> set[str]:
    """All permission codes the user has in one branch."""
    if user.is_org_admin:
        return set(ALL_PERMISSION_CODES)
    assignment = (
        UserBranchRole.objects.filter(user=user, branch=branch, role__is_deleted=False)
        .select_related("role")
        .first()
    )
    if assignment is None:
        return set()
    return set(assignment.role.permissions) & ALL_PERMISSION_CODES


def user_has_perm(user, code: str, branch=None) -> bool:
    """
    With a branch: does the user have `code` in that branch?
    Without a branch (organization-wide screens): in at least one active branch?
    """
    if user.is_org_admin:
        return True
    if branch is not None:
        return code in branch_permissions(user, branch)
    roles = Role.objects.filter(
        assignments__user=user, assignments__is_deleted=False, assignments__branch__is_active=True,
    )
    return any(code in role.permissions for role in roles)


def user_requires_2fa(user) -> bool:
    """Doctors and admins must enter an OTP at login."""
    if user.is_org_admin:
        return True
    return Role.objects.filter(
        assignments__user=user, assignments__is_deleted=False, requires_2fa=True,
    ).exists()


def create_default_roles(organization) -> dict[str, Role]:
    """Create the standard roles for a new organization (skips ones that exist)."""
    roles = {}
    for code, info in DEFAULT_ROLES.items():
        role, _ = Role.objects.get_or_create(
            organization=organization,
            code=code,
            defaults={
                "name": info["name"],
                "description": info["description"],
                "permissions": list(info["permissions"]),
                "requires_2fa": info["requires_2fa"],
                "is_system": True,
            },
        )
        roles[code] = role
    return roles
