import pytest

from apps.audit.models import AuditLog
from apps.audit.services import log_action
from conftest import client_for


@pytest.mark.django_db
def test_audit_log_is_append_only(org_admin):
    entry = log_action(None, "view", org_admin, user=org_admin)
    entry.action = "delete"
    with pytest.raises(PermissionError):
        entry.save()
    with pytest.raises(PermissionError):
        entry.delete()
    with pytest.raises(PermissionError):
        AuditLog.objects.all().delete()
    with pytest.raises(PermissionError):
        AuditLog.objects.update(action="x")


@pytest.mark.django_db
def test_only_allowed_users_see_audit_log(org_admin, receptionist, branch_admin, branch_a):
    log_action(None, "view", org_admin, user=org_admin, branch=branch_a)
    assert client_for(receptionist, branch_a).get("/api/v1/audit-logs/").status_code == 403
    assert client_for(branch_admin, branch_a).get("/api/v1/audit-logs/").status_code == 200
    assert client_for(org_admin, branch_a).get("/api/v1/audit-logs/").data["count"] >= 1


@pytest.mark.django_db
def test_update_records_what_changed(org_admin, org, branch_a):
    from apps.organizations.models import Room

    room = Room.objects.create(organization=org, branch=branch_a, name="Old name")
    client_for(org_admin, branch_a).patch(f"/api/v1/rooms/{room.id}/", {"name": "New name"}, format="json")
    log = AuditLog.objects.get(action="update", object_id=str(room.id))
    assert log.changes["name"] == {"from": "Old name", "to": "New name"}
