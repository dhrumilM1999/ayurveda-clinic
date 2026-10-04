"""
Creates FAKE demo data: 1 organization, 2 branches, rooms, and one user per role.

    python manage.py seed_demo              # add demo data
    python manage.py seed_demo --if-empty   # only if the database has no organization yet
    python manage.py seed_demo --reset      # wipe EVERYTHING and start again (DEMO_MODE only)

SAFE TO EDIT: the demo names, rooms and timings below (they are fake data).
"""
from datetime import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import DoctorSchedule, User, UserBranchRole
from apps.accounts.services import create_default_roles
from apps.organizations.management.commands.ensure_defaults import ensure_defaults_for
from apps.organizations.models import Branch, Organization, Room, RoomType

DEMO_PASSWORD = "Ayur@Demo2026"

BRANCHES = [
    {"code": "AHD", "name": "Ahmedabad - Navrangpura (Demo)", "city": "Ahmedabad", "pincode": "380009"},
    {"code": "VDR", "name": "Vadodara - Alkapuri (Demo)", "city": "Vadodara", "pincode": "390007"},
]

ROOM_TYPES = ["Consultation", "Panchakarma / Therapy", "Pharmacy", "Waiting area"]

ROOMS = {
    "AHD": [("Consultation Room 1", "Consultation"), ("Consultation Room 2", "Consultation"),
            ("Therapy Room A", "Panchakarma / Therapy"), ("Pharmacy Counter", "Pharmacy")],
    "VDR": [("Consultation Room", "Consultation"), ("Therapy Room", "Panchakarma / Therapy")],
}

# username, full name, phone, is_doctor, is_org_admin, {branch code: role code}
USERS = [
    ("admin", "Demo Owner (Admin)", "9800000001", False, True, {}),
    ("doctor1", "Dr. Asha Mehta (Demo)", "9800000002", True, False, {"AHD": "doctor", "VDR": "doctor"}),
    ("doctor2", "Dr. Ravi Patel (Demo)", "9800000003", True, False, {"VDR": "doctor"}),
    ("reception1", "Nita Shah (Demo Reception)", "9800000004", False, False, {"AHD": "receptionist"}),
    ("therapist1", "Kiran Joshi (Demo Therapist)", "9800000005", False, False, {"AHD": "therapist"}),
    ("pharmacist1", "Meena Desai (Demo Pharmacist)", "9800000006", False, False, {"AHD": "pharmacist"}),
    ("branchadmin", "Vadodara Manager (Demo)", "9800000007", False, False, {"VDR": "admin"}),
]

# FAKE demo patients: first, father/husband, surname, gender, age, mobile, city, branch code,
# conditions, allergy (or None)
DEMO_PATIENTS = [
    ("Ramesh", "Bhikhabhai", "Patel", "male", 54, "9811000001", "Ahmedabad", "AHD", ["diabetes", "hypertension"], ("drug", "Penicillin")),
    ("Sunita", "Rajesh", "Shah", "female", 42, "9811000002", "Ahmedabad", "AHD", ["thyroid"], None),
    ("Harsh", "Mahesh", "Desai", "male", 29, "9811000003", "Vadodara", "VDR", ["acidity"], ("food", "Peanuts")),
    ("Kokila", "Jayantilal", "Mehta", "female", 67, "9811000004", "Vadodara", "VDR", ["arthritis", "hypertension"], None),
    ("Aarav", "Nikhil", "Joshi", "male", 8, "9811000005", "Ahmedabad", "AHD", ["asthma"], ("environment", "Dust")),
]

# doctor username, branch code, weekdays, start, end
SCHEDULES = [
    ("doctor1", "AHD", [0, 1, 2, 3, 4], time(10, 0), time(13, 0)),
    ("doctor1", "VDR", [5], time(10, 0), time(14, 0)),
    ("doctor2", "VDR", [0, 1, 2, 3, 4, 5], time(16, 0), time(20, 0)),
]


