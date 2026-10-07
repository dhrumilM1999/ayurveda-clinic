from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.enquiries.models import Enquiry
from conftest import client_for, set_additional_features

FORM = "/api/v1/public/enquiry-form/"
SEND = "/api/v1/public/enquiries/"
STAFF = "/api/v1/enquiries/"


def payload(**extra):
    data = {"name": "Meena Shah", "phone": "+91 98250 12345", "concern": "Joint pain", "message": "Knee pain for 3 months",
            "preferred_time": "morning", "language": "gu", "consent_contact": True}
    data.update(extra)
    return data


@pytest.fixture
def on(org):
    set_additional_features(org, codes=["online_enquiry"])


@pytest.mark.django_db
def test_form_is_closed_until_the_switch_is_on(org, branch_a):
    assert APIClient().get(FORM).data["enabled"] is False
    assert APIClient().post(SEND, payload(), format="json").status_code == 404
    set_additional_features(org, codes=["online_enquiry"])
    form = APIClient().get(FORM).data
    assert form["enabled"] is True and form["clinic"] == org.name
    assert [b["name"] for b in form["branches"]] == [branch_a.name] and form["concerns"]


@pytest.mark.django_db
def test_visitor_sends_an_enquiry(on, org, branch_a):
    res = APIClient().post(SEND, payload(branch=str(branch_a.id)), format="json")
    assert res.status_code == 201 and res.data == {"ok": True}
    e = Enquiry.objects.get()
    assert e.phone == "9825012345" and e.status == "new" and e.source == "website" and e.branch_id == branch_a.id
    assert e.consent_contact and e.language == "gu"


@pytest.mark.django_db
def test_bad_input_and_bots_are_stopped(on, org):
    client = APIClient()
    assert "phone" in client.post(SEND, payload(phone="12345"), format="json").data
    assert "consent_contact" in client.post(SEND, payload(consent_contact=False), format="json").data
    assert "name" in client.post(SEND, payload(name=" "), format="json").data
    yesterday = str(timezone.localdate() - timedelta(days=1))
    assert "preferred_date" in client.post(SEND, payload(preferred_date=yesterday), format="json").data
    # A bot fills the hidden field: it is told "ok" but nothing is saved
    assert client.post(SEND, payload(website="http://spam"), format="json").status_code == 201
    assert Enquiry.objects.count() == 0


@pytest.mark.django_db
def test_the_same_number_twice_in_ten_minutes_is_one_enquiry(on, org):
    client = APIClient()
    for _ in range(2):
        assert client.post(SEND, payload(), format="json").status_code == 201
    assert Enquiry.objects.count() == 1


@pytest.mark.django_db
def test_website_origin_is_allowed_only_if_listed(on, settings):
    settings.ENQUIRY_ALLOWED_ORIGINS = ["https://www.myclinic.in"]
    ok = APIClient().get(FORM, HTTP_ORIGIN="https://www.myclinic.in")
    assert ok["Access-Control-Allow-Origin"] == "https://www.myclinic.in"
    other = APIClient().get(FORM, HTTP_ORIGIN="https://evil.example")
    assert "Access-Control-Allow-Origin" not in other


@pytest.mark.django_db
def test_front_desk_follows_up(on, org, branch_a, receptionist, pharmacist):
    APIClient().post(SEND, payload(), format="json")
    desk = client_for(receptionist, branch_a)
    rows = desk.get(STAFF).data["results"]
    assert len(rows) == 1 and rows[0]["phone"] == "9825012345" and rows[0]["status"] == "new"
    assert desk.get(STAFF + "summary/").data["new"] == 1
    res = desk.patch(f"{STAFF}{rows[0]['id']}/", {"status": "contacted", "notes": "Called, will come Monday",
                                                   "follow_up_on": str(timezone.localdate() + timedelta(days=2))}, format="json")
    assert res.status_code == 200 and res.data["status"] == "contacted"
    assert desk.get(STAFF + "summary/").data["new"] == 0
    # Phone enquiry recorded by staff
    made = desk.post(STAFF, {"name": "Ramesh Patel", "phone": "9811000009", "concern": "Piles"}, format="json")
    assert made.status_code == 201 and made.data["source"] == "phone"
    # Nobody deletes enquiries; the pharmacist has no access
    assert desk.delete(f"{STAFF}{rows[0]['id']}/").status_code == 405
    assert client_for(pharmacist, branch_a).get(STAFF).status_code == 403


@pytest.mark.django_db
def test_staff_screen_is_closed_when_the_switch_is_off(org, branch_a, receptionist):
    assert client_for(receptionist, branch_a).get(STAFF).status_code == 403
