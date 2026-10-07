import pytest

from apps.medicines.catalog_loader import add_ayurveda_generic_medicines, add_homeopathy_medicines
from apps.medicines.models import Medicine
from conftest import client_for

URL = "/api/v1/medicines/"


@pytest.mark.django_db
def test_catalogs_add_many_medicines_and_can_be_run_twice(org):
    first = add_homeopathy_medicines(org)
    assert first > 700
    assert add_homeopathy_medicines(org) == 0  # nothing duplicated
    assert add_ayurveda_generic_medicines(org) > 100
    assert add_ayurveda_generic_medicines(org) == 0
    arnica = Medicine.objects.get(organization=org, kind="homeopathy", name="Arnica Montana 30C")
    assert arnica.strength == "30C" and arnica.dosage_form.code == "dilution" and arnica.dose_unit.code == "pills"
    sample = Medicine.objects.get(organization=org, kind="homeopathy", name="Natrum Muriaticum 6X (biochemic)")
    assert sample.dosage_form.code == "biochemic" and sample.is_sample
    metals = Medicine.objects.get(organization=org, name="Lohasava")
    assert metals.contains_metals and metals.pregnancy_caution


@pytest.mark.django_db
def test_homeopathy_is_hidden_until_the_switch_is_on(org, org_admin, branch_a):
    add_homeopathy_medicines(org)
    client = client_for(org_admin, branch_a)
    off = client.get(URL, {"q": "Arnica", "page_size": 50})
    assert off.status_code == 200 and off.data["count"] == 0
    assert client.patch("/api/v1/additional-features/medicines_homeopathy/", {"enabled": True}, format="json").status_code == 200
    on = client.get(URL, {"q": "Arnica", "page_size": 50})
    assert on.data["count"] >= 4  # 6C, 30C, 200C, 1M, tincture, ointments ...
    only = client.get(URL, {"kind": "homeopathy", "page_size": 10})
    assert only.data["count"] > 700 and all(m["kind"] == "homeopathy" for m in only.data["results"])
