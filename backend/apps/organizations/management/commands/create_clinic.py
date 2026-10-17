"""
Sets up the FIRST real clinic on a new (empty) server: the organization, the first branch, the owner's
login, and the starting roles, dropdown values and consent purposes. NO demo patients, users or invoices.

SAFE TO EDIT: the questions and messages. ASK FIRST before changing what gets created.

Safe to run again: if a clinic already exists nothing is changed (only missing starting values are added).

    python manage.py create_clinic                       (asks the questions one by one)
    python manage.py create_clinic --org-name "My Clinic" --branch-name "Main" --branch-code MAIN \
        --city Surat --admin-username owner --admin-name "Dr Name" --admin-phone 9876543210 --generate-password
"""
import getpass
import json
import re
import secrets
import string

from datetime import time
from pathlib import Path

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import DoctorSchedule, User, UserBranchRole
from apps.accounts.services import create_default_roles
from apps.organizations.management.commands.ensure_defaults import ensure_defaults_for
from apps.organizations.models import Branch, Organization

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def make_password(length=16):
    """A random password that passes the password rules (upper, lower, digit, symbol)."""
    symbols = "@#%+=?"
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length - 2)) + "".join(
            secrets.choice(symbols) for _ in range(2)
        )
        if (any(c.islower() for c in password) and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)):
            return password


