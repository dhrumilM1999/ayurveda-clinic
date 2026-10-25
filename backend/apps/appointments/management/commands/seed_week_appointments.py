"""
Fills the next working days with 10-20 booked appointments a day (made-up reasons, the sample patients), through the
real booking API as the front desk, so the week can be tested like a real clinic week.

    python manage.py seed_week_appointments              # tomorrow up to next Saturday (about 11 working days)
    python manage.py seed_week_appointments --days 14    # the next 14 days
Only when DEMO_MODE=true (never on a real clinic). Running it again adds nothing to days that already have 10 or more.
"""
import random
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.appointments.services import doctor_slots
from apps.organizations.models import Organization
from apps.patients.models import Patient

REASONS = [
    "Knee pain, follow-up", "Acidity and gas", "Back pain (Kati Shoola)", "Constipation", "Skin rash, first visit",
    "Joint pain review", "Sugar control follow-up", "Thyroid review", "Migraine / headache", "Hair fall",
    "Cold and cough", "Sleep problem", "Weight management", "Piles, follow-up", "Irregular periods",
    "Neck pain and stiffness", "Panchakarma advice", "General check-up", "Allergy, sneezing", "Fatigue and weakness",
]


class Command(BaseCommand):
    help = "Book 10-20 sample appointments a day for the next working days (DEMO_MODE only)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=0, help="How many days ahead (default: until next Saturday).")
        parser.add_argument("--today", action="store_true", help="Also fill today (the free times that have not passed).")
        parser.add_argument("--min", type=int, default=10)
        parser.add_argument("--max", type=int, default=20)

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError("Refusing: DEMO_MODE is not true. This command is only for sample data.")
        org = Organization.objects.order_by("created_at").first()
        branch = org.main_branch() if org else None
        doctor = User.objects.filter(organization=org, username="doctor1").first()
        front = User.objects.filter(organization=org, username="reception1").first()
        if not (branch and doctor and front):
            raise CommandError("Run seed_demo first (clinic, doctor1 and reception1 are needed).")
        patients = list(Patient.objects.filter(organization=org).order_by("created_at"))
        if len(patients) < 20:
            raise CommandError("Not enough sample patients (need at least 20).")

        today = timezone.localdate()
        last = today + timedelta(days=options["days"]) if options["days"] else today + timedelta(days=(5 - today.weekday()) % 7 + 7)
        client = APIClient(HTTP_HOST="localhost")
        client.force_authenticate(front)
        client.credentials(HTTP_X_BRANCH_ID=str(branch.id))
        rng = random.Random(f"week-{today}")
        made = 0
        day = today if options["today"] else today + timedelta(days=1)
        while day <= last:
            if day.weekday() == 6:  # Sunday: closed
                day += timedelta(days=1)
                continue
            have = Appointment.objects.filter(branch=branch, date=day).exclude(status="cancelled").count()
            want = rng.randint(options["min"], options["max"])
            free = [s["start"] for s in doctor_slots(branch, doctor, day) if s["status"] == "free"]
            rng.shuffle(free)
            booked_patients = set(Appointment.objects.filter(branch=branch, date=day).values_list("patient_id", flat=True))
            pool = [p for p in patients if p.id not in booked_patients]
            rng.shuffle(pool)
            for start, patient in list(zip(sorted(free[: max(0, want - have)]), pool)):
                res = client.post("/api/v1/appointments/", {
                    "patient": str(patient.id), "doctor": str(doctor.id), "kind": "booked", "date": str(day),
                    "start_time": start, "reason": rng.choice(REASONS),
                }, format="json")
                if res.status_code == 201:
                    made += 1
                else:
                    self.stdout.write(self.style.WARNING(f"{day} {start}: {res.status_code} {res.data}"))
            day += timedelta(days=1)
        self.stdout.write(self.style.SUCCESS(f"{made} sample appointments booked until {last:%d-%m-%Y}."))
