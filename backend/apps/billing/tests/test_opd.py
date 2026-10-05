from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.billing.models import ConsultationFee, Invoice, ServiceCharge
from apps.emr.models import Visit
from apps.patients.models import Patient
from conftest import client_for, make_user, set_additional_features

TODAY = timezone.localdate()


@pytest.fixture
def patient(org):
    return Patient.objects.create(organization=org, uhid="T-9", first_name="Kiran", last_name="Shah", gender="female",
                                  mobile="9876500000")


@pytest.fixture
def fee(org, branch_a, doctor):
    return ConsultationFee.objects.create(organization=org, branch=branch_a, doctor=doctor, new_case_fee=Decimal("300"),
                                          follow_up_fee=Decimal("150"), follow_up_days=15)


@pytest.fixture
def appointment(org, branch_a, patient, doctor):
    return Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, date=TODAY,
                                      start_time=time(10, 0), end_time=time(10, 15), status="checked_in", token_number=1)


@pytest.fixture
def service(org):
    return ServiceCharge.objects.create(organization=org, name="Agnikarma", price=Decimal("500"))


def consultation_line(amount):
    return {"kind": "consultation", "description": "OPD consultation", "unit_price": str(amount)}


@pytest.mark.django_db
def test_new_case_then_follow_up_fee(org, branch_a, receptionist, doctor, patient, appointment, fee):
    client = client_for(receptionist, branch_a)
    data = client.get("/api/v1/opd-bills/suggest/", {"appointment": str(appointment.id)}).data
    assert data["consultation"]["visit_kind"] == "new" and data["consultation"]["fee"] == "300.00"
    assert data["bill"] is None
    Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                         visit_date=TODAY - timedelta(days=10))
    data = client.get("/api/v1/opd-bills/suggest/", {"appointment": str(appointment.id)}).data
    assert data["consultation"]["visit_kind"] == "follow_up" and data["consultation"]["fee"] == "150.00"


@pytest.mark.django_db
def test_fee_at_check_in_then_services_after_check_up(org, branch_a, receptionist, doctor, patient, appointment, fee, service):
    desk = client_for(receptionist, branch_a)
    res = desk.post("/api/v1/opd-bills/charge/", {
        "appointment": str(appointment.id), "lines": [consultation_line(300)],
        "payment": {"mode": "cash", "amount": "300"}}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["number"].startswith("A/OP/") and res.data["status"] == "paid" and res.data["care_type"] == "OPD"
    # The doctor starts the check-up and adds a procedure: same OPD bill, now partly paid
    visit = Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, visit_date=TODAY,
                                 appointment=appointment)
    res = client_for(doctor, branch_a).post("/api/v1/opd-bills/charge/", {
        "visit": str(visit.id), "lines": [{"kind": "service", "service": str(service.id), "unit_price": "500"}]},
        format="json")
    assert res.status_code == 201, res.data
    invoice = Invoice.objects.get(series="OP")
    assert invoice.total_amount == Decimal("800.00") and invoice.status == "partly_paid" and invoice.balance == 500
    assert invoice.visit_id == visit.id and invoice.lines.count() == 2
    assert Invoice.objects.filter(series="OP").count() == 1


@pytest.mark.django_db
def test_doctor_cannot_take_payment(branch_a, doctor, appointment):
    res = client_for(doctor, branch_a).post("/api/v1/opd-bills/charge/", {
        "appointment": str(appointment.id), "lines": [consultation_line(300)],
        "payment": {"mode": "cash", "amount": "300"}}, format="json")
    assert res.status_code == 403


@pytest.mark.django_db
def test_therapist_cannot_bill(org, roles, branch_a, appointment):
    therapist = make_user(org, "ther", {branch_a: roles["therapist"]})
    res = client_for(therapist, branch_a).post("/api/v1/opd-bills/charge/", {
        "appointment": str(appointment.id), "lines": [consultation_line(300)]}, format="json")
    assert res.status_code == 403


@pytest.mark.django_db
def test_fees_and_services_setup(org_admin, branch_a, doctor, service):
    client = client_for(org_admin, branch_a)
    res = client.post("/api/v1/consultation-fees/set/", {"doctor": str(doctor.id), "new_case_fee": "400",
                                                         "follow_up_fee": "0", "follow_up_days": 7}, format="json")
    assert res.status_code == 200, res.data
    row = next(r for r in client.get("/api/v1/consultation-fees/").data if r["doctor"] == str(doctor.id))
    assert row["new_case_fee"] == "400.00" and row["follow_up_days"] == 7
    client.post(f"/api/v1/services/{service.id}/branch-price/", {"price": "450", "is_active": True}, format="json")
    listed = next(s for s in client.get("/api/v1/services/").data if s["id"] == str(service.id))
    assert listed["effective_price"] == "450.00" and listed["price"] == "500.00"


