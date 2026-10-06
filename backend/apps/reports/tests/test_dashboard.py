from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.emr.models import Visit
from apps.patients.models import Patient
from conftest import client_for

TODAY = timezone.localdate()
URL = "/api/v1/dashboard/today/"


@pytest.fixture
def opd_day(org, branch_a, doctor):
    """Two patients today: Asha (new case, waiting) and Ravi (follow-up, seen)."""
    asha = Patient.objects.create(organization=org, uhid="D-1", first_name="Asha", last_name="P", gender="female", mobile="9800000101")
    ravi = Patient.objects.create(organization=org, uhid="D-2", first_name="Ravi", last_name="K", gender="male", mobile="9800000102")
    Appointment.objects.create(organization=org, branch=branch_a, patient=asha, doctor=doctor, date=TODAY,
                               start_time=time(10, 0), status="checked_in", token_number=1)
    done = Appointment.objects.create(organization=org, branch=branch_a, patient=ravi, doctor=doctor, date=TODAY,
                                      start_time=time(10, 15), status="completed", token_number=2)
    Visit.objects.create(organization=org, branch=branch_a, patient=ravi, doctor=doctor, visit_date=TODAY - timedelta(days=20))
    Visit.objects.create(organization=org, branch=branch_a, patient=ravi, doctor=doctor, visit_date=TODAY, appointment=done)
    Visit.objects.create(organization=org, branch=branch_a, patient=asha, doctor=doctor, visit_date=TODAY)


@pytest.mark.django_db
def test_doctor_sees_own_opd_in_simple_words(branch_a, doctor, opd_day):
    data = client_for(doctor, branch_a).get(URL).data
    assert data["is_doctor"] is True
    mine = data["my_opd"]
    assert (mine["booked"], mine["waiting"], mine["seen"]) == (2, 1, 1)
    assert (mine["new_cases"], mine["follow_ups"]) == (1, 1)
    assert data["next_patients"][0]["patient"].startswith("Asha")
    assert "money" in data  # doctors may see bills (billing.view)


@pytest.mark.django_db
def test_money_today_by_opd_and_pharmacy(branch_a, receptionist, opd_day):
    client = client_for(receptionist, branch_a)
    appointment = Appointment.objects.get(token_number=1)
    client.post("/api/v1/opd-bills/charge/", {"appointment": str(appointment.id), "lines": [
        {"kind": "consultation", "description": "OPD consultation", "unit_price": "300"}],
        "payment": {"mode": "cash", "amount": "200"}}, format="json")
    money = client.get(URL).data["money"]
    assert Decimal(money["opd"]) == 200 and Decimal(money["pharmacy"]) == 0
    assert Decimal(money["due_today"]) == 100 and money["unpaid_bills"] == 1
    assert "my_opd" not in client.get(URL).data  # not a doctor


@pytest.mark.django_db
def test_pharmacist_sees_no_opd_numbers(branch_a, pharmacist):
    data = client_for(pharmacist, branch_a).get(URL).data
    assert "opd" not in data and "money" in data
