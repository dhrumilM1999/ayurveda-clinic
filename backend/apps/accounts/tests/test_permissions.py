import pytest

from apps.accounts.models import Role
from conftest import client_for, make_user


@pytest.mark.django_db
def test_receptionist_cannot_manage_roles_or_staff(receptionist, branch_a, roles):
    client = client_for(receptionist, branch_a)
    assert client.get("/api/v1/roles/").status_code == 403
    assert client.post("/api/v1/roles/", {"name": "X", "permissions": []}, format="json").status_code == 403
    assert client.post("/api/v1/staff/", {"username": "x"}, format="json").status_code == 403


@pytest.mark.django_db
def test_therapist_has_no_billing_permission(therapist, branch_a):
    from apps.accounts.services import user_has_perm

    assert not user_has_perm(therapist, "billing.view", branch_a)
    assert user_has_perm(therapist, "therapy.manage", branch_a)


@pytest.mark.django_db
def test_org_admin_can_create_role_with_valid_permissions_only(org_admin, branch_a):
    client = client_for(org_admin, branch_a)
    bad = client.post("/api/v1/roles/", {"name": "Bad", "permissions": ["nope.nothing"]}, format="json")
    assert bad.status_code == 400
    ok = client.post("/api/v1/roles/", {"name": "Accountant", "permissions": ["billing.view"]}, format="json")
    assert ok.status_code == 201
    assert ok.data["code"] == "accountant"


@pytest.mark.django_db
def test_system_role_cannot_be_deleted(org_admin, branch_a, roles):
    client = client_for(org_admin, branch_a)
    response = client.delete(f"/api/v1/roles/{roles['doctor'].id}/")
    assert response.status_code == 400
    assert Role.objects.filter(pk=roles["doctor"].pk).exists()


@pytest.mark.django_db
def test_changing_a_role_changes_what_users_can_do(org_admin, receptionist, branch_a, roles):
    reception_client = client_for(receptionist, branch_a)
    assert reception_client.get("/api/v1/roles/").status_code == 403
    admin_client = client_for(org_admin, branch_a)
    perms = roles["receptionist"].permissions + ["roles.view"]
    admin_client.patch(f"/api/v1/roles/{roles['receptionist'].id}/", {"permissions": perms}, format="json")
    assert reception_client.get("/api/v1/roles/").status_code == 200


@pytest.mark.django_db
def test_branch_admin_creates_staff_only_in_own_branch(branch_admin, branch_a, branch_b, roles):
    client = client_for(branch_admin, branch_a)
    payload = {
        "username": "newreception", "full_name": "New Reception", "password": "Strong@Pass2026",
        "branch_roles": [{"branch": str(branch_a.id), "role": str(roles["receptionist"].id)}],
    }
    assert client.post("/api/v1/staff/", payload, format="json").status_code == 201

    payload["username"] = "otherbranch"
    payload["branch_roles"] = [{"branch": str(branch_b.id), "role": str(roles["receptionist"].id)}]
    assert client.post("/api/v1/staff/", payload, format="json").status_code == 400


@pytest.mark.django_db
def test_branch_admin_cannot_make_org_admin(branch_admin, branch_a):
    client = client_for(branch_admin, branch_a)
    payload = {"username": "sneaky", "full_name": "S", "password": "Strong@Pass2026", "is_org_admin": True}
    assert client.post("/api/v1/staff/", payload, format="json").status_code == 400


@pytest.mark.django_db
def test_weak_password_is_refused(org_admin, branch_a):
    client = client_for(org_admin, branch_a)
    payload = {"username": "weak", "full_name": "Weak", "password": "12345678"}
    response = client.post("/api/v1/staff/", payload, format="json")
    assert response.status_code == 400
    assert "password" in response.data


@pytest.mark.django_db
def test_staff_delete_is_soft(org_admin, branch_a, org):
    from apps.accounts.models import User

    target = make_user(org, "leaving")
    client = client_for(org_admin, branch_a)
    assert client.delete(f"/api/v1/staff/{target.id}/").status_code == 204
    assert not User.objects.filter(pk=target.pk).exists()
    kept = User.all_objects.get(pk=target.pk)
    assert kept.is_deleted and not kept.is_active


@pytest.mark.django_db
def test_doctor_schedule_overlap_is_refused(org_admin, doctor, branch_a, branch_b):
    payload = {"doctor": str(doctor.id), "weekday": 0, "start_time": "10:00", "end_time": "13:00"}
    assert client_for(org_admin, branch_a).post("/api/v1/doctor-schedules/", payload, format="json").status_code == 201
    # Same doctor, same day, overlapping time in another branch.
    payload.update(start_time="12:00", end_time="14:00")
    assert client_for(org_admin, branch_b).post("/api/v1/doctor-schedules/", payload, format="json").status_code == 400
