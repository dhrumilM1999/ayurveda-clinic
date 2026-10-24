"""
One whole clinic day in one test, as the real people do it:
front desk registers + bills the consultation -> doctor writes the prescription -> pharmacy gives the medicines
(stock goes down, a medicine that is out of stock is flagged) -> everything is on ONE bill -> the owner's totals agree.
"""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import DoctorSchedule
from apps.billing.models import ConsultationFee, Invoice
from apps.medicines.models import Medicine
from apps.medicines.services import add_sample_medicines
from apps.pharmacy.models import StockBatch
from conftest import client_for, set_additional_features

API = "/api/v1/"
LATER = str(date.today() + timedelta(days=400))


@pytest.fixture
def day(org, roles, branch_a, doctor, pharmacist, receptionist, branch_admin):
    set_additional_features(org)  # every extra switched on (incl. one combined bill)
    add_sample_medicines(org)
    for weekday in range(7):
        DoctorSchedule.objects.create(organization=org, branch=branch_a, doctor=doctor, weekday=weekday,
                                      start_time=time(0, 0), end_time=time(23, 0), slot_minutes=15)
    ConsultationFee.objects.create(organization=org, branch=branch_a, doctor=doctor, new_case_fee=300, follow_up_fee=150,
                                   follow_up_days=15)
    meds = {m.name: m for m in Medicine.objects.filter(organization=org)}
    pharm = client_for(pharmacist, branch_a)
    # stock: Triphala has 10, Ashwagandha only 1, Kaishore Guggulu none at all
    for name, qty in (("Triphala Churna", "10"), ("Ashwagandha Churna", "1")):
        res = pharm.post(API + "purchases/", {"invoice_no": "S-" + name[:3].upper(), "invoice_date": str(date.today()), "items": [{
            "medicine": str(meds[name].id), "batch_no": name[:3].upper() + "1", "expiry_date": LATER, "quantity": qty,
            "purchase_rate": "50", "mrp": "112", "gst_rate": "12"}]}, format="json")
        assert res.status_code == 201, res.data
    return meds


