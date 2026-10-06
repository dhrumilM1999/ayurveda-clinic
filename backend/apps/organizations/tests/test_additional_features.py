import pytest

from apps.organizations.models import Organization
from apps.organizations.services import is_feature_enabled, organization_features
from conftest import client_for

URL = "/api/v1/additional-features/"


def _row(response, code):
    return next(r for r in response.data if r["code"] == code)


@pytest.mark.django_db
def test_additional_features_are_off_by_default(org, org_admin, branch_a):
    response = client_for(org_admin, branch_a).get(URL)
    assert response.status_code == 200
    basics = {"pharmacy_batch_tracking", "pharmacy_expiry_tracking", "pharmacy_purchase_price",
              "pharmacy_selling_price", "pharmacy_suppliers"}
    # Extras are off; the stock basics (how the pharmacy always worked) are on
    assert {r["code"] for r in response.data if r["enabled"]} == basics
    assert not is_feature_enabled(branch_a, "pharmacy_racks")


@pytest.mark.django_db
def test_org_admin_switches_a_feature_for_the_whole_organization(org, org_admin, branch_a, branch_b):
    response = client_for(org_admin, branch_a).patch(f"{URL}pharmacy_racks/", {"enabled": True}, format="json")
    assert response.status_code == 200
    assert _row(response, "pharmacy_racks")["enabled"] is True
    # Every branch of the organization gets it, and the branch module list still works
    assert is_feature_enabled(branch_a, "pharmacy_racks") and is_feature_enabled(branch_b, "pharmacy_racks")
    assert is_feature_enabled(branch_a, "pharmacy")


@pytest.mark.django_db
def test_other_organizations_are_not_affected(org, org_admin, branch_a):
    client_for(org_admin, branch_a).patch(f"{URL}pharmacy_billing/", {"enabled": True}, format="json")
    other = Organization.objects.create(name="Other clinic")
    assert organization_features(org.id)["pharmacy_billing"] is True
    assert organization_features(other.id)["pharmacy_billing"] is False


@pytest.mark.django_db
def test_feature_needing_another_stays_off_until_that_one_is_on(org, org_admin, branch_a):
    client = client_for(org_admin, branch_a)
    response = client.patch(f"{URL}pharmacy_discounts/", {"enabled": True}, format="json")
    row = _row(response, "pharmacy_discounts")
    assert row["switched_on"] is True and row["enabled"] is False and row["requires"] == "pharmacy_billing"
    response = client.patch(f"{URL}pharmacy_billing/", {"enabled": True}, format="json")
    assert _row(response, "pharmacy_discounts")["enabled"] is True


@pytest.mark.django_db
def test_only_org_admins_can_switch(pharmacist, branch_a):
    client = client_for(pharmacist, branch_a)
    assert client.get(URL).status_code == 200
    assert client.patch(f"{URL}pharmacy_racks/", {"enabled": True}, format="json").status_code == 403


@pytest.mark.django_db
def test_unknown_feature(org_admin, branch_a):
    assert client_for(org_admin, branch_a).patch(f"{URL}nope/", {"enabled": True}, format="json").status_code == 404


@pytest.mark.django_db
def test_needs_are_checked_down_the_chain(org, org_admin, branch_a):
    client = client_for(org_admin, branch_a)
    for code in ("pharmacy_billing", "pharmacy_discounts"):
        client.patch(f"{URL}{code}/", {"enabled": True}, format="json")
    assert organization_features(org.id)["pharmacy_discounts"] is True
    # Discounts need bills, bills need prices: prices off switches both off
    client.patch(f"{URL}pharmacy_selling_price/", {"enabled": False}, format="json")
    values = organization_features(org.id)
    assert values["pharmacy_billing"] is False and values["pharmacy_discounts"] is False


@pytest.mark.django_db
def test_label_format_choice(org_admin, pharmacist, branch_a):
    url = "/api/v1/additional-choices/"
    rows = client_for(pharmacist, branch_a).get(url).data
    assert next(r for r in rows if r["code"] == "label_format")["value"] == "standard"
    assert client_for(pharmacist, branch_a).patch(f"{url}label_format/", {"value": "compact"}, format="json").status_code == 403
    admin = client_for(org_admin, branch_a)
    assert admin.patch(f"{url}label_format/", {"value": "huge"}, format="json").status_code == 400
    res = admin.patch(f"{url}label_format/", {"value": "compact"}, format="json")
    assert next(r for r in res.data if r["code"] == "label_format")["value"] == "compact"
