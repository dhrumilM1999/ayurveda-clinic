"""
"By mistake" tests, part 2: the doctor's check-up and prescription, the pharmacy and stock, and the wrong person.
The app should refuse politely, keep the data safe and never half-save.
"""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.billing.models import Invoice
from apps.emr.models import Visit
from apps.patients.models import Patient
from apps.pharmacy.models import StockBatch, StockMovement
from apps.pharmacy.tests.test_pharmacy import LATER, TODAY, final_rx, meds, receive, sell  # noqa: F401 (fixtures)
from conftest import client_for

VISITS = "/api/v1/visits/"
pytestmark = pytest.mark.usefixtures("all_additional_features")


@pytest.fixture
def patient(org, roles):
    return Patient.objects.create(organization=org, uhid="1", first_name="Ramesh", last_name="Patel", gender="male",
                                  mobile="9876543210")


@pytest.fixture
def appointment(org, branch_a, patient, doctor):
    return Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                      date=timezone.localdate(), start_time=time(10, 0), end_time=time(10, 15))


def open_visit(client, appointment):
    return client.post(VISITS, {"appointment": str(appointment.id)}, format="json").data["id"]


# ---------------------------------------------------------------- the doctor's check-up
@pytest.mark.django_db
def test_complete_twice_is_safe(doctor, branch_a, appointment):
    c = client_for(doctor, branch_a)
    vid = open_visit(c, appointment)
    assert c.post(f"{VISITS}{vid}/complete/").status_code == 200
    again = c.post(f"{VISITS}{vid}/complete/")
    assert again.status_code in (200, 400)
    assert Visit.objects.filter(pk=vid, status="completed").count() == 1
    assert Visit.objects.count() == 1


@pytest.mark.django_db
def test_checkup_of_a_cancelled_appointment_cannot_be_opened(doctor, branch_a, appointment, receptionist):
    client_for(receptionist, branch_a).post(f"/api/v1/appointments/{appointment.id}/cancel/", {"reason": "x"}, format="json")
    res = client_for(doctor, branch_a).post(VISITS, {"appointment": str(appointment.id)}, format="json")
    assert res.status_code == 400, res.data
    assert Visit.objects.count() == 0


@pytest.mark.django_db
def test_wrong_check_up_data_is_refused_and_nothing_changes(doctor, branch_a, appointment):
    c = client_for(doctor, branch_a)
    vid = open_visit(c, appointment)
    for bad in ({"follow_up_date": "not-a-date"}, {"follow_up_date": str(date.today() - timedelta(days=30))},
                {"complaints": "not a list"}, {"advice": "should be a list"}, {"diagnoses": [{"label": "X", "kind": "maybe"}]}):
        res = c.patch(f"{VISITS}{vid}/", bad, format="json")
        assert res.status_code == 400, (bad, res.data)
    assert Visit.objects.get(pk=vid).follow_up_date is None


@pytest.mark.django_db
def test_wrong_people_and_the_checkup(receptionist, pharmacist, therapist, branch_a, appointment, doctor):
    vid = open_visit(client_for(doctor, branch_a), appointment)
    for user in (receptionist, pharmacist):
        c = client_for(user, branch_a)
        assert c.get(f"{VISITS}{vid}/").status_code == 403
        assert c.patch(f"{VISITS}{vid}/", {"history_notes": "x"}, format="json").status_code == 403
        assert c.post(f"{VISITS}{vid}/complete/").status_code == 403
    assert Visit.objects.get(pk=vid).history_notes in ("", None)


# ---------------------------------------------------------------- pharmacy: the wrong stock action
def line_of(rx):
    return rx.items.get(medicine__isnull=False)


@pytest.mark.django_db
def test_double_click_on_give_medicines_never_sells_twice(pharmacist, branch_a, meds, final_rx):
    c = client_for(pharmacist, branch_a)
    receive(c, meds, [("Triphala Churna", "B1", LATER, "10")])
    batch = StockBatch.objects.get(batch_no="B1")
    lines = [{"prescription_item": str(line_of(final_rx).id), "batch": str(batch.id), "quantity": "3"}]
    first = sell(c, final_rx, lines)
    second = sell(c, final_rx, lines)  # the same click again
    assert first.status_code == 201, first.data
    assert second.status_code == 400 and "already given" in str(second.data)
    assert StockBatch.objects.get(pk=batch.pk).quantity == 7  # given once, not twice
    assert StockMovement.objects.filter(batch=batch, kind="dispense").count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("qty", ["0", "-2", "abc", ""])
