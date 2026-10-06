from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.billing.models import Invoice
from apps.emr.models import Visit
from apps.patients.models import Patient
from conftest import client_for

TODAY = timezone.localdate()


def url(code, **params):
    query = "&".join(f"{k}={v}" for k, v in {"date_from": TODAY.replace(day=1), "date_to": TODAY, **params}.items())
    return f"/api/v1/reports/{code}/?{query}"


def patient(org, uhid, name):
    return Patient.objects.create(organization=org, uhid=uhid, first_name=name, last_name="Demo", gender="female",
                                  mobile="9812345621")


def opd_bill(client, org, branch, doctor, pat, price, payment=None):
    token = Appointment.objects.filter(branch=branch, date=TODAY).count() + 1
    appointment = Appointment.objects.create(organization=org, branch=branch, patient=pat, doctor=doctor, date=TODAY,
                                             start_time=time(9, 0 + 15 * token), status="checked_in", token_number=token)
    body = {"appointment": str(appointment.id),
            "lines": [{"kind": "consultation", "description": "OPD consultation", "unit_price": str(price)}]}
    if payment:
        body["payment"] = payment
    response = client.post("/api/v1/opd-bills/charge/", body, format="json")
    assert response.status_code in (200, 201), response.data
    return Invoice.objects.get(appointment=appointment)


@pytest.fixture
def billed_day(org, branch_a, doctor, receptionist):
    """Two OPD bills today: 300 cash (paid), 500 UPI 200 paid (300 due)."""
    client = client_for(receptionist, branch_a)
    opd_bill(client, org, branch_a, doctor, patient(org, "R-1", "Asha"), 300, {"mode": "cash", "amount": "300"})
    opd_bill(client, org, branch_a, doctor, patient(org, "R-2", "Ravi"), 500, {"mode": "upi", "amount": "200"})


@pytest.mark.django_db
def test_collection_by_payment_mode(branch_a, branch_admin, billed_day):
    data = client_for(branch_admin, branch_a).get(url("collection")).data
    total = data["totals"]
    assert Decimal(total["cash"]) == 300 and Decimal(total["upi"]) == 200 and Decimal(total["card"]) == 0
    assert Decimal(total["net"]) == 500 and total["bills"] == 2
    assert data["rows"][0]["period"] == str(TODAY)


@pytest.mark.django_db
def test_collection_by_month_and_refund(branch_a, branch_admin, billed_day):
    client = client_for(branch_admin, branch_a)
    paid = Invoice.objects.get(patient__uhid="R-1")
    client.post(f"/api/v1/invoices/{paid.id}/cancel/", {"reason": "Test", "refund_mode": "cash"}, format="json")
    data = client.get(url("collection", group="month")).data
    assert data["rows"][0]["period"] == str(TODAY.replace(day=1))
    assert Decimal(data["totals"]["refunds"]) == 300 and Decimal(data["totals"]["net"]) == 200
    assert data["totals"]["bills"] == 1  # the cancelled bill no longer counts


@pytest.mark.django_db
def test_income_by_doctor_and_branch(branch_a, branch_admin, doctor, billed_day):
    client = client_for(branch_admin, branch_a)
    row = client.get(url("by_doctor")).data["rows"][0]
    assert row["name"] == doctor.full_name
    assert Decimal(row["consultation"]) == 800 and Decimal(row["received"]) == 500 and Decimal(row["due"]) == 300
    parts = sum(Decimal(row[k]) for k in ("consultation", "services", "medicines", "round_off"))
    assert parts == Decimal(row["billed"])  # each row adds up
    branch_row = client.get(url("by_branch")).data["rows"][0]
    assert branch_row["name"] == "Branch A" and Decimal(branch_row["billed"]) == 800


