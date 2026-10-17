"""
Walks EVERY address of the API and proves who can open it.
- Nobody logged in: only the public addresses answer (login, branding, enquiry form, verify, health).
- A logged-in person with an empty role (no permissions): nothing private opens.
- Another clinic's admin: never sees this clinic's records.
"""
import re

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role
from conftest import client_for, make_user

from .url_walk import DUMMY_ID, all_api_paths

# The only addresses that may answer without logging in. Everything else must say 401/403.
PUBLIC = {
    "/api/v1/health/",
    "/api/v1/auth/login/",
    "/api/v1/auth/verify-otp/",
    "/api/v1/auth/refresh/",
    "/api/v1/branding/",
    "/api/v1/branding/logo/",
    "/api/v1/public/enquiry-form/",
    "/api/v1/public/enquiries/",
}
PUBLIC_PREFIXES = ("/api/v1/verify/",)

# Allowed for any logged-in staff member, even with an empty role (they only show the person's own info
# or harmless lookups). Everything else must refuse a person without permissions.
OPEN_TO_ANY_STAFF = {
    "/api/v1/auth/me/",
    "/api/v1/auth/logout/",
    "/api/v1/auth/change-password/",
    # Lookups every screen needs (dropdown values, switches, clinic name/address, paper sizes): no patient data
    "/api/v1/",
    "/api/v1/additional-choices/",
    "/api/v1/additional-features/",
    "/api/v1/consent-purposes/",
    "/api/v1/feature-flags/",
    "/api/v1/masters/",
    "/api/v1/organization/",
    "/api/v1/print-settings/paper-defaults/",
}

METHODS = ["get", "post", "put", "patch", "delete"]


def is_public(path):
    return path in PUBLIC or path.startswith(PUBLIC_PREFIXES)


def test_the_walk_finds_the_api():
    paths = [p for p, _, _ in all_api_paths()]
    assert len(paths) > 60, "the URL walk found too few addresses - the test would prove nothing"
    assert "/api/v1/auth/login/" in paths and "/api/v1/patients/" in paths
    for public in PUBLIC:
        assert public in paths, f"{public} is listed as public but does not exist (update the list)"


@pytest.mark.django_db
def test_nobody_logged_in_can_open_anything_private():
    anonymous = APIClient()
    leaks = []
    for path, _, _ in all_api_paths():
        if is_public(path):
            continue
        for method in METHODS:
            response = getattr(anonymous, method)(path, {}, format="json")
            if response.status_code not in (401, 403):
                leaks.append(f"{method.upper()} {path} -> {response.status_code}")
    assert not leaks, "These addresses answered without a login:\n" + "\n".join(leaks)


@pytest.mark.django_db
def test_public_addresses_do_not_show_private_data():
    """The public addresses answer, but never with patient or staff details."""
    anonymous = APIClient()
    for path in ("/api/v1/health/", "/api/v1/branding/", "/api/v1/public/enquiry-form/"):
        response = anonymous.get(path)
        assert response.status_code == 200
        text = response.content.decode().lower()
        for word in ("patient", "mobile", "password", "uhid", "invoice"):
            assert word not in text, f"{path} mentions '{word}'"
    # The public form can only be written to, never read from
    assert anonymous.get("/api/v1/public/enquiries/").status_code in (405, 401, 403)


@pytest.mark.django_db
def test_a_person_with_an_empty_role_opens_nothing_private(org, branch_a):
    empty_role = Role.objects.create(organization=org, name="Empty", code="empty", permissions=[])
    user = make_user(org, "nobody", {branch_a: empty_role})
    client = client_for(user, branch_a)
    opened = []
    for path, has_params, _ in all_api_paths():
        if is_public(path) or path in OPEN_TO_ANY_STAFF:
            continue
        for method in ("get", "post", "delete"):
            response = getattr(client, method)(path, {}, format="json")
            if response.status_code in (200, 201, 204):
                opened.append(f"{method.upper()} {path} -> {response.status_code}")
    assert not opened, "A person with no permissions could open:\n" + "\n".join(opened)


@pytest.mark.django_db
def test_another_clinics_admin_sees_nothing_of_this_clinic():
    """Fill clinic A with the full sample data, then let clinic B's owner open every list and detail address."""
    from django.core.management import call_command

    from apps.organizations.models import Branch, Organization

    call_command("seed_demo", verbosity=0)
    org_a = Organization.objects.get(name="Ayurveda Clinic")
    secrets = _ids_of_organization(org_a)
    assert len(secrets) > 50, "sample clinic is empty - the test would prove nothing"

    org_b = Organization.objects.create(name="Other Clinic")
    branch_b = Branch.objects.create(organization=org_b, name="B", code="B")
    owner_b = make_user(org_b, "ownerb", is_org_admin=True)
    client = client_for(owner_b, branch_b)
    # Owner A, to learn real ids of clinic A for detail addresses
    from apps.accounts.models import User

    owner_a = User.objects.get(username="admin")
    branch_a = Branch.objects.filter(organization=org_a).first()
    client_a = client_for(owner_a, branch_a)

    leaked = []
    for path, has_params, _ in all_api_paths():
        if is_public(path) or path in OPEN_TO_ANY_STAFF or path.startswith("/api/v1/auth/"):
            continue
        if has_params:
            continue
        response = client.get(path)
        body = response.content.decode(errors="ignore")
        found = [i for i in secrets if i in body]
        if found:
            leaked.append(f"GET {path} shows {len(found)} record(s) of clinic A")
        # Detail addresses: take a real id from clinic A's list and ask for it as clinic B
        listing = client_a.get(path)
        data = listing.json() if listing.status_code == 200 and "json" in listing.get("Content-Type", "") else None
        rows = data.get("results") if isinstance(data, dict) else data
        if isinstance(rows, list) and rows and isinstance(rows[0], dict) and rows[0].get("id"):
            detail = f"{path}{rows[0]['id']}/"
            answer = client.get(detail)
            if answer.status_code == 200:
                leaked.append(f"GET {detail} (clinic A's record) opened for clinic B")
    assert not leaked, "\n".join(leaked)


def _ids_of_organization(org):
    """Every primary key of every row that belongs to the organization (as text)."""
    from django.apps import apps

    ids = set()
    for model in apps.get_models():
        if any(f.name == "organization" for f in model._meta.get_fields()):
            manager = getattr(model, "all_objects", model._default_manager)
            for pk in manager.filter(organization=org).values_list("pk", flat=True)[:400]:
                text = str(pk)
                if re.fullmatch(r"[0-9a-f-]{36}", text):  # UUIDs only: small numbers would match by accident
                    ids.add(text)
    return ids


@pytest.mark.django_db
def test_staff_of_branch_b_cannot_use_branch_a_header(org, roles, branch_a, branch_b):
    user = make_user(org, "onlyb", {branch_b: roles["receptionist"]})
    client = client_for(user, branch_a)
    for path in ("/api/v1/patients/", "/api/v1/appointments/", "/api/v1/invoices/"):
        assert client.get(path).status_code == 403, path
