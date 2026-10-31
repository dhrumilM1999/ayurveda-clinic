"""The "Send Order" lab order slip: the tests the doctor advised, to hand to the patient / send to the lab."""
import pytest

from apps.documents.models import IssuedDocument
from apps.emr.models import VisitInvestigation
from conftest import client_for

from .test_documents import visit  # noqa: F401  (the same demo check-up the other document tests use)


def advise(visit, name, **kw):
    return VisitInvestigation.objects.create(organization=visit.organization, visit=visit, patient=visit.patient, test_name=name,
                                             advised_on=visit.visit_date, **kw)


@pytest.mark.django_db
def test_lab_order_is_a_pdf_with_the_chosen_tests(doctor, branch_a, visit):
    cbc, lft = advise(visit, "CBC"), advise(visit, "LFT")
    res = client_for(doctor, branch_a).get(f"/api/v1/documents/lab-order/{visit.id}/",
                                           {"tests": f"{cbc.id},{lft.id}", "lab": "Super Nova Lab", "urgent": "1"})
    assert res.status_code == 200, getattr(res, "data", "")
    assert res["Content-Type"] == "application/pdf" and res.content.startswith(b"%PDF")
    doc = IssuedDocument.objects.get(kind="lab_order", object_id=str(visit.id))
    assert doc.number.startswith("A/LO/")


@pytest.mark.django_db
def test_lab_order_needs_at_least_one_test_of_this_visit(org, branch_a, doctor, visit):
    from apps.emr.models import Visit

    client = client_for(doctor, branch_a)
    url = f"/api/v1/documents/lab-order/{visit.id}/"
    assert client.get(url).status_code == 400  # no test chosen
    assert client.get(url, {"tests": "not-an-id"}).status_code == 400
    elsewhere = Visit.objects.create(organization=org, branch=branch_a, patient=visit.patient, doctor=doctor,
                                     visit_date=visit.visit_date)
    assert client.get(url, {"tests": str(advise(elsewhere, "ESR").id)}).status_code == 400  # a test of another check-up


@pytest.mark.django_db
def test_lab_order_is_for_people_who_may_see_check_ups(receptionist, branch_a, visit):
    advise(visit, "CBC")
    assert client_for(receptionist, branch_a).get(f"/api/v1/documents/lab-order/{visit.id}/").status_code == 403