@pytest.mark.django_db
def test_a_whole_clinic_day(org, branch_a, doctor, receptionist, pharmacist, branch_admin, day):
    meds = day
    desk, dr, pharm, owner = (client_for(u, branch_a) for u in (receptionist, doctor, pharmacist, branch_admin))

    # ---- 1. front desk registers the patient and gives a walk-in token
    patient = desk.post(API + "patients/", {"first_name": "Kamla", "last_name": "Shah", "gender": "female", "age": 52,
                                            "mobile": "9825011111"}, format="json")
    assert patient.status_code == 201, patient.data
    appt = desk.post(API + "appointments/", {"patient": patient.data["id"], "doctor": str(doctor.id), "kind": "walk_in",
                                             "reason": "Joint pain"}, format="json")
    assert appt.status_code == 201, appt.data
    assert appt.data["status"] == "checked_in" and appt.data["token_number"] == 1

    # ---- 2. the consultation fee is billed at the desk and paid in cash
    sug = desk.get(API + "opd-bills/suggest/", {"appointment": appt.data["id"]})
    assert sug.status_code == 200, sug.data
    fee = Decimal(str(sug.data["consultation"]["fee"]))
    bill = desk.post(API + "opd-bills/charge/", {"appointment": appt.data["id"], "lines": [{
        "kind": "consultation", "description": sug.data["consultation"]["description"], "unit_price": str(fee)}],
        "payment": {"mode": "cash", "amount": str(fee)}}, format="json")
    assert bill.status_code == 201, bill.data
    assert bill.data["status"] == "paid"

    # ---- 3. the doctor opens the check-up and writes the prescription
    visit = dr.post(API + "visits/", {"appointment": appt.data["id"]}, format="json")
    assert visit.status_code == 201, visit.data
    vid = visit.data["id"]
    assert dr.patch(f"{API}visits/{vid}/", {
        "complaints": [{"label": "Joint pain", "duration": 3, "duration_unit": "months"}],
        "diagnoses": [{"label": "Sandhivata", "kind": "final"}], "advice": ["Warm water"]}, format="json").status_code == 200

    def line(name, **extra):
        return {"medicine": str(meds[name].id), "dose": "3", "dose_unit": "gram", "frequency": "1-0-1", "timing": "After food",
                "anupana": "Warm water", "duration": 15, "duration_unit": "days", **extra}
    rx = dr.post(API + "prescriptions/", {"visit": vid, "items": [
        line("Triphala Churna"), line("Ashwagandha Churna"), line("Kaishore Guggulu")]}, format="json")
    assert rx.status_code == 201, rx.data

    # the doctor can see which medicines the pharmacy has (before finishing)
    stock = {m["name"]: m for m in dr.get(API + "medicines/", {"q": "Churna", "page_size": 50}).data["results"]}
    assert stock["Triphala Churna"].get("stock_available") is not None
    assert Decimal(str(stock["Triphala Churna"]["stock_available"])) == 10
    kg = dr.get(API + "medicines/", {"q": "Kaishore", "page_size": 5}).data["results"][0]
    assert Decimal(str(kg["stock_available"])) == 0

    assert dr.post(f"{API}visits/{vid}/complete/").status_code == 200

    # ---- 4. the pharmacy sees the prescription and what is missing
    queue = pharm.get(API + "dispensing/", {"date": str(date.today())}).data
    row = next(r for r in queue if r["id"] == rx.data["id"])
    assert row["status"] == "pending"
    assert row.get("missing_stock") == 1  # Kaishore Guggulu: not in stock
    detail = pharm.get(f"{API}dispensing/{rx.data['id']}/").data
    by_name = {l["medicine_name"]: l for l in detail["lines"]}
    assert by_name["Kaishore Guggulu"]["batches"] == []                      # nothing to give
    assert by_name["Kaishore Guggulu"].get("out_of_stock") is True
    assert by_name["Triphala Churna"]["batches"] and by_name["Ashwagandha Churna"]["batches"]

    # ---- 5. the pharmacy gives what it has; the medicines go on the SAME bill as the consultation
    sale_lines = [{"prescription_item": by_name[n]["id"], "batch": by_name[n]["batches"][0]["id"], "quantity": "1"}
                  for n in ("Triphala Churna", "Ashwagandha Churna")]
    sold = pharm.post(f"{API}dispensing/{rx.data['id']}/sell/", {"items": sale_lines,
                      "payment": {"mode": "upi", "amount": "224"}}, format="json")
    assert sold.status_code == 201, sold.data
    invoices = Invoice.objects.filter(patient_id=patient.data["id"])
    assert invoices.count() == 1, [i.number for i in invoices]               # ONE bill: consultation + medicines
    invoice = invoices.get()
    assert invoice.series == "OP" and invoice.lines.count() == 3
    assert invoice.total_amount == fee + Decimal("224")
    assert invoice.paid_amount == fee + Decimal("224") and invoice.status == "paid"

    # ---- 6. stock went down, and the shop is told what to re-order
    assert StockBatch.objects.get(batch_no="TRI1").quantity == 9
    assert StockBatch.objects.get(batch_no="ASH1").quantity == 0
    alerts = pharm.get(API + "stock/alerts/").data
    assert alerts["out"] == 1 and alerts["needed"] == 1                      # Ashwagandha sold out; Kaishore was asked for but never stocked
    needed = pharm.get(API + "stock/needed/").data
    assert [n["name"] for n in needed] == ["Kaishore Guggulu"] and needed[0]["times"] == 1
    assert pharm.get(f"{API}dispensing/{rx.data['id']}/").data["status"] == "partly"

    # ---- 7. the owner's numbers agree
    summary = owner.get(API + "invoices/summary/").data
    assert Decimal(summary["received"]["cash"]) == fee and Decimal(summary["received"]["upi"]) == Decimal("224")
    today = owner.get(API + "dashboard/today/").data
    assert today  # the dashboard loads for the owner
