"""Shared test setup: a small fake clinic with two branches and one user per role."""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User, UserBranchRole
from apps.accounts.services import create_default_roles
from apps.notifications.sms import FakeSmsProvider
from apps.organizations.models import Branch, Organization

PASSWORD = "Test@Clinic2026"


@pytest.fixture(autouse=True)
def _test_settings(settings):
    settings.SMS_PROVIDER = "fake"
    settings.SHOW_DEV_OTP_ON_SCREEN = False
    FakeSmsProvider.outbox.clear()
    cache.clear()  # resets login rate limits between tests
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Test Clinic")


@pytest.fixture
def roles(org):
    from apps.organizations.management.commands.ensure_defaults import ensure_defaults_for

    ensure_defaults_for(org)  # dropdown values and consent purposes
    return create_default_roles(org)


@pytest.fixture(autouse=True)
def _private_files(settings, tmp_path):
    """Uploaded patient files go to a temporary folder during tests."""
    settings.STORAGES = {
        **settings.STORAGES,
        "private": {"BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": str(tmp_path / "private")}},
    }


@pytest.fixture
def branch_a(org):
    return Branch.objects.create(organization=org, name="Branch A", code="A")


@pytest.fixture
def branch_b(org):
    return Branch.objects.create(organization=org, name="Branch B", code="B")


def make_user(org, username, branch_roles=None, **extra):
    user = User.objects.create_user(
        username=username, password=PASSWORD, full_name=username.title(), organization=org,
        phone="9811111111", **extra,
    )
    for branch, role in (branch_roles or {}).items():
        UserBranchRole.objects.create(organization=org, user=user, branch=branch, role=role)
    return user


@pytest.fixture
def org_admin(org, roles):
    return make_user(org, "owner", is_org_admin=True)


@pytest.fixture
def receptionist(org, roles, branch_a):
    return make_user(org, "reception", {branch_a: roles["receptionist"]})


@pytest.fixture
def doctor(org, roles, branch_a, branch_b):
    return make_user(org, "doc", {branch_a: roles["doctor"], branch_b: roles["doctor"]}, is_doctor=True)


@pytest.fixture
def branch_admin(org, roles, branch_a):
    return make_user(org, "manager", {branch_a: roles["admin"]})


@pytest.fixture
def therapist(org, roles, branch_a):
    return make_user(org, "therapy", {branch_a: roles["therapist"]})


@pytest.fixture
def pharmacist(org, roles, branch_a):
    return make_user(org, "pharma", {branch_a: roles["pharmacist"]})


@pytest.fixture
def api():
    return APIClient()


def client_for(user, branch=None):
    """An API client already logged in as `user`, working in `branch`."""
    client = APIClient()
    client.force_authenticate(user)
    if branch is not None:
        client.credentials(HTTP_X_BRANCH_ID=str(branch.id))
    return client
