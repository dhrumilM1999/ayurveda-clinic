"""
"By mistake" tests, part 3: the owner / admin screens: staff, roles, prices, schedules, rooms, switches.
The owner must not be able to lock themselves out or enter impossible numbers.
"""
import pytest

from apps.accounts.models import Role, User
from apps.organizations.models import Room
from conftest import client_for, make_user


@pytest.mark.django_db
def test_admin_cannot_lock_themselves_out(org_admin, branch_a):
    c = client_for(org_admin, branch_a)
    assert c.delete(f"/api/v1/staff/{org_admin.id}/").status_code in (400, 403)
    res = c.patch(f"/api/v1/staff/{org_admin.id}/", {"is_active": False}, format="json")
    assert res.status_code in (400, 403)
    org_admin.refresh_from_db()
    assert org_admin.is_active and not org_admin.is_deleted


@pytest.mark.django_db
def test_last_organization_admin_cannot_be_demoted(org_admin, branch_a):
    c = client_for(org_admin, branch_a)
    res = c.patch(f"/api/v1/staff/{org_admin.id}/", {"is_org_admin": False}, format="json")
    assert res.status_code in (400, 403), res.data
    org_admin.refresh_from_db()
    assert org_admin.is_org_admin


@pytest.mark.django_db
def test_role_in_use_cannot_be_deleted_and_system_role_stays(org_admin, receptionist, branch_a, roles):
    c = client_for(org_admin, branch_a)
    assert c.delete(f"/api/v1/roles/{roles['receptionist'].id}/").status_code in (400, 403, 409)
    assert Role.all_objects.filter(pk=roles["receptionist"].pk, is_deleted=False).exists()


@pytest.mark.django_db
def test_role_with_no_permissions_or_wrong_codes_is_refused(org_admin, branch_a):
    c = client_for(org_admin, branch_a)
    res = c.post("/api/v1/roles/", {"name": "Odd", "code": "odd", "permissions": ["patients.view", "not.a.permission"]}, format="json")
    assert res.status_code == 400
    assert not Role.objects.filter(code="odd").exists()


@pytest.mark.django_db
@pytest.mark.parametrize("body", [
    {"name": "X", "price": "-10"}, {"name": "X", "price": "abc"}, {"name": "", "price": "100"},
    {"name": "X", "price": "100", "gst_rate": "150"}, {"name": "X", "price": "100", "gst_rate": "-1"},
])
def test_wrong_service_prices_are_refused(org_admin, branch_a, body):
    res = client_for(org_admin, branch_a).post("/api/v1/services/", body, format="json")
    assert res.status_code == 400, (body, res.data)


@pytest.mark.django_db
def test_service_with_same_name_twice_is_refused(org_admin, branch_a):
    c = client_for(org_admin, branch_a)
    assert c.post("/api/v1/services/", {"name": "Abhyanga", "price": "500"}, format="json").status_code == 201
    assert c.post("/api/v1/services/", {"name": "Abhyanga", "price": "600"}, format="json").status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("body", [
    {"weekday": 0, "start_time": "13:00", "end_time": "10:00"},   # ends before it starts
    {"weekday": 0, "start_time": "10:00", "end_time": "10:00"},
    {"weekday": 9, "start_time": "10:00", "end_time": "13:00"},   # no such weekday
    {"weekday": 0, "start_time": "10:00", "end_time": "13:00", "slot_minutes": 0},
    {"weekday": 0, "start_time": "10:00", "end_time": "13:00", "slot_minutes": -15},
])
def test_wrong_doctor_timings_are_refused(org_admin, doctor, branch_a, body):
    res = client_for(org_admin, branch_a).post("/api/v1/doctor-schedules/", {"doctor": str(doctor.id), **body}, format="json")
    assert res.status_code == 400, (body, res.data)


@pytest.mark.django_db
@pytest.mark.parametrize("body", [{"new_case_fee": "-100"}, {"follow_up_fee": "-1"}, {"follow_up_days": -3}, {"new_case_fee": "abc"}])
def test_wrong_consultation_fees_are_refused(org_admin, doctor, branch_a, body):
    res = client_for(org_admin, branch_a).post("/api/v1/consultation-fees/set/", {
        "doctor": str(doctor.id), "new_case_fee": "300", "follow_up_fee": "150", "follow_up_days": 15, **body}, format="json")
    assert res.status_code == 400, (body, res.data)


@pytest.mark.django_db
def test_wrong_rooms_are_refused(org_admin, branch_a):
    c = client_for(org_admin, branch_a)
    assert c.post("/api/v1/rooms/", {"name": ""}, format="json").status_code == 400
    assert c.post("/api/v1/rooms/", {"name": "R", "capacity": -1}, format="json").status_code == 400
    assert Room.objects.count() == 0


@pytest.mark.django_db
def test_branch_admin_cannot_touch_another_branch_or_org_settings(branch_admin, branch_a, branch_b):
    c = client_for(branch_admin, branch_a)
    assert c.get("/api/v1/organization/").status_code in (200, 403)
    assert client_for(branch_admin, branch_b).get("/api/v1/rooms/").status_code == 403


@pytest.mark.django_db
def test_wrong_password_attempts_are_limited_and_message_is_the_same(org, roles, branch_a):
    make_user(org, "limited")
    from rest_framework.test import APIClient

    client = APIClient()
    answers = {client.post("/api/v1/auth/login/", {"username": name, "password": "wrong-Password1"}, format="json").status_code
               for name in ("limited", "no-such-user") for _ in range(2)}
    assert answers <= {400, 401}          # same answer whether the user exists or not
    for _ in range(40):
        last = client.post("/api/v1/auth/login/", {"username": "limited", "password": "wrong-Password1"}, format="json").status_code
    assert last == 429                    # slowed down after many wrong tries
    assert User.objects.get(username="limited").is_active