class Command(BaseCommand):
    help = "Create fake demo data (organization, branches, rooms, users for every role)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete ALL data first (DEMO_MODE only).")
        parser.add_argument("--if-empty", action="store_true", help="Do nothing if an organization exists.")
        parser.add_argument("--add-demo-patients", action="store_true",
                            help="Only add the demo patients to the existing demo organization.")

    def handle(self, *args, **options):
        if options["reset"]:
            if not settings.DEMO_MODE:
                raise CommandError("Refusing to reset: DEMO_MODE is not true in .env.")
            self.stdout.write(self.style.WARNING("Wiping all data (demo reset)..."))
            call_command("flush", interactive=False, verbosity=0)
        elif options["add_demo_patients"]:
            org = Organization.objects.order_by("created_at").first()
            if org is None:
                raise CommandError("No organization yet. Run seed_demo first.")
            ensure_defaults_for(org)
            self._seed_patients(org)
            self.stdout.write(self.style.SUCCESS("Demo patients added."))
            return
        elif options["if_empty"] and Organization.objects.exists():
            self.stdout.write("Demo data already present - skipping seed_demo.")
            return

        with transaction.atomic():
            self._seed()
        self._print_logins()

    def _seed(self):
        org = Organization.objects.create(
            name="Demo Ayurveda Clinics", short_name="Demo Ayur",
            phone="9800000000", email="demo-clinic@example.com",
            address="DEMO ONLY - not a real clinic", default_language="en",
        )
        roles = create_default_roles(org)
        ensure_defaults_for(org)

        branches = {}
        for info in BRANCHES:
            branches[info["code"]] = Branch.objects.create(
                organization=org, state="Gujarat", address="Demo address", phone="9800000000", **info,
            )

        room_types = {
            name: RoomType.objects.create(organization=org, name=name, sort_order=i)
            for i, name in enumerate(ROOM_TYPES)
        }
        for code, rooms in ROOMS.items():
            for name, type_name in rooms:
                Room.objects.create(
                    organization=org, branch=branches[code], name=name, room_type=room_types[type_name],
                )

        users = {}
        for username, full_name, phone, is_doctor, is_org_admin, assignments in USERS:
            user = User.objects.create_user(
                username=username, password=DEMO_PASSWORD, full_name=full_name, phone=phone,
                organization=org, is_doctor=is_doctor, is_org_admin=is_org_admin,
                # The owner account may also open the Django admin site.
                is_staff=is_org_admin, is_superuser=is_org_admin,
                qualification="BAMS (demo)" if is_doctor else "",
            )
            users[username] = user
            for branch_code, role_code in assignments.items():
                UserBranchRole.objects.create(
                    organization=org, user=user, branch=branches[branch_code], role=roles[role_code],
                )

        for username, branch_code, weekdays, start, end in SCHEDULES:
            for weekday in weekdays:
                DoctorSchedule.objects.create(
                    organization=org, branch=branches[branch_code], doctor=users[username],
                    weekday=weekday, start_time=start, end_time=end, slot_minutes=15,
                )

        self._seed_patients(org)

    def _seed_patients(self, org):
        from datetime import date

        from apps.common.models import MasterValue
        from apps.patients.models import Patient, PatientAllergy, PatientCondition, PatientConsent, ConsentPurpose
        from apps.patients.services import next_uhid

        def master(category, code):
            return MasterValue.objects.get(organization=org, category=category, code=code)

        branches = {b.code: b for b in Branch.objects.filter(organization=org)}
        receptionist = User.objects.filter(organization=org, username="reception1").first()
        treatment = ConsentPurpose.objects.get(organization=org, code="treatment")
        for first, middle, last, gender, age, mobile, city, branch_code, conditions, allergy in DEMO_PATIENTS:
            if Patient.objects.filter(organization=org, mobile=mobile).exists():
                continue
            branch = branches[branch_code]
            title = "master" if age < 12 else ("mr" if gender == "male" else "mrs")
            patient = Patient.objects.create(
                organization=org, uhid=next_uhid(org), registered_branch=branch,
                title=master("title", title), first_name=first, middle_name=middle, last_name=last,
                gender=gender, date_of_birth=date(date.today().year - age, 7, 1), dob_is_estimated=True,
                mobile=mobile, city=city, state="Gujarat", preferred_language="gu",
                referral_source=master("referral_source", "walk_in"),
                created_by=receptionist, updated_by=receptionist,
                guardian_name=f"{middle} {last}" if age < 18 else "",
            )
            for code in conditions:
                PatientCondition.objects.create(organization=org, patient=patient,
                                                condition=master("medical_condition", code))
            if allergy:
                PatientAllergy.objects.create(organization=org, patient=patient,
                                              allergy_type=master("allergy_type", allergy[0]),
                                              allergen=allergy[1], severity="moderate")
            PatientConsent.objects.create(
                organization=org, patient=patient, branch=branch, purpose=treatment,
                purpose_version=treatment.version, granted=True, method="signed_form",
                language="gu", created_by=receptionist,
            )

    def _print_logins(self):
        line = "=" * 64
        self.stdout.write(self.style.SUCCESS(f"\n{line}\n DEMO LOGINS (fake data)   password for all: {DEMO_PASSWORD}\n{line}"))
        for username, full_name, _, _, is_org_admin, assignments in USERS:
            where = "all branches" if is_org_admin else ", ".join(f"{r} @ {b}" for b, r in assignments.items())
            self.stdout.write(f"  {username:<13} {full_name:<32} {where}")
        self.stdout.write("  (admin, doctors and branch admins also need an OTP - see logs.bat)")
        self.stdout.write(self.style.SUCCESS(line))
