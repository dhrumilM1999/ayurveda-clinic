"""
Creates SAMPLE data for practice: 1 clinic, 1 main branch, rooms, one user per role,
a few sample patients and today's sample appointments. All names and numbers are made up.

    python manage.py seed_demo              # add the sample data
    python manage.py seed_demo --if-empty   # only if the database has no clinic yet (runs on every start)
    python manage.py seed_demo --reset      # wipe EVERYTHING and start again (DEMO_MODE only)
    python manage.py seed_demo --add-sample-appointments   # add today's sample appointments again

SAFE TO EDIT: the sample names, rooms and timings below (they are made up).
Change the clinic name and address later on the Settings screen.
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

SAMPLE_PASSWORD = "Ayur@2026"

CLINIC = {
    "name": "Ayurveda Clinic", "short_name": "Ayurveda", "phone": "9800000000",
    "email": "clinic@example.com", "address": "Main Road, Ahmedabad", "default_language": "en",
}

BRANCH = {"code": "MAIN", "name": "Main Branch", "city": "Ahmedabad", "pincode": "380009",
          "state": "Gujarat", "address": "Main Road, Ahmedabad", "phone": "9800000000"}

ROOM_TYPES = ["Consultation", "Panchakarma / Therapy", "Pharmacy", "Waiting area"]

ROOMS = [("Consultation Room 1", "Consultation"), ("Consultation Room 2", "Consultation"),
         ("Therapy Room", "Panchakarma / Therapy"), ("Pharmacy Counter", "Pharmacy")]

# username, full name, phone, is_doctor, is_org_admin, role code in the main branch
USERS = [
    ("admin", "Clinic Owner", "9800000001", False, True, None),
    ("doctor1", "Dr. Asha Mehta", "9800000002", True, False, "doctor"),
    ("doctor2", "Dr. Ravi Patel", "9800000003", True, False, "doctor"),
    ("reception1", "Nita Shah", "9800000004", False, False, "receptionist"),
    ("therapist1", "Kiran Joshi", "9800000005", False, False, "therapist"),
    ("pharmacist1", "Meena Desai", "9800000006", False, False, "pharmacist"),
]

# Sample patients (made up): first, father/husband, surname, gender, age, mobile, city, conditions, allergy
SAMPLE_PATIENTS = [
    ("Ramesh", "Bhikhabhai", "Patel", "male", 54, "9811000001", "Ahmedabad", ["diabetes", "hypertension"], ("drug", "Penicillin")),
    ("Sunita", "Rajesh", "Shah", "female", 42, "9811000002", "Ahmedabad", ["thyroid"], None),
    ("Harsh", "Mahesh", "Desai", "male", 29, "9811000003", "Gandhinagar", ["acidity"], ("food", "Peanuts")),
    ("Kokila", "Jayantilal", "Mehta", "female", 67, "9811000004", "Ahmedabad", ["arthritis", "hypertension"], None),
    ("Aarav", "Nikhil", "Joshi", "male", 8, "9811000005", "Ahmedabad", ["asthma"], ("environment", "Dust")),
]

# doctor username, weekdays (0 = Monday ... 5 = Saturday), start, end
SCHEDULES = [
    ("doctor1", [0, 1, 2, 3, 4, 5], time(10, 0), time(13, 0)),
    ("doctor1", [0, 1, 2, 3, 4], time(17, 0), time(20, 0)),
    ("doctor2", [0, 1, 2, 3, 4, 5], time(10, 0), time(14, 0)),
]


class Command(BaseCommand):
    help = "Create sample data (clinic, main branch, rooms, users for every role, sample patients)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete ALL data first (DEMO_MODE only).")
        parser.add_argument("--if-empty", action="store_true", help="Do nothing if a clinic exists.")
        parser.add_argument("--add-sample-appointments", action="store_true",
                            help="Add today's sample appointments and walk-ins.")

    def handle(self, *args, **options):
        if options["reset"]:
            if not settings.DEMO_MODE:
                raise CommandError("Refusing to reset: DEMO_MODE is not true in .env.")
            self.stdout.write(self.style.WARNING("Wiping all data..."))
            call_command("flush", interactive=False, verbosity=0)
        elif options["add_sample_appointments"]:
            org = Organization.objects.order_by("created_at").first()
            if org is None:
                raise CommandError("No clinic yet. Run seed_demo first.")
            self._seed_appointments(org)
            self.stdout.write(self.style.SUCCESS("Sample appointments added for today."))
            return
        elif options["if_empty"] and Organization.objects.exists():
            self.stdout.write("Data already present - skipping sample data.")
            return

        with transaction.atomic():
            self._seed()
        self._print_logins()

    def _seed(self):
        org = Organization.objects.create(**CLINIC)
        roles = create_default_roles(org)
        ensure_defaults_for(org)
        branch = Branch.objects.create(organization=org, **BRANCH)

        room_types = {
            name: RoomType.objects.create(organization=org, name=name, sort_order=i)
            for i, name in enumerate(ROOM_TYPES)
        }
        for name, type_name in ROOMS:
            Room.objects.create(organization=org, branch=branch, name=name, room_type=room_types[type_name])

        users = {}
        for username, full_name, phone, is_doctor, is_org_admin, role_code in USERS:
            user = User.objects.create_user(
                username=username, password=SAMPLE_PASSWORD, full_name=full_name, phone=phone,
                organization=org, is_doctor=is_doctor, is_org_admin=is_org_admin,
                # The owner account may also open the Django admin site.
                is_staff=is_org_admin, is_superuser=is_org_admin,
                qualification="BAMS" if is_doctor else "",
            )
            users[username] = user
            if role_code:
                UserBranchRole.objects.create(organization=org, user=user, branch=branch, role=roles[role_code])

        for username, weekdays, start, end in SCHEDULES:
            for weekday in weekdays:
                DoctorSchedule.objects.create(
                    organization=org, branch=branch, doctor=users[username],
                    weekday=weekday, start_time=start, end_time=end, slot_minutes=15,
                )

        self._seed_patients(org, branch)
        self._seed_appointments(org)

    def _seed_patients(self, org, branch):
        from datetime import date

        from apps.common.models import MasterValue
        from apps.patients.models import ConsentPurpose, Patient, PatientAllergy, PatientCondition, PatientConsent
        from apps.patients.services import next_uhid

        def master(category, code):
            return MasterValue.objects.get(organization=org, category=category, code=code)

        receptionist = User.objects.filter(organization=org, username="reception1").first()
        treatment = ConsentPurpose.objects.get(organization=org, code="treatment")
        communication = ConsentPurpose.objects.get(organization=org, code="communication")
        for first, middle, last, gender, age, mobile, city, conditions, allergy in SAMPLE_PATIENTS:
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
            # Sample patients agree to treatment and to SMS/WhatsApp messages
            for purpose in (treatment, communication):
                PatientConsent.objects.create(
                    organization=org, patient=patient, branch=branch, purpose=purpose,
                    purpose_version=purpose.version, granted=True, method="signed_form",
                    language="gu", created_by=receptionist,
                )

    def _seed_appointments(self, org):
        """Today: two walk-ins waiting. Next working day: two booked appointments."""
        from datetime import datetime, timedelta

        from django.utils import timezone

        from apps.appointments.models import Appointment
        from apps.appointments.services import change_status
        from apps.patients.models import Patient

        branch = org.main_branch()
        doctor = User.objects.filter(organization=org, username="doctor1").first()
        receptionist = User.objects.filter(organization=org, username="reception1").first()
        if not branch or not doctor:
            return
        today = timezone.localdate()
        if Appointment.objects.filter(branch=branch, date=today).exists():
            return
        patients = list(Patient.objects.filter(organization=org).order_by("created_at"))
        if len(patients) < 4:
            return
        next_day = today + timedelta(days=1)
        if next_day.weekday() == 6:  # the clinic is closed on Sunday
            next_day += timedelta(days=1)
        plan = [  # patient, day, time, reason, walk-in?
            (patients[0], today, None, "Follow-up: sugar control", True),
            (patients[1], today, None, "Thyroid review", True),
            (patients[2], next_day, (11, 0), "Acidity, first visit", False),
            (patients[3], next_day, (11, 30), "Knee pain follow-up", False),
        ]
        for patient, day, start, reason, walk_in in plan:
            start_time = datetime.strptime(f"{start[0]}:{start[1]}", "%H:%M").time() if start else None
            end_time = (datetime.combine(day, start_time) + timedelta(minutes=15)).time() if start else None
            appointment = Appointment.objects.create(
                organization=org, branch=branch, patient=patient, doctor=doctor, date=day,
                start_time=start_time, end_time=end_time, kind="walk_in" if walk_in else "booked",
                reason=reason, created_by=receptionist, updated_by=receptionist,
            )
            if walk_in:
                change_status(appointment, "check_in", receptionist)

    def _print_logins(self):
        line = "=" * 64
        self.stdout.write(self.style.SUCCESS(f"\n{line}\n SAMPLE LOGINS   password for all: {SAMPLE_PASSWORD}\n{line}"))
        for username, full_name, _, _, is_org_admin, role_code in USERS:
            self.stdout.write(f"  {username:<13} {full_name:<20} {'owner (all access)' if is_org_admin else role_code}")
        self.stdout.write("  (admin and doctors also need an OTP - shown on the login screen and in logs.bat)")
        self.stdout.write(self.style.SUCCESS(line))