def test_wrong_quantity_in_sale_is_refused(pharmacist, branch_a, meds, final_rx, qty):
    c = client_for(pharmacist, branch_a)
    receive(c, meds, [("Triphala Churna", "B1", LATER, "10")])
    batch = StockBatch.objects.get(batch_no="B1")
    res = sell(c, final_rx, [{"prescription_item": str(line_of(final_rx).id), "batch": str(batch.id), "quantity": qty}])
    assert res.status_code == 400, (qty, res.data)
    assert StockBatch.objects.get(pk=batch.pk).quantity == 10 and not Invoice.objects.exists()


@pytest.mark.django_db
def test_selling_a_batch_of_another_medicine_is_refused(pharmacist, branch_a, meds, final_rx):
    c = client_for(pharmacist, branch_a)
    receive(c, meds, [("Ashwagandha Churna", "WRONG", LATER, "10")])
    wrong = StockBatch.objects.get(batch_no="WRONG")
    res = sell(c, final_rx, [{"prescription_item": str(line_of(final_rx).id), "batch": str(wrong.id), "quantity": "1"}])
    assert res.status_code == 400, res.data
    assert StockBatch.objects.get(pk=wrong.pk).quantity == 10


@pytest.mark.django_db
@pytest.mark.parametrize("body", [
    {"qty": "0"}, {"qty": "-5"}, {"qty": "abc"}, {"expiry": "yesterday"}, {"mrp": "-1"}, {"rate": "-1"},
])
def test_wrong_purchase_lines_are_refused(pharmacist, branch_a, meds, body):
    c = client_for(pharmacist, branch_a)
    item = {"medicine": str(meds["Triphala Churna"].id), "batch_no": "Z9", "expiry_date": LATER, "quantity": "5",
            "purchase_rate": "50", "mrp": "90", "gst_rate": "12"}
    for key, value in body.items():
        item[{"qty": "quantity", "expiry": "expiry_date", "mrp": "mrp", "rate": "purchase_rate"}[key]] = value
    res = c.post("/api/v1/purchases/", {"invoice_no": "I1", "invoice_date": str(TODAY), "items": [item]}, format="json")
    assert res.status_code == 400, (body, res.data)
    assert StockBatch.objects.count() == 0  # nothing half-saved


@pytest.mark.django_db
def test_stock_correction_cannot_make_stock_negative(pharmacist, branch_a, meds):
    c = client_for(pharmacist, branch_a)
    receive(c, meds, [("Triphala Churna", "B1", LATER, "5")])
    batch = StockBatch.objects.get(batch_no="B1")
    res = c.post("/api/v1/stock/adjust/", {"batch": str(batch.id), "kind": "damaged", "change": "50", "reason": "typo"}, format="json")
    assert res.status_code == 400, res.data
    assert StockBatch.objects.get(pk=batch.pk).quantity == 5


@pytest.mark.django_db
def test_return_twice_never_returns_more_than_sold(pharmacist, branch_a, meds, final_rx):
    c = client_for(pharmacist, branch_a)
    receive(c, meds, [("Triphala Churna", "B1", LATER, "5", 0, "50", "112")])
    batch = StockBatch.objects.get(batch_no="B1")
    sold = sell(c, final_rx, [{"prescription_item": str(line_of(final_rx).id), "batch": str(batch.id), "quantity": "2"}],
                payment={"mode": "cash", "amount": "224"}).data
    item = c.get(f"/api/v1/sales/{sold['dispense']}/").data["items"][0]["id"]
    body = {"reason": "wrong", "refund_mode": "cash", "items": [{"dispense_item": item, "quantity": "2", "back_to_stock": True}]}
    assert c.post(f"/api/v1/sales/{sold['dispense']}/return/", body, format="json").status_code == 201
    assert c.post(f"/api/v1/sales/{sold['dispense']}/return/", body, format="json").status_code == 400  # the same click again
    assert StockBatch.objects.get(pk=batch.pk).quantity == 5
    bad = {"reason": "", "items": [{"dispense_item": item, "quantity": "-1"}]}
    assert c.post(f"/api/v1/sales/{sold['dispense']}/return/", bad, format="json").status_code == 400


