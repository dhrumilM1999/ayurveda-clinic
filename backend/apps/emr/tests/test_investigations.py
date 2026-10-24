from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.emr.investigations import load_sample_lab_tests
from apps.emr.models import LabTest, Visit, VisitInvestigation
from apps.patients.models import Patient
from conftest import client_for

LABS = "/api/v1/lab-tests/"
INV = "/api/v1/investigations/"


@pytest.fixture
def patient(org, roles):
    return Patient.objects.create(organization=org, uhid="1", first_name="Kamla", last_name="Shah", gender="female",
                                  mobile="9825011111", preferred_language="gu")


@pytest.fixture
def visit(org, branch_a, patient, doctor):
    return Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, visit_date=timezone.localdate())


@pytest.mark.django_db
def test_starting_list_is_added_once_and_searchable(org, doctor, branch_a, roles):
    assert LabTest.objects.filter(organization=org).count() > 40  # the starting list comes with the clinic set-up
    assert load_sample_lab_tests(org) == 0                        # and is never added twice
    c = client_for(doctor, branch_a)
    assert any("CBC" in t["name"] for t in c.get(LABS, {"q": "cbc"}).data)
    assert c.get(LABS, {"q": "થાઇરોઇડ"}).data  # found by the Gujarati name
    res = c.post(LABS, {"name": "Serum amylase", "category": "blood"}, format="json")
    assert res.status_code == 201
    assert c.post(LABS, {"name": "Serum amylase", "category": "blood"}, format="json").status_code == 400  # same name twice
    LabTest.objects.filter(name="Serum amylase").update(is_active=False)
    assert not any(t["name"] == "Serum amylase" for t in c.get(LABS).data)  # switched off = hidden from the list


@pytest.mark.django_db
def test_doctor_advises_tests_then_the_report_comes(org, doctor, branch_a, visit, patient):
    load_sample_lab_tests(org)
    c = client_for(doctor, branch_a)
    cbc = LabTest.objects.get(name__startswith="CBC")
    one = c.post(INV, {"visit": str(visit.id), "test": str(cbc.id), "note": "fasting"}, format="json")
    assert one.status_code == 201, one.data
    assert one.data["status"] == "advised" and one.data["test_name"] == cbc.name and one.data["advised_on"] == str(visit.visit_date)
    free = c.post(INV, {"visit": str(visit.id), "test_name": "Rheumatoid panel"}, format="json")  # a test not in the list
    assert free.status_code == 201
    assert c.post(INV, {"visit": str(visit.id)}, format="json").status_code == 400                  # nothing chosen
    listing = c.get(INV, {"visit": str(visit.id)}).data
    assert {r["test_name"] for r in listing} == {cbc.name, "Rheumatoid panel"}

    # the staff upload the report as a patient document, the doctor links it
    doc = c.post("/api/v1/patient-documents/", {"patient": str(patient.id), "title": "CBC report",
                 "file": SimpleUploadedFile("cbc.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf")}, format="multipart")
    assert doc.status_code == 201, doc.data
    done = c.patch(f"{INV}{one.data['id']}/", {"document": doc.data["id"], "result_text": "Hb 11.2"}, format="json")
    assert done.status_code == 200 and done.data["status"] == "done" and done.data["reported_on"] == str(timezone.localdate())
    assert done.data["document_title"] == "CBC report"
    # not needed: hidden from the list, not deleted
    assert c.delete(f"{INV}{free.data['id']}/").status_code == 204
    assert VisitInvestigation.all_objects.filter(pk=free.data["id"]).exists()
    assert len(c.get(INV, {"visit": str(visit.id)}).data) == 1
    # pending reports of a patient (all visits)
    later = Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                 visit_date=timezone.localdate() + timedelta(days=1))
    c.post(INV, {"visit": str(later.id), "test_name": "ESR"}, format="json")
    pending = c.get(INV, {"patient": str(patient.id), "status": "advised"}).data
    assert [p["test_name"] for p in pending] == ["ESR"]


@pytest.mark.django_db
def test_wrong_things_are_refused(org, doctor, receptionist, pharmacist, branch_a, branch_b, visit, patient):
    c = client_for(doctor, branch_a)
    inv = c.post(INV, {"visit": str(visit.id), "test_name": "ESR"}, format="json").data["id"]
    other = Patient.objects.create(organization=org, uhid="2", first_name="Other", last_name="P", gender="male", mobile="9825022222")
    doc = c.post("/api/v1/patient-documents/", {"patient": str(other.id), "title": "Not hers",
                 "file": SimpleUploadedFile("x.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf")}, format="multipart").data["id"]
    assert c.patch(f"{INV}{inv}/", {"document": doc}, format="json").status_code == 400          # another patient's file
    assert c.patch(f"{INV}{inv}/", {"reported_on": str(timezone.localdate() + timedelta(days=3))}, format="json").status_code == 400
    assert c.get(INV).status_code == 400                                                         # a visit or patient must be chosen
    for user in (receptionist, pharmacist):                                                      # no check-up notes for them
        assert client_for(user, branch_a).get(INV, {"visit": str(visit.id)}).status_code == 403
        assert client_for(user, branch_a).post(INV, {"visit": str(visit.id), "test_name": "X"}, format="json").status_code == 403
    assert client_for(doctor, branch_b).post(INV, {"visit": str(visit.id), "test_name": "X"}, format="json").status_code in (400, 403, 404)


@pytest.mark.django_db
def test_tests_advised_are_printed_on_the_prescription_in_the_patients_language(org, doctor, branch_a, visit, patient):
    from apps.documents.services import prescription_context
    from apps.prescriptions.services import save_prescription

    load_sample_lab_tests(org)
    c = client_for(doctor, branch_a)
    c.post(INV, {"visit": str(visit.id), "test": str(LabTest.objects.get(name="ESR").id)}, format="json")
    c.post(INV, {"visit": str(visit.id), "test_name": "Special panel"}, format="json")
    rx = save_prescription(visit, [{"medicine": None, "medicine_name": "Ginger tea"}], "", doctor)
    assert prescription_context(rx, "en")["investigations"] == ["ESR", "Special panel"]
    assert prescription_context(rx, "gu")["investigations"] == ["ઈએસઆર", "Special panel"]
    res = c.get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": 1})
    assert res.status_code == 200 and res.content[:4] == b"%PDF"