class Command(BaseCommand):
    help = "Create the first clinic (organization, branch, owner login) on an empty server."

    def add_arguments(self, parser):
        parser.add_argument("--org-name", help="Clinic name, e.g. the name printed on bills")
        parser.add_argument("--branch-name", help="Name of the first branch")
        parser.add_argument("--branch-code", help="Short code used in invoice numbers, e.g. AHD")
        parser.add_argument("--city", default=None)
        parser.add_argument("--state", default=None, help="Default: Gujarat")
        parser.add_argument("--gstin", default=None, help="Optional, 15 characters")
        parser.add_argument("--admin-username", help="Login name of the owner")
        parser.add_argument("--admin-name", help="Full name of the owner")
        parser.add_argument("--admin-phone", help="Mobile number (the login OTP goes here)")
        parser.add_argument("--admin-email", default="")
        parser.add_argument("--generate-password", action="store_true", help="Make a strong password and show it once")
        parser.add_argument("--profile", help="JSON file with the clinic's real details, e.g. clinic_profiles/vednath.json")
        parser.add_argument("--no-input", action="store_true", help="Never ask questions (missing values are an error)")

    # ---- small helpers ---------------------------------------------------------------
    def _ask(self, options, key, label, default=None, required=True):
        value = options.get(key)
        if value in (None, ""):
            if options["no_input"]:
                value = default
            else:
                suffix = f" [{default}]" if default else ""
                value = input(f"{label}{suffix}: ").strip() or default
        if required and not value:
            raise CommandError(f"{label} is required.")
        return (value or "").strip()

    def _password(self, options):
        if options["generate_password"]:
            return make_password(), True
        if options["no_input"]:
            raise CommandError("With --no-input please also give --generate-password.")
        while True:
            first = getpass.getpass("Password for the owner (typing is hidden): ")
            if first == "":
                self.stdout.write("The password cannot be empty.")
                continue
            if first != getpass.getpass("Type the password again: "):
                self.stdout.write("The two passwords are different. Try again.")
                continue
            try:
                validate_password(first)
            except ValidationError as error:
                self.stdout.write("That password is too weak: " + " ".join(error.messages))
                continue
            return first, False

    def _load_profile(self, options):
        """Fill options that were not given on the command line from the profile file."""
        path = options.get("profile")
        if not path:
            return {}
        file = Path(path)
        if not file.is_absolute():
            file = Path(__file__).resolve().parents[4] / path   # relative to the backend folder
        try:
            profile = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise CommandError(f"Cannot read the profile file {file}: {error}")
        org, branch, owner = profile.get("organization", {}), profile.get("branch", {}), profile.get("owner", {})
        wanted = {
            "org_name": org.get("name"), "branch_name": branch.get("name"), "branch_code": branch.get("code"),
            "city": branch.get("city"), "state": branch.get("state"), "gstin": branch.get("gstin"),
            "admin_username": owner.get("username"), "admin_name": owner.get("full_name"),
        }
        for key, value in wanted.items():
            if options.get(key) in (None, "") and value:
                options[key] = value
        return profile

    # ---- main --------------------------------------------------------------------------
    def handle(self, *args, **options):
        existing = Organization.objects.order_by("created_at").first()
        if existing:
            ensure_defaults_for(existing)
            create_default_roles(existing)
            self.stdout.write(
                f"A clinic already exists ({existing.name}). Nothing was changed. "
                "(Missing starting values were added if any.)"
            )
            return

        profile = self._load_profile(options)
        org_name = self._ask(options, "org_name", "Clinic name")
        branch_name = self._ask(options, "branch_name", "First branch name", default="Main Branch")
        branch_code = self._ask(options, "branch_code", "Branch short code (letters, e.g. AHD)", default="MAIN").upper()
        city = self._ask(options, "city", "City", required=False)
        state = self._ask(options, "state", "State", default="Gujarat")
        gstin = self._ask(options, "gstin", "GSTIN (press Enter to skip)", required=False).upper()
        username = self._ask(options, "admin_username", "Owner login name (no spaces)", default="owner")
        full_name = self._ask(options, "admin_name", "Owner full name")
        phone = self._ask(options, "admin_phone", "Owner mobile number")
        email = self._ask(options, "admin_email", "Owner e-mail (login codes can go here; Enter to skip)", required=False)

        if not re.fullmatch(r"[A-Z0-9]{1,20}", branch_code):
            raise CommandError("The branch code can only have letters and numbers (no spaces).")
        if gstin and not GSTIN_PATTERN.match(gstin):
            raise CommandError(
                "That GSTIN does not look right (15 characters, like 24ABCDE1234F1Z5). Leave it empty to skip."
            )
        if not re.fullmatch(r"[\w.@+-]{1,150}", username):
            raise CommandError("The login name can only have letters, numbers and . @ + - _")
        if not re.fullmatch(r"\+?[0-9 ]{10,15}", phone):
            raise CommandError("The mobile number should have 10 digits, e.g. 9876543210.")
        if User.all_objects.filter(username=username).exists():
            raise CommandError(f"The login name '{username}' is already used.")

        password, generated = self._password(options)

        with transaction.atomic():
            org_info = profile.get("organization", {})
            org = Organization.objects.create(
                name=org_name, short_name=org_info.get("short_name") or org_name[:50],
                legal_name=org_info.get("legal_name", ""), gstin=gstin, phone=phone, email=email,
                default_language=org_info.get("default_language", "en"),
            )
            roles = create_default_roles(org)
            ensure_defaults_for(org)
            branch = Branch.objects.create(
                organization=org, name=branch_name, code=branch_code, city=city, state=state, gstin=gstin, phone=phone,
            )
            owner_info = profile.get("owner", {})
            owner = User.objects.create_user(
                username=username, password=password, full_name=full_name, phone=phone, email=email,
                organization=org, is_org_admin=True, is_staff=True, is_superuser=True,
                is_doctor=bool(owner_info.get("is_doctor")), qualification=owner_info.get("qualification", ""),
                registration_number=owner_info.get("registration_number", ""),
            )
            UserBranchRole.objects.create(organization=org, user=owner, branch=branch, role=roles["admin"])
            schedule = profile.get("schedule")
            if schedule and owner.is_doctor:
                for weekday in schedule.get("weekdays", []):
                    for start, end in schedule.get("slots", []):
                        DoctorSchedule.objects.create(
                            organization=org, branch=branch, doctor=owner, weekday=weekday,
                            start_time=time.fromisoformat(start), end_time=time.fromisoformat(end),
                            slot_minutes=schedule.get("slot_minutes", 15),
                        )

        self.stdout.write("")
        self.stdout.write(f"Done. Clinic '{org.name}' with branch '{branch.name}' is ready.")
        self.stdout.write(f"  Login name : {username}")
        if generated:
            self.stdout.write(f"  Password   : {password}")
            self.stdout.write("  (Shown ONLY NOW. Write it down and change it after your first login.)")
        self.stdout.write("No demo patients, users or bills were added.")