@pytest.mark.django_db
def test_wrong_people_and_the_pharmacy(receptionist, therapist, doctor, branch_a, meds, final_rx):
    for user in (receptionist, therapist):
        c = client_for(user, branch_a)
        assert c.get("/api/v1/stock/").status_code == 403
        assert c.post("/api/v1/stock/adjust/", {"batch": "x", "change": "1", "reason": "r"}, format="json").status_code == 403
        assert c.post("/api/v1/purchases/", {"items": []}, format="json").status_code == 403
    assert client_for(receptionist, branch_a).post(f"/api/v1/dispensing/{final_rx.id}/sell/", {"items": []}, format="json").status_code == 403


@pytest.mark.django_db
def test_selling_from_a_draft_prescription_is_refused(pharmacist, branch_a, meds, final_rx):
    c = client_for(pharmacist, branch_a)
    receive(c, meds, [("Triphala Churna", "B1", LATER, "10")])
    batch = StockBatch.objects.get(batch_no="B1")
    final_rx.status = "draft"
    final_rx.save()
    res = sell(c, final_rx, [{"prescription_item": str(line_of(final_rx).id), "batch": str(batch.id), "quantity": "1"}])
    assert res.status_code in (400, 404), res.data
    assert StockBatch.objects.get(pk=batch.pk).quantity == 10


@pytest.mark.django_db
def test_stock_of_another_branch_is_not_sold_or_seen(pharmacist, org, roles, branch_a, branch_b, meds, final_rx):
    from conftest import make_user

    c_b_user = make_user(org, "pharm_b", {branch_b: roles["pharmacist"]})
    cb = client_for(c_b_user, branch_b)
    receive(cb, meds, [("Triphala Churna", "BB1", LATER, "10")])
    other = StockBatch.objects.get(batch_no="BB1")
    ca = client_for(pharmacist, branch_a)
    res = sell(ca, final_rx, [{"prescription_item": str(line_of(final_rx).id), "batch": str(other.id), "quantity": "1"}])
    assert res.status_code == 400, res.data
    assert StockBatch.objects.get(pk=other.pk).quantity == 10


# ---------------------------------------------------------------- "Complete visit" pressed by mistake
@pytest.mark.django_db
def test_complete_visit_can_be_reopened_until_medicines_are_given(org, doctor, pharmacist, branch_a, meds, final_rx):
    from apps.pharmacy.models import StockBatch

    visit = final_rx.visit
    visit.status = "completed"
    visit.save()
    d = client_for(doctor, branch_a)
    res = d.post(f"{VISITS}{visit.id}/reopen/")
    assert res.status_code == 200 and res.data["status"] == "draft"
    final_rx.refresh_from_db()
    assert final_rx.status == "draft"                      # the pharmacy cannot give from a prescription being changed
    # the doctor finishes again
    assert d.post(f"{VISITS}{visit.id}/complete/").status_code == 200
    final_rx.refresh_from_db()
    assert final_rx.status == "final"
    # the pharmacy gives a medicine: now it cannot be re-opened and the given line cannot be changed or removed
    p = client_for(pharmacist, branch_a)
    receive(p, meds, [("Triphala Churna", "B1", LATER, "10")])
    batch = StockBatch.objects.get(batch_no="B1")
    assert sell(p, final_rx, [{"prescription_item": str(line_of(final_rx).id), "batch": str(batch.id), "quantity": "1"}]).status_code == 201
    again = d.post(f"{VISITS}{visit.id}/reopen/")
    assert again.status_code == 400 and "already given" in str(again.data)
    item = line_of(final_rx)
    removed = d.patch(f"/api/v1/prescriptions/{final_rx.id}/", {"items": []}, format="json")
    assert removed.status_code == 400 and "already given" in str(removed.data)
    assert final_rx.items.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_only_doctors_may_reopen_and_not_an_open_checkup(doctor, receptionist, pharmacist, branch_a, appointment):
    d = client_for(doctor, branch_a)
    vid = open_visit(d, appointment)
    assert d.post(f"{VISITS}{vid}/reopen/").status_code == 400                       # not completed
    d.post(f"{VISITS}{vid}/complete/")
    for user in (receptionist, pharmacist):
        assert client_for(user, branch_a).post(f"{VISITS}{vid}/reopen/").status_code == 403
    appointment.refresh_from_db()
    assert appointment.status == "completed"
    assert d.post(f"{VISITS}{vid}/reopen/").status_code == 200
    appointment.refresh_from_db()
    assert appointment.status == "in_consultation" and appointment.completed_at is None
