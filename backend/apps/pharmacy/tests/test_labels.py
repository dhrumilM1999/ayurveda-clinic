import pytest

from apps.pharmacy.labels import build_labels
from apps.pharmacy.tests.test_pharmacy import LATER, final_rx, meds, receive, sell  # noqa: F401 (fixtures)
from conftest import client_for, set_additional_features

URL = "/api/v1/medicine-labels/"


@pytest.mark.django_db
def test_labels_need_the_switch(pharmacist, branch_a, final_rx):
    assert client_for(pharmacist, branch_a).get(URL, {"prescription": str(final_rx.id)}).status_code == 403


@pytest.mark.django_db
def test_prescription_labels_pdf_in_each_format(org, doctor, branch_a, final_rx):
    set_additional_features(org, codes=["medicine_labels"])
    client = client_for(doctor, branch_a)
    for label_format in ("compact", "standard", "detailed"):
        res = client.get(URL, {"prescription": str(final_rx.id), "layout": label_format})
        assert res.status_code == 200 and res["Content-Type"] == "application/pdf"
    assert client.get(URL, {"prescription": str(final_rx.id), "layout": "huge"}).status_code == 400


@pytest.mark.django_db
def test_label_fields_follow_the_switches(org, pharmacist, branch_a, meds, final_rx):
    set_additional_features(org, codes=["medicine_labels", "label_batch", "label_price"])
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TB1", LATER, "5", 0, "50", "90")])
    line = client.get(f"/api/v1/dispensing/{final_rx.id}/").data["lines"][0]
    sale = sell(client, final_rx, [{"prescription_item": line["id"], "batch": line["batches"][0]["id"], "quantity": "1"}])
    from apps.pharmacy.models import Dispense

    data = build_labels(prescription=final_rx, dispense=Dispense.objects.get(pk=sale.data["dispense"]))
    label = data["labels"][0]
    assert label["medicine"] == "Triphala Churna" and label["batch"] == "TB1" and str(label["price"]) == "90.00"
    assert label["times"] is None or len(label["times"]) == 3
    # Batch off on labels: not printed
    set_additional_features(org, on=False, codes=["label_batch"])
    data = build_labels(prescription=final_rx, dispense=Dispense.objects.get(pk=sale.data["dispense"]))
    assert data["labels"][0]["batch"] == ""
    assert client.get(URL, {"dispense": sale.data["dispense"]}).status_code == 200