@pytest.mark.django_db
def test_new_vs_repeat_patients(org, branch_a, branch_admin, doctor):
    old, new = patient(org, "P-1", "Old"), patient(org, "P-2", "New")
    Visit.objects.create(organization=org, branch=branch_a, patient=old, doctor=doctor, visit_date=TODAY - timedelta(days=60))
    Visit.objects.create(organization=org, branch=branch_a, patient=old, doctor=doctor, visit_date=TODAY)
    Visit.objects.create(organization=org, branch=branch_a, patient=new, doctor=doctor, visit_date=TODAY)
    totals = client_for(branch_admin, branch_a).get(url("patients")).data["totals"]
    assert (totals["visits"], totals["patients"], totals["new"], totals["repeat"]) == (2, 2, 1, 1)
    # A new patient who comes back in the same period: one new case and one follow-up, still one patient
    Visit.objects.create(organization=org, branch=branch_a, patient=new, doctor=doctor, visit_date=TODAY + timedelta(days=1))
    data = client_for(branch_admin, branch_a).get(url("patients", date_to=TODAY + timedelta(days=1))).data
    assert (data["totals"]["patients"], data["totals"]["new"], data["totals"]["repeat"]) == (2, 1, 2)
    assert sum(r["repeat"] for r in data["rows"]) == data["totals"]["repeat"]


@pytest.mark.django_db
def test_missed_follow_ups_masks_phone_and_is_audited(org, branch_a, branch_b, receptionist, doctor):
    late, came = patient(org, "F-1", "Late"), patient(org, "F-2", "Came")
    due = TODAY - timedelta(days=3)
    for p in (late, came):
        Visit.objects.create(organization=org, branch=branch_a, patient=p, doctor=doctor,
                             visit_date=due - timedelta(days=10), follow_up_date=due)
    # "Came" came back - in the other branch - so is not missed
    Visit.objects.create(organization=org, branch=branch_b, patient=came, doctor=doctor, visit_date=due)
    client = client_for(receptionist, branch_a)
    # Receptionists don't have "reports.view" at the start: an admin can add it on the Roles screen
    assert client.get(url("follow_ups", date_from=due - timedelta(days=30))).status_code == 403
    role = receptionist.branch_roles.first().role
    role.permissions.append("reports.view")
    role.save()
    rows = client.get(url("follow_ups", date_from=due - timedelta(days=30))).data["rows"]
    assert [r["uhid"] for r in rows] == ["F-1"]
    assert rows[0]["phone"] == "98XXXXXX21" and rows[0]["days_late"] == 3
    assert AuditLog.objects.filter(action="view", object_type="report").exists()


@pytest.mark.django_db
def test_gst_summary(branch_a, branch_admin, billed_day):
    rows = client_for(branch_admin, branch_a).get(url("gst")).data["rows"]
    assert rows[0]["code"] == "999312" and rows[0]["rate"] == "0%" and Decimal(rows[0]["taxable"]) == 800


@pytest.mark.django_db
def test_export_excel_and_pdf_are_audited(branch_a, branch_admin, billed_day):
    client = client_for(branch_admin, branch_a)
    xlsx = client.get(url("collection", export="xlsx"))
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"  # Excel files are zip files
    pdf = client.get(url("by_doctor", export="pdf"))
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert AuditLog.objects.filter(action="export", object_type="report").count() == 2


@pytest.mark.django_db
def test_branch_choice_respects_access(org, branch_a, branch_b, roles, doctor, billed_day):
    from conftest import make_user

    manager_a = make_user(org, "onlya", {branch_a: roles["admin"]})
    client = client_for(manager_a, branch_a)
    assert client.get(url("collection", branch=branch_b.id)).status_code == 403
    data = client.get(url("collection", branch="all")).data
    assert [b["name"] for b in data["branches"]] == ["Branch A"]


@pytest.mark.django_db
def test_therapist_cannot_see_money_reports(branch_a, therapist):
    assert client_for(therapist, branch_a).get(url("collection")).status_code == 403


@pytest.mark.django_db
def test_bad_dates_are_refused(branch_a, branch_admin):
    client = client_for(branch_admin, branch_a)
    assert client.get(url("collection", date_from=TODAY, date_to=TODAY - timedelta(days=1))).status_code == 400
    assert client.get(url("collection", date_from=TODAY - timedelta(days=2000))).status_code == 400
    assert client.get("/api/v1/reports/nothing/").status_code == 400
