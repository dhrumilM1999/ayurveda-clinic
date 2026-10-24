import pytest
from rest_framework.test import APIClient

from apps.audit.error_log import normalize_path
from apps.audit.models import ErrorLog
from conftest import client_for



def client_with_session(user, branch, session):
    c = client_for(user, branch)
    c.credentials(HTTP_X_BRANCH_ID=str(branch.id), HTTP_X_SESSION_ID=session)
    return c


LIST = "/api/v1/error-logs/"
REPORT = "/api/v1/error-logs/report/"


def test_the_same_problem_on_different_records_is_one_problem():
    a = normalize_path("/api/v1/patients/3f2a1c9e-1111-4222-8333-444455556666/?search=Kamla")
    b = normalize_path("/api/v1/patients/aaaaaaaa-1111-4222-8333-444455556666/")
    assert a == b == "/api/v1/patients/:id/"
    assert normalize_path("/api/v1/appointments/45/") == "/api/v1/appointments/:n/"


@pytest.mark.django_db
def test_a_refused_action_is_written_with_who_and_where(receptionist, branch_a):
    c = client_for(receptionist, branch_a)
    assert c.get("/api/v1/audit-logs/").status_code == 403
    row = ErrorLog.objects.get()
    assert (row.level, row.status_code, row.username, row.source) == ("warning", 403, receptionist.username, "backend")
    assert row.path == "/api/v1/audit-logs/" and row.branch_id == branch_a.id and row.request_code
    c.get("/api/v1/audit-logs/")
    row.refresh_from_db()
    assert ErrorLog.objects.count() == 1 and row.count == 2          # counted, not repeated


@pytest.mark.django_db
def test_nothing_is_written_for_a_logged_out_user_or_an_expired_login(branch_a):
    assert APIClient().get("/api/v1/audit-logs/").status_code == 401
    assert ErrorLog.objects.count() == 0


@pytest.mark.django_db
def test_a_crash_is_logged_with_a_code_the_user_can_read_out(org_admin, branch_a, monkeypatch):
    from apps.audit import views

    def boom(self):
        raise RuntimeError("something odd inside")
    monkeypatch.setattr(views.AuditLogViewSet, "get_queryset", boom)
    c = client_with_session(org_admin, branch_a, "sess-123")
    res = c.get("/api/v1/audit-logs/")
    assert res.status_code == 500 and res.data["code"] and res.data["code"] in res.data["detail"]
    row = ErrorLog.objects.get(request_code=res.data["code"])
    assert row.level == "error" and row.status_code == 500 and "RuntimeError: something odd inside" in row.message
    assert "Traceback" in row.details and row.session_id == "sess-123" and row.username == org_admin.username


@pytest.mark.django_db
def test_the_screen_reports_its_own_crash_and_the_owner_reads_and_resolves_it(org_admin, receptionist, branch_a):
    staff = client_with_session(receptionist, branch_a, "abc_1")
    trail = [{"t": "10:01:02", "type": "page", "text": "/patients"}, {"t": "10:01:09", "type": "api", "text": "GET /patients/ 200"}]
    res = staff.post(REPORT, {"kind": "react", "message": "Cannot read properties of undefined", "details": "at X (a.js:1)",
                              "screen": "/patients", "trail": trail}, format="json")
    assert res.status_code == 201 and res.data["code"]
    # a reception user cannot read the log, the owner can
    assert staff.get(LIST).status_code == 403
    owner = client_for(org_admin, branch_a)
    page = owner.get(LIST, {"source": "frontend"}).data
    assert page["count"] == 1 and page["results"][0]["username"] == receptionist.username and page["results"][0]["session_id"] == "abc_1"
    one = owner.get(f"{LIST}{page['results'][0]['id']}/").data
    assert one["trail"][1]["text"] == "GET /patients/ 200" and one["details"].startswith("at X")
    # the screen crash and the refused page of the same login are both found by the session id
    assert owner.get(LIST, {"session_id": "abc_1"}).data["count"] == 2 and owner.get(LIST, {"session_id": "zzz"}).data["count"] == 0
    assert owner.get(f"{LIST}summary/").data["open_errors"] == 1
    done = owner.patch(f"{LIST}{one['id']}/", {"is_resolved": True, "note": "fixed in the update"}, format="json")
    assert done.status_code == 200 and done.data["is_resolved"] and done.data["resolved_by_name"] == org_admin.username
    assert owner.get(f"{LIST}summary/").data["open_errors"] == 0
    # the text of the problem cannot be rewritten, and nothing can be deleted
    owner.patch(f"{LIST}{one['id']}/", {"message": "all fine"}, format="json")
    assert ErrorLog.objects.get(source="frontend").message == "Cannot read properties of undefined"
    assert owner.delete(f"{LIST}{one['id']}/").status_code == 405


@pytest.mark.django_db
def test_a_server_error_gets_the_users_last_steps_added_later(org_admin, branch_a, monkeypatch):
    from apps.audit import views

    monkeypatch.setattr(views.AuditLogViewSet, "get_queryset", lambda self: (_ for _ in ()).throw(ValueError("bad")))
    c = client_for(org_admin, branch_a)
    code = c.get("/api/v1/audit-logs/").data["code"]
    c.post(REPORT, {"kind": "trail", "code": code, "screen": "/audit-log", "trail": [{"t": "1", "type": "page", "text": "/audit-log"}]}, format="json")
    row = ErrorLog.objects.get(request_code=code)
    assert row.trail[0]["text"] == "/audit-log" and row.screen == "/audit-log"
    assert ErrorLog.objects.count() == 1


@pytest.mark.django_db
def test_other_clinics_and_bad_reports_are_kept_out(org_admin, receptionist, branch_a):
    c = client_for(org_admin, branch_a)
    assert c.post(REPORT, {"kind": "nonsense"}, format="json").status_code == 400
    assert c.post(REPORT, {"kind": "js", "message": "x" * 5000}, format="json").status_code == 400
    assert APIClient().post(REPORT, {"kind": "js", "message": "x"}, format="json").status_code == 401
    assert ErrorLog.objects.count() == 0
