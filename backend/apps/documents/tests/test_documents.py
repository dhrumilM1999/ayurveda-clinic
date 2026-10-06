from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.documents.models import IssuedDocument
from apps.emr.models import Visit
from apps.medicines.models import Medicine
from apps.medicines.services import add_sample_medicines
from apps.patients.models import Patient
from apps.prescriptions.services import save_prescription
from conftest import client_for, make_user

TODAY = timezone.localdate()


@pytest.fixture
def visit(org, branch_a, doctor):
    patient = Patient.objects.create(organization=org, uhid="D-9", first_name="Mira", last_name="Joshi", gender="female",
                                     mobile="9876500011", preferred_language="gu")
    return Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, visit_date=TODAY,
                                follow_up_date=TODAY + timedelta(days=15))


@pytest.fixture
def rx(org, roles, visit, doctor):
    add_sample_medicines(org)
    medicine = Medicine.objects.get(organization=org, name="Triphala Churna")
    return save_prescription(visit, [{"medicine": medicine, "medicine_name": medicine.name, "dose": "3", "frequency": "1-0-1",
                                      "duration": 30}], "Take after food", doctor)


@pytest.mark.django_db
def test_prescription_pdf_number_duplicate_and_verify(doctor, branch_a, rx):
    client = client_for(doctor, branch_a)
    url = f"/api/v1/documents/prescription/{rx.id}/"
    res = client.get(url, {"preview": "1"})
    assert res.status_code == 200 and res["Content-Type"] == "application/pdf"
    doc = IssuedDocument.objects.get(kind="prescription", object_id=str(rx.id))
    assert doc.number.startswith("A/RX/") and doc.print_count == 0  # preview is not a print
    client.get(url, {"size": "a4"})
    client.get(url)
    doc.refresh_from_db()
    assert doc.print_count == 2  # the second print is the DUPLICATE COPY
    assert client.get(url, {"size": "huge"}).status_code == 400
    # Anyone with the QR code can check it is genuine - without medical details
    public = APIClient().get(f"/api/v1/verify/{doc.token}/")
    assert public.status_code == 200 and public.data["valid"] is True
    assert public.data["patient_initials"] == "M. J." and "medicine" not in str(public.data).lower()
    assert APIClient().get("/api/v1/verify/not-a-real-code/").status_code == 404


@pytest.mark.django_db
def test_who_can_print(org, roles, branch_a, rx, pharmacist):
    therapist = make_user(org, "ther9", {branch_a: roles["therapist"]})
    assert client_for(therapist, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/").status_code == 403
    assert client_for(pharmacist, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": "1"}).status_code == 200


@pytest.mark.django_db
def test_follow_up_card_and_prakriti_need_their_data(doctor, branch_a, visit):
    client = client_for(doctor, branch_a)
    assert client.get(f"/api/v1/documents/follow-up-card/{visit.id}/").status_code == 200
    assert client.get(f"/api/v1/documents/prakriti/{visit.id}/").status_code == 400  # no Prakriti answers yet
    visit.follow_up_date = None
    visit.save()
    assert client.get(f"/api/v1/documents/follow-up-card/{visit.id}/").status_code == 400


@pytest.mark.django_db
def test_certificate_create_print_cancel(doctor, branch_a, visit):
    client = client_for(doctor, branch_a)
    bad = client.post("/api/v1/certificates/", {"patient": str(visit.patient_id), "doctor": str(doctor.id), "kind": "medical"},
                      format="json")
    assert bad.status_code == 400  # rest dates needed
    res = client.post("/api/v1/certificates/", {
        "patient": str(visit.patient_id), "doctor": str(doctor.id), "visit": str(visit.id), "kind": "medical",
        "diagnosis": "Acute gastritis", "rest_from": str(TODAY), "rest_to": str(TODAY + timedelta(days=2))}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["number"].startswith("A/MC/")
    cert_id = res.data["id"]
    assert client.get(f"/api/v1/documents/certificate/{cert_id}/").status_code == 200
    token = IssuedDocument.objects.get(kind="certificate", object_id=cert_id).token
    assert client.post(f"/api/v1/certificates/{cert_id}/cancel/", {}, format="json").status_code == 400
    assert client.post(f"/api/v1/certificates/{cert_id}/cancel/", {"reason": "Wrong dates"}, format="json").status_code == 200
    public = APIClient().get(f"/api/v1/verify/{token}/").data
    assert public["valid"] is False and public["cancelled"] is True


@pytest.mark.django_db
def test_whatsapp_share_needs_consent(doctor, branch_a, rx):
    res = client_for(doctor, branch_a).post(f"/api/v1/documents/prescription/{rx.id}/whatsapp/")
    assert res.status_code == 200 and res.data["consent"] is False and res.data["link"] == ""
