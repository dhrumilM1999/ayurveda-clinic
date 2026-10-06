"""Pharmacy stock labels (barcode, no patient details), scanning them, extra scanned medicines and counter sales."""
import pytest

from apps.audit.models import AuditLog
from apps.pharmacy.models import StockBatch
from apps.pharmacy.tests.test_pharmacy import LATER, meds, receive  # noqa: F401 (fixtures)
from conftest import client_for, set_additional_features

pytestmark = pytest.mark.usefixtures("all_additional_features")


def labels(client, items, **params):
    return client.get("/api/v1/stock/labels/", {"items": ",".join(f"{b.id}:{n}" for b, n in items), **params})


@pytest.mark.django_db
def test_stock_labels_give_a_batch_a_barcode_that_scans(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC9", LATER, "3")])
    batch = StockBatch.objects.get(batch_no="TC9")
    assert batch.barcode == ""
    res = labels(client, [(batch, 3)], layout="compact")
    assert res.status_code == 200 and res.content[:4] == b"%PDF"
    batch.refresh_from_db()
    assert len(batch.barcode) == 12 and batch.barcode.startswith("29")
    # Printing again keeps the same code
    labels(client, [(batch, 1)], layout="standard")
    first = batch.barcode
    batch.refresh_from_db()
    assert batch.barcode == first
    # The scanner finds that exact batch
    found = client.get("/api/v1/stock/scan/", {"code": first}).data
    assert found["scanned_batch"] == str(batch.id)
    assert AuditLog.objects.filter(action="print", object_type="pharmacy.stocklabel").count() == 2


@pytest.mark.django_db
def test_maker_barcode_is_kept(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC8", LATER, "1")])
    batch = StockBatch.objects.get(batch_no="TC8")
    batch.barcode = "8901234567890"
    batch.save()
    assert labels(client, [(batch, 1)]).status_code == 200
    batch.refresh_from_db()
    assert batch.barcode == "8901234567890"


@pytest.mark.django_db
def test_stock_labels_need_their_switch_and_a_sane_count(org, pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC7", LATER, "1")])
    batch = StockBatch.objects.get(batch_no="TC7")
    assert labels(client, [(batch, 501)]).status_code == 400
    assert labels(client, [(batch, 0)]).status_code == 400
    set_additional_features(org, on=False, codes=["pharmacy_stock_labels"])
    assert labels(client, [(batch, 1)]).status_code == 403
