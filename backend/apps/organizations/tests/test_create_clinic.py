"""Tests for `manage.py create_clinic` (first clinic on a new server)."""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import Role, User, UserBranchRole
from apps.common.models import MasterValue
from apps.organizations.models import Branch, Organization
from apps.patients.models import ConsentPurpose

ARGS = dict(
    org_name="Test Ayurved", branch_name="Main", branch_code="main", city="Surat",
    admin_username="boss", admin_name="Dr Boss", admin_phone="9876543210", generate_password=True, no_input=True,
)


def run(**overrides):
    call_command("create_clinic", **{**ARGS, **overrides})


@pytest.mark.django_db
def test_creates_clinic_branch_owner_and_starting_data(capsys):
    run(gstin="24ABCDE1234F1Z5")
    org = Organization.objects.get()
    assert org.name == "Test Ayurved"
    branch = Branch.objects.get()
    assert (branch.code, branch.city, branch.state, branch.gstin) == ("MAIN", "Surat", "Gujarat", "24ABCDE1234F1Z5")
    owner = User.objects.get(username="boss")
    assert owner.is_org_admin and owner.is_staff and owner.organization == org
    assert UserBranchRole.objects.get(user=owner).role.code == "admin"
    assert Role.objects.filter(organization=org).count() >= 5
    assert MasterValue.objects.filter(organization=org).exists()
    assert ConsentPurpose.objects.filter(organization=org).exists()
    # The generated password is shown once and really works
    out = capsys.readouterr().out
    password = next(line.split(":", 1)[1].strip() for line in out.splitlines() if "Password" in line and ":" in line)
    assert owner.check_password(password)


@pytest.mark.django_db
def test_no_demo_data_is_created():
    from apps.patients.models import Patient

    run()
    assert User.objects.count() == 1
    assert Patient.objects.count() == 0
    from apps.billing.models import Invoice

    assert Invoice.objects.count() == 0


@pytest.mark.django_db
def test_running_twice_changes_nothing(capsys):
    run()
    capsys.readouterr()
    run(org_name="Another Name", admin_username="other")
    assert "already exists" in capsys.readouterr().out
    assert Organization.objects.count() == 1
    assert User.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("bad", [
    {"gstin": "NOTAGSTIN"}, {"branch_code": "has space"}, {"admin_phone": "123"}, {"admin_username": "bad name"},
])
def test_bad_input_is_refused_and_nothing_is_saved(bad):
    with pytest.raises(CommandError):
        run(**bad)
    assert Organization.objects.count() == 0
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_typed_password_is_checked_for_strength(monkeypatch):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "Strong#Pass2026")
    monkeypatch.setattr("builtins.input", lambda prompt="": "")  # keep the defaults for unanswered questions
    run(generate_password=False, no_input=False)
    assert User.objects.get(username="boss").check_password("Strong#Pass2026")


@pytest.mark.django_db
def test_no_input_needs_generate_password():
    with pytest.raises(CommandError):
        run(generate_password=False)
