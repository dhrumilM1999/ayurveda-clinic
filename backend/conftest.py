"""Shared test setup: a small fake clinic with two branches and one user per role."""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User, UserBranchRole
from apps.accounts.services import create_default_roles
from apps.notifications.sms import FakeSmsProvider
from apps.notifications.whatsapp import FakeWhatsAppProvider
from apps.organizations.models import Branch, Organization

PASSWORD = "Test@Clinic2026"


@pytest.fixture(autouse=True)
def _test_settings(settings):
    settings.SMS_PROVIDER = "fake"
    settings.WHATSAPP_PROVIDER = "fake"
    settings.PAYMENT_PROVIDER = "fake"
    settings.SHOW_DEV_OTP_ON_SCREEN = False
    FakeSmsProvider.outbox.clear()
    FakeWhatsAppProvider.outbox.clear()
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
    """
    Uploaded patient files go to a temporary folder during tests, never into the real storage.
    (File fields keep the storage they got at start-up, so each one is pointed to the temp folder.)
    """
    from django.apps import apps
    from django.core.files.storage import FileSystemStorage
    from django.db import models

    temp = FileSystemStorage(location=str(tmp_path / "private"))
    real_location = str(settings.PRIVATE_MEDIA_ROOT)
    swapped = []
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, models.FileField) and str(getattr(field.storage, "location", "")) == real_location:
                swapped.append((field, field.storage))
                field.storage = temp
    yield
    for field, storage in swapped:
        field.storage = storage


@pytest.fixture
def branch_a(org):
    return Branch.objects.create(organization=org, name="Branch A", code="A")


@pytest.fixture
def branch_b(org):
    return Branch.objects.create(organization=org, name="Branch B", code="B")


def set_additional_features(org, on=True, codes=None):
    """Switch optional additional features on/off for an organization (all of them by default)."""
    from apps.organizations.features_catalog import ADDITIONAL_FEATURES
    from apps.organizations.models import OrganizationFeature

    for code in codes or ADDITIONAL_FEATURES:
        OrganizationFeature.objects.update_or_create(organization=org, code=code, defaults={"enabled": on})


@pytest.fixture
def all_additional_features(org):
    """Tests of the extra pharmacy features need them switched on."""
    set_additional_features(org)


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
