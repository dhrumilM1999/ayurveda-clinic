from datetime import date

import pytest
from django.utils import timezone

from apps.common.models import MasterValue
from apps.emr.models import Visit
from apps.medicines.models import Medicine
from apps.medicines.services import add_sample_medicines
from apps.patients.models import Patient, PatientAllergy, PatientCondition
from conftest import client_for

URL = "/api/v1/prescriptions/"


@pytest.fixture
def meds(org, roles):
    add_sample_medicines(org)
    return {m.name: m for m in Medicine.objects.filter(organization=org)}


def make_patient(org, gender="male", age=40, **extra):
    return Patient.objects.create(organization=org, uhid=f"T-{gender}{age}", first_name="Test", last_name="Patient",
                                  gender=gender, mobile="9876543210",
                                  date_of_birth=date(date.today().year - age, 1, 1), **extra)


@pytest.fixture
def visit(org, branch_a, doctor):
    patient = make_patient(org)
    return Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                visit_date=timezone.localdate())


def line(med, **extra):
    return {"medicine": str(med.id), "dose": "2", "dose_unit": "tablet", "frequency": "1-0-1",
            "timing": "After food", "anupana": "Warm water", "duration": 15, "duration_unit": "days", **extra}


@pytest.mark.django_db
def test_write_prescription_with_copies(doctor, branch_a, visit, meds):
    client = client_for(doctor, branch_a)
    med = meds["Kaishore Guggulu"]
    res = client.post(URL, {"visit": str(visit.id), "items": [line(med)], "notes": "Review after 15 days"}, format="json")
    assert res.status_code == 201, res.data
    item = res.data["items"][0]
    assert item["medicine_name"] == "Kaishore Guggulu" and item["medicine_version"] == 1
    assert item["dosage_form"] == "Guggulu"
    # The medicine is renamed later: the old prescription keeps the old name
    med.name = "Kaishore Guggulu (new label)"
    med.save()
    again = client.get(f"{URL}{res.data['id']}/").data
    assert again["items"][0]["medicine_name"] == "Kaishore Guggulu"
    assert client.post(URL, {"visit": str(visit.id), "items": []}, format="json").status_code == 400  # only one


@pytest.mark.django_db
def test_edit_lines_keeps_ids(doctor, branch_a, visit, meds):
    client = client_for(doctor, branch_a)
    created = client.post(URL, {"visit": str(visit.id), "items": [line(meds["Triphala Churna"]), line(meds["Ashwagandha Churna"])]},
                          format="json").data
    first = created["items"][0]
    res = client.patch(f"{URL}{created['id']}/", {"items": [{**line(meds["Triphala Churna"]), "id": first["id"], "dose": "5"}]},
                       format="json")
    assert res.status_code == 200, res.data
    assert len(res.data["items"]) == 1 and res.data["items"][0]["id"] == first["id"] and res.data["items"][0]["dose"] == "5"


@pytest.mark.django_db
def test_free_text_medicine(doctor, branch_a, visit):
    res = client_for(doctor, branch_a).post(URL, {"visit": str(visit.id), "items": [
        {"medicine_name": "Home remedy: ginger tea", "frequency": "1-0-1"}]}, format="json")
    assert res.status_code == 201 and res.data["items"][0]["medicine"] is None