@pytest.mark.django_db
def test_preview_is_not_counted_as_print(branch_a, receptionist, appointment):
    client = client_for(receptionist, branch_a)
    bill = client.post("/api/v1/opd-bills/charge/", {"appointment": str(appointment.id),
                                                     "lines": [consultation_line(300)]}, format="json").data
    assert client.get(f"/api/v1/invoices/{bill['id']}/pdf/", {"preview": "1"}).status_code == 200
    assert Invoice.objects.get(pk=bill["id"]).print_count == 0
    client.get(f"/api/v1/invoices/{bill['id']}/pdf/")
    assert Invoice.objects.get(pk=bill["id"]).print_count == 1


@pytest.mark.django_db
def test_cancel_opd_bill_makes_credit_note(branch_a, receptionist, org, roles, appointment):
    admin = make_user(org, "branchadmin2", {branch_a: roles["admin"]})
    bill = client_for(receptionist, branch_a).post("/api/v1/opd-bills/charge/", {
        "appointment": str(appointment.id), "lines": [consultation_line(300)],
        "payment": {"mode": "upi", "amount": "300"}}, format="json").data
    res = client_for(admin, branch_a).post(f"/api/v1/invoices/{bill['id']}/cancel/",
                                           {"reason": "Booked by mistake", "refund_mode": "upi"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "cancelled" and res.data["credit_notes"][0]["refund_amount"] == "300.00"


# --- One combined bill: medicines on the OPD bill -----------------------------------------------------
@pytest.mark.django_db
def test_combined_bill_puts_medicines_on_opd_bill(org, branch_a, receptionist, pharmacist, doctor, patient, appointment):
    from apps.medicines.services import add_sample_medicines
    from apps.medicines.models import Medicine
    from apps.pharmacy.models import StockBatch
    from apps.prescriptions.services import save_prescription

    set_additional_features(org, codes=["pharmacy_billing", "combined_opd_bill"])
    add_sample_medicines(org)
    medicine = Medicine.objects.get(organization=org, name="Triphala Churna")
    client_for(receptionist, branch_a).post("/api/v1/opd-bills/charge/", {
        "appointment": str(appointment.id), "lines": [consultation_line(300)],
        "payment": {"mode": "cash", "amount": "300"}}, format="json")
    visit = Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, visit_date=TODAY,
                                 appointment=appointment)
    rx = save_prescription(visit, [{"medicine": medicine, "medicine_name": medicine.name, "dose": "3"}], "", doctor)
    rx.status = "final"
    rx.save()
    pharmacy = client_for(pharmacist, branch_a)
    pharmacy.post("/api/v1/purchases/", {"invoice_no": "S1", "invoice_date": str(TODAY), "items": [
        {"medicine": str(medicine.id), "batch_no": "B1", "expiry_date": str(TODAY + timedelta(days=400)),
         "quantity": "5", "mrp": "100"}]}, format="json")
    line = pharmacy.get(f"/api/v1/dispensing/{rx.id}/").data["lines"][0]
    res = pharmacy.post(f"/api/v1/dispensing/{rx.id}/sell/", {"items": [
        {"prescription_item": line["id"], "batch": line["batches"][0]["id"], "quantity": "2"}]}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["number"].startswith("A/OP/")
    assert not Invoice.objects.filter(series="PH").exists()
    bill = Invoice.objects.get(series="OP")
    assert bill.total_amount == Decimal("500.00") and bill.balance == Decimal("200.00")
    # Cancelling the OPD bill puts the medicines back in stock
    admin = make_user(org, "branchadmin3", {branch_a: roles_admin(org)})
    res = client_for(admin, branch_a).post(f"/api/v1/invoices/{bill.id}/cancel/", {"reason": "Test"}, format="json")
    assert res.status_code == 200, res.data
    assert StockBatch.objects.get(batch_no="B1").quantity == 5


def roles_admin(org):
    from apps.accounts.models import Role

    return Role.objects.get(organization=org, code="admin")
