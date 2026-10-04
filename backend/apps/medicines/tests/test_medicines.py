import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditLog
from apps.common.models import MasterValue
from apps.medicines.models import Medicine
from apps.medicines.services import add_sample_medicines
from conftest import client_for

URL = "/api/v1/medicines/"


def master(org, category, code):
    return str(MasterValue.objects.get(organization=org, category=category, code=code).id)


@pytest.fixture
def samples(org, roles):
    add_sample_medicines(org)
    return {m.name: m for m in Medicine.objects.filter(organization=org)}


@pytest.mark.django_db
def test_sample_medicines_are_marked(samples):
    assert len(samples) >= 20
    arogya = samples["Arogyavardhini Vati"]
    assert arogya.is_sample and arogya.schedule_e1 and arogya.contains_metals
    assert arogya.dosage_form.code == "vati"
    assert samples["SampleCare Triphala Tablets"].classical_equivalent == samples["Triphala Churna"]


@pytest.mark.django_db
def test_search_by_synonym_and_gujarati(pharmacist, branch_a, samples):
    client = client_for(pharmacist, branch_a)
    assert client.get(URL, {"q": "Withania"}).data["results"][0]["name"] == "Ashwagandha Churna"
    assert client.get(URL, {"q": "ત્રિફળા"}).data["count"] >= 1


@pytest.mark.django_db
def test_create_edit_keeps_versions(org, pharmacist, branch_a, roles):
    client = client_for(pharmacist, branch_a)
    res = client.post(URL, {"kind": "classical", "name": "Test Churna", "dosage_form": master(org, "dosage_form", "churna"),
                            "mrp": "50.00", "gst_rate": "12"}, format="json")
    assert res.status_code == 201, res.data
    med_id = res.data["id"]
    assert res.data["version"] == 1
    res = client.patch(f"{URL}{med_id}/", {"mrp": "60.00", "pregnancy_caution": True}, format="json")
    assert res.data["version"] == 2
    versions = client.get(f"{URL}{med_id}/versions/").data
    assert [v["version"] for v in versions] == [2, 1]
    assert versions[1]["data"]["mrp"] == "50.00"
    # Saving without a change does not create a new version
    assert client.patch(f"{URL}{med_id}/", {"mrp": "60.00"}, format="json").data["version"] == 2
    assert AuditLog.objects.filter(object_id=med_id, action="update").exists()


@pytest.mark.django_db
def test_duplicate_name_refused(pharmacist, branch_a, samples):
    res = client_for(pharmacist, branch_a).post(URL, {"kind": "classical", "name": "triphala churna"}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_branch_price_and_switch_off(pharmacist, branch_a, branch_b, samples, doctor):
    med = samples["Triphala Churna"]
    client = client_for(pharmacist, branch_a)
    res = client.patch(f"{URL}{med.id}/branch/", {"price": "99.50", "is_active": False}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["branch_price"] == "99.50" and res.data["branch_active"] is False
    # Not offered for prescribing in branch A, still in branch B, with the normal price there
    names_a = [m["name"] for m in client_for(doctor, branch_a).get(URL, {"for_rx": 1, "page_size": 100}).data["results"]]
    rx_b = client_for(doctor, branch_b).get(URL, {"for_rx": 1, "page_size": 100}).data["results"]
    assert "Triphala Churna" not in names_a
    assert next(m for m in rx_b if m["name"] == "Triphala Churna")["branch_price"] == "90.00"


@pytest.mark.django_db
def test_permissions(doctor, receptionist, branch_a, samples):
    assert client_for(doctor, branch_a).get(URL).status_code == 200
    assert client_for(doctor, branch_a).post(URL, {"name": "X"}, format="json").status_code == 403
    assert client_for(receptionist, branch_a).get(URL).status_code == 403


@pytest.mark.django_db
def test_csv_import_preview_then_save(org, pharmacist, branch_a, samples):
    client = client_for(pharmacist, branch_a)
    csv_text = (
        "kind,name,synonyms,dosage_form,mrp,schedule_e1,classical_equivalent\n"
        "classical,New Vati,new tablet,vati,70,yes,\n"
        "classical,Triphala Churna,,churna,95,no,\n"
        "proprietary,Brand X,,unknownform,10,no,\n"
        "proprietary,Brand Y,,vati,40,no,Triphala Churna\n"
    )

    def upload(dry):
        f = SimpleUploadedFile("list.csv", csv_text.encode(), content_type="text/csv")
        return client.post(URL + "import/", {"file": f, "dry_run": "1" if dry else "0"}, format="multipart")

    preview = upload(True).data
    assert preview["created"] == 2 and preview["updated"] == 1 and len(preview["errors"]) == 1
    assert not Medicine.objects.filter(name="New Vati").exists()  # preview saves nothing
    result = upload(False).data
    assert result["created"] == 2
    new = Medicine.objects.get(name="New Vati")
    assert new.schedule_e1 and new.dosage_form.code == "vati"
    assert Medicine.objects.get(name="Brand Y").classical_equivalent.name == "Triphala Churna"
    assert Medicine.objects.get(name="Triphala Churna", kind="classical").version == 2


@pytest.mark.django_db
def test_excel_import(pharmacist, branch_a, roles):
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.append(["kind", "name", "mrp"])
    sheet.append(["classical", "Excel Churna", 33])
    buffer = io.BytesIO()
    book.save(buffer)
    f = SimpleUploadedFile("list.xlsx", buffer.getvalue())
    res = client_for(pharmacist, branch_a).post(URL + "import/", {"file": f}, format="multipart")
    assert res.status_code == 200 and res.data["created"] == 1