@pytest.mark.django_db
def test_safety_rules(org, doctor, branch_a, meds, roles):
    client = client_for(doctor, branch_a)

    def rules(patient, names, **extra):
        res = client.post(URL + "check/", {"patient": str(patient.id), "items": [line(meds[n], **extra) for n in names]},
                          format="json")
        return {(w["rule"], w["level"]) for w in res.data["warnings"]}

    adult_man = make_patient(org)
    found = rules(adult_man, ["Arogyavardhini Vati"])
    assert ("schedule_e1", "warning") in found and ("metals", "warning") in found
    assert ("long_course", "warning") in rules(adult_man, ["Arogyavardhini Vati"], duration=4, duration_unit="months")

    woman = make_patient(org, gender="female", age=30)
    assert ("pregnancy_check", "warning") in rules(woman, ["Abhayarishta"])
    PatientCondition.objects.create(organization=org, patient=woman,
                                    condition=MasterValue.objects.get(organization=org, category="medical_condition", code="pregnant"))
    assert ("pregnancy", "danger") in rules(woman, ["Abhayarishta"])

    child = make_patient(org, age=8)
    assert ("child", "danger") in rules(child, ["Arogyavardhini Vati"])

    PatientAllergy.objects.create(organization=org, patient=adult_man, allergen="Guggulu", severity="moderate")
    assert ("allergy", "danger") in rules(adult_man, ["Kaishore Guggulu"])
    assert ("duplicate", "warning") in rules(adult_man, ["Triphala Churna", "Triphala Churna"])
    assert rules(make_patient(org, age=50), ["Triphala Churna"]) == set()


@pytest.mark.django_db
def test_completing_visit_makes_prescription_final(doctor, branch_a, visit, meds):
    client = client_for(doctor, branch_a)
    rx = client.post(URL, {"visit": str(visit.id), "items": [line(meds["Triphala Churna"])]}, format="json").data
    assert rx["status"] == "draft"
    client.post(f"/api/v1/visits/{visit.id}/complete/")
    assert client.get(f"{URL}{rx['id']}/").data["status"] == "final"
    # The pharmacy list of today shows it
    finals = client.get(URL, {"status": "final"}).data["results"]
    assert [p["id"] for p in finals] == [rx["id"]]


@pytest.mark.django_db
def test_who_can_see_and_write(visit, meds, receptionist, pharmacist, branch_a, doctor):
    rx = client_for(doctor, branch_a).post(URL, {"visit": str(visit.id), "items": [line(meds["Triphala Churna"])]},
                                          format="json").data
    assert client_for(pharmacist, branch_a).get(f"{URL}{rx['id']}/").status_code == 200
    assert client_for(pharmacist, branch_a).patch(f"{URL}{rx['id']}/", {"items": []}, format="json").status_code == 403
    assert client_for(receptionist, branch_a).get(f"{URL}{rx['id']}/").status_code == 403


@pytest.mark.django_db
def test_templates(org, doctor, branch_a, meds, roles):
    client = client_for(doctor, branch_a)
    dx = MasterValue.objects.get(organization=org, category="diagnosis", code="amlapitta")
    res = client.post("/api/v1/prescription-templates/", {
        "name": "Amlapitta - standard", "diagnosis": str(dx.id),
        "items": [line(meds["Avipattikar Churna"], dose="3", dose_unit="g")],
    }, format="json")
    assert res.status_code == 201, res.data
    assert res.data["items"][0]["medicine_name"] == "Avipattikar Churna"
    assert client.post("/api/v1/prescription-templates/", {"name": "Empty", "items": []}, format="json").status_code == 400
    client.patch(f"/api/v1/prescription-templates/{res.data['id']}/", {"is_active": False}, format="json")
    assert client.get("/api/v1/prescription-templates/").data == []


@pytest.mark.django_db
def test_medicine_days_saved_and_kept(doctor, branch_a, visit, meds):
    client = client_for(doctor, branch_a)
    created = client.post(URL, {"visit": str(visit.id), "items": [line(meds["Triphala Churna"], duration=180)],
                                "medicine_days": 180}, format="json")
    assert created.status_code == 201, created.data
    assert created.data["medicine_days"] == 180
    # Saving lines without medicine_days keeps it; null clears it; bad values are refused
    res = client.patch(f"{URL}{created.data['id']}/", {"items": [line(meds["Triphala Churna"])]}, format="json")
    assert res.data["medicine_days"] == 180
    assert client.patch(f"{URL}{created.data['id']}/", {"medicine_days": 0}, format="json").status_code == 400
    assert client.patch(f"{URL}{created.data['id']}/", {"medicine_days": None}, format="json").data["medicine_days"] is None
