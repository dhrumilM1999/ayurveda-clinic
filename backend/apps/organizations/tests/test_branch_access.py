import uuid

import pytest

from apps.audit.models import AuditLog
from apps.organizations.models import Branch, Organization, Room
from conftest import client_for, make_user


@pytest.mark.django_db
def test_rooms_need_a_branch_header(org_admin):
    response = client_for(org_admin).get("/api/v1/rooms/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_user_cannot_use_a_branch_they_are_not_in(receptionist, branch_b):
    response = client_for(receptionist, branch_b).get("/api/v1/rooms/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_bad_branch_header_is_rejected(receptionist):
    client = client_for(receptionist)
    client.credentials(HTTP_X_BRANCH_ID="not-a-uuid")
    assert client.get("/api/v1/rooms/").status_code == 400
    client.credentials(HTTP_X_BRANCH_ID=str(uuid.uuid4()))
    assert client.get("/api/v1/rooms/").status_code == 403


@pytest.mark.django_db
def test_rooms_are_filtered_by_branch(org_admin, org, branch_a, branch_b):
    Room.objects.create(organization=org, branch=branch_a, name="Room in A")
    Room.objects.create(organization=org, branch=branch_b, name="Room in B")
    names_a = [r["name"] for r in client_for(org_admin, branch_a).get("/api/v1/rooms/").data["results"]]
    names_b = [r["name"] for r in client_for(org_admin, branch_b).get("/api/v1/rooms/").data["results"]]
    assert names_a == ["Room in A"]
    assert names_b == ["Room in B"]


@pytest.mark.django_db
def test_branch_admin_adds_room_and_it_is_audited(branch_admin, branch_a):
    client = client_for(branch_admin, branch_a)
    response = client.post("/api/v1/rooms/", {"name": "Therapy 2", "capacity": 2}, format="json")
    assert response.status_code == 201
    room = Room.objects.get(pk=response.data["id"])
    assert room.branch == branch_a and room.created_by == branch_admin
    log = AuditLog.objects.get(action="create", object_id=str(room.id))
    assert log.user == branch_admin and log.branch == branch_a


@pytest.mark.django_db
def test_receptionist_can_see_but_not_add_rooms(receptionist, branch_a):
    client = client_for(receptionist, branch_a)
    assert client.get("/api/v1/rooms/").status_code == 200
    assert client.post("/api/v1/rooms/", {"name": "X"}, format="json").status_code == 403


@pytest.mark.django_db
def test_room_delete_is_soft(org_admin, org, branch_a):
    room = Room.objects.create(organization=org, branch=branch_a, name="Old room")
    assert client_for(org_admin, branch_a).delete(f"/api/v1/rooms/{room.id}/").status_code == 204
    assert not Room.objects.filter(pk=room.pk).exists()
    assert Room.all_objects.get(pk=room.pk).is_deleted


@pytest.mark.django_db
def test_org_admin_sees_all_branches_but_others_only_theirs(org_admin, branch_admin, receptionist, branch_a, branch_b):
    assert len(client_for(org_admin, branch_a).get("/api/v1/branches/").data["results"]) == 2
    codes = [b["code"] for b in client_for(branch_admin, branch_a).get("/api/v1/branches/").data["results"]]
    assert codes == ["A"]
    # Receptionists don't have branches.view at all.
    assert client_for(receptionist, branch_a).get("/api/v1/branches/").status_code == 403


@pytest.mark.django_db
def test_only_org_admin_can_add_branches(org_admin, branch_admin, branch_a):
    payload = {"name": "Surat", "code": "srt"}
    assert client_for(branch_admin, branch_a).post("/api/v1/branches/", payload, format="json").status_code == 403
    response = client_for(org_admin, branch_a).post("/api/v1/branches/", payload, format="json")
    assert response.status_code == 201
    assert response.data["code"] == "SRT"


@pytest.mark.django_db
def test_other_organization_data_is_invisible(org_admin, branch_a, roles):
    other_org = Organization.objects.create(name="Other Clinic")
    other_branch = Branch.objects.create(organization=other_org, name="Elsewhere", code="X")
    Room.objects.create(organization=other_org, branch=other_branch, name="Secret room")
    client = client_for(org_admin)
    client.credentials(HTTP_X_BRANCH_ID=str(other_branch.id))
    assert client.get("/api/v1/rooms/").status_code == 403
    names = [b["name"] for b in client_for(org_admin, branch_a).get("/api/v1/branches/").data["results"]]
    assert "Elsewhere" not in names


@pytest.mark.django_db
def test_feature_flags_toggle(org_admin, receptionist, branch_a, branch_b):
    admin = client_for(org_admin, branch_a)
    flags = {f["code"]: f["enabled"] for f in admin.get("/api/v1/feature-flags/").data}
    assert flags["panchakarma"] is False
    assert admin.patch("/api/v1/feature-flags/panchakarma/", {"enabled": True}, format="json").status_code == 200
    flags_a = {f["code"]: f["enabled"] for f in admin.get("/api/v1/feature-flags/").data}
    flags_b = {f["code"]: f["enabled"] for f in client_for(org_admin, branch_b).get("/api/v1/feature-flags/").data}
    assert flags_a["panchakarma"] is True and flags_b["panchakarma"] is False
    # Receptionist can read flags but not change them.
    reception = client_for(receptionist, branch_a)
    assert reception.get("/api/v1/feature-flags/").status_code == 200
    assert reception.patch("/api/v1/feature-flags/panchakarma/", {"enabled": False}, format="json").status_code == 403
