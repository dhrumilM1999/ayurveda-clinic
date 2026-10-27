"""
A practice "clinic day" robot, for testing only. At the time of each of today's appointments it does what the real
people do - through the SAME screens' API, not by touching the database:

    front desk  : check the patient in, bill the consultation fee and take the money
    doctor      : open the check-up, write the complaint and diagnosis, write a prescription from the medicines
                  that are on the shelf (sometimes one that is not, so the "needed" list is tested), complete it
    pharmacist  : give the medicines (stock goes down), take the payment for the medicines

    python manage.py run_demo_doctor_bot            # stays running, looks every 30 seconds (Ctrl+C to stop)
    python manage.py run_demo_doctor_bot --once     # do everything that is due now, then stop
    python manage.py run_demo_doctor_bot --all-now  # pretend it is the end of the day: do ALL of today's patients now

Only when DEMO_MODE=true (never on a real clinic). Uses fake patients only. Stock alerts then show up in the app
(Pharmacy -> Stock) and the "Send stock alert on WhatsApp" button gives the message.
"""
import random
import time
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.organizations.models import Organization
from apps.pharmacy.models import StockBatch

API = "/api/v1/"

# complaint -> (diagnosis, advice) - made-up, only for practice data
CASES = {
    "knee": ("Sandhivata", "Warm water, avoid cold food"),
    "back": ("Kati Shoola", "Light exercise, avoid sitting long"),
    "acid": ("Amlapitta", "Avoid spicy food"),
    "gas": ("Adhmana", "Eat on time"),
    "constipation": ("Vibandha", "Warm water in the morning"),
    "skin": ("Kitibha", "Avoid oily food"),
    "sugar": ("Madhumeha", "Walk 30 minutes daily"),
    "thyroid": ("Galaganda", "Regular medicines"),
    "migraine": ("Ardhavabhedaka", "Sleep on time"),
    "hair": ("Khalitya", "Oil massage"),
    "cold": ("Pratishyaya", "Steam, warm drinks"),
    "sleep": ("Anidra", "No screens at night"),
    "weight": ("Sthaulya", "Walk daily, light dinner"),
    "pile": ("Arsha", "Fibre-rich food"),
    "period": ("Artava Vikara", "Rest, regular food"),
    "neck": ("Manya Stambha", "Neck exercises"),
}
FREQUENCIES = ["1-0-1", "1-1-1", "0-0-1", "1-0-0"]


class Command(BaseCommand):
    help = "Practice robot: sees today's patients at their appointment time (DEMO_MODE only)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Do what is due now and stop.")
        parser.add_argument("--all-now", action="store_true", help="Do all of today's patients now, whatever the time.")
        parser.add_argument("--every", type=int, default=30, help="Seconds between looks (default 30).")

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError("Refusing: DEMO_MODE is not true. This robot is only for practice data.")
        org = Organization.objects.order_by("created_at").first()
        self.branch = org.main_branch() if org else None
        users = {u.username: u for u in User.objects.filter(organization=org)}
        try:
            self.desk, self.dr, self.pharm = (self._client(users[n]) for n in ("reception1", "doctor1", "pharmacist1"))
        except KeyError as missing:
            raise CommandError(f"Run seed_demo first: user {missing} is missing.")
        self.doctor = users["doctor1"]
        self.rng = random.Random()
        self.done = set()
        self.stdout.write("Practice robot started. Ctrl+C to stop.")
        while True:
            self.round(everything=options["all_now"])
            if options["once"] or options["all_now"]:
                break
            time.sleep(options["every"])

    def _client(self, user):
        client = APIClient(HTTP_HOST="localhost")
        client.force_authenticate(user)
        client.credentials(HTTP_X_BRANCH_ID=str(self.branch.id))
        return client

    def round(self, everything=False):
        now = timezone.localtime()
        due = (Appointment.objects.filter(branch=self.branch, date=now.date(), doctor=self.doctor)
               .exclude(status__in=["cancelled", "no_show", "completed", "in_consultation"]).order_by("start_time", "created_at"))
        for appt in due:
            if appt.id in self.done:
                continue
            if not everything and appt.start_time and appt.start_time > now.time():
                continue
            self.done.add(appt.id)
            try:
                self.see(appt)
            except Exception as error:  # a problem with one patient must not stop the day
                self.stdout.write(self.style.ERROR(f"{appt.patient.full_name}: {error}"))

    # ------------------------------------------------------------------ one patient
    def see(self, appt):
        name = appt.patient.full_name
        check = self.desk.post(f"{API}appointments/{appt.id}/check-in/")
        self._ok(check, "check-in")
        suggest = self.desk.get(API + "opd-bills/suggest/", {"appointment": str(appt.id)})
        self._ok(suggest, "fee")
        fee = Decimal(str(suggest.data["consultation"]["fee"]))
        if fee > 0:
            mode = self.rng.choice(["cash", "upi", "card"])
            self._ok(self.desk.post(API + "opd-bills/charge/", {"appointment": str(appt.id), "lines": [{
                "kind": "consultation", "description": suggest.data["consultation"]["description"],
                "unit_price": str(fee)}], "payment": {"mode": mode, "amount": str(fee)}}, format="json"), "fee bill")

        visit = self.dr.post(API + "visits/", {"appointment": str(appt.id)}, format="json")
        self._ok(visit, "open check-up")
        vid = visit.data["id"]
        reason = appt.reason or "General check-up"
        diagnosis, advice = next((v for k, v in CASES.items() if k in reason.lower()), ("Vata vikara", "Rest and light food"))
        self._ok(self.dr.patch(f"{API}visits/{vid}/", {
            "complaints": [{"label": reason, "duration": self.rng.randint(1, 12), "duration_unit": self.rng.choice(["days", "weeks", "months"])}],
            "diagnoses": [{"label": diagnosis, "kind": "final"}], "advice": [advice]}, format="json"), "notes")

        on_shelf = self.medicines_on_shelf()
        picks = self.rng.sample(on_shelf, k=min(len(on_shelf), self.rng.randint(1, 3)))
        items = [self.line(m) for m in picks]
        rx_id = None
        if items:
            rx = self.dr.post(API + "prescriptions/", {"visit": vid, "items": items}, format="json")
            self._ok(rx, "prescription")
            rx_id = rx.data["id"]
        self._ok(self.dr.post(f"{API}visits/{vid}/complete/"), "complete check-up")
        given = self.give(rx_id) if rx_id else "no medicines"
        self.stdout.write(f"{timezone.localtime():%H:%M} {name}: {reason} -> {diagnosis}; {given}")

    def medicines_on_shelf(self):
        """Medicines that have usable stock now (not expired), without the Schedule E1 ones (they need extra care)."""
        today = date.today()
        batches = (StockBatch.objects.filter(branch=self.branch, quantity__gt=0, medicine__schedule_e1=False)
                   .exclude(expiry_date__lt=today).values_list("medicine_id", flat=True).distinct())
        return list(batches)

    def line(self, medicine_id):
        return {"medicine": str(medicine_id), "dose": "3", "dose_unit": "gram", "frequency": self.rng.choice(FREQUENCIES),
                "timing": "After food", "anupana": "Warm water", "duration": self.rng.choice([7, 10, 15, 30]), "duration_unit": "days"}

    def give(self, rx_id):
        detail = self.pharm.get(f"{API}dispensing/{rx_id}/")
        self._ok(detail, "pharmacy")
        lines, missing = [], 0
        for line in detail.data["lines"]:
            if not line["batches"]:
                missing += 1
                continue
            batch = line["batches"][0]
            packs = int(Decimal(str(line.get("suggested_packs") or 1)))
            packs = max(1, min(packs, int(Decimal(str(batch["quantity"])))))
            lines.append({"prescription_item": line["id"], "batch": batch["id"], "quantity": str(packs)})
        if not lines:
            return f"nothing in stock ({missing} medicines)"
        sold = self.pharm.post(f"{API}dispensing/{rx_id}/sell/", {"items": lines}, format="json")
        self._ok(sold, "give medicines")
        note = f"{len(lines)} medicines given"
        if sold.data.get("invoice"):
            inv = self.pharm.get(f"{API}invoices/{sold.data['invoice']}/")
            due = Decimal(str(inv.data["total_amount"])) - Decimal(str(inv.data["credited_amount"])) - Decimal(str(inv.data["paid_amount"]))
            if due > 0:
                self._ok(self.pharm.post(f"{API}invoices/{sold.data['invoice']}/pay/", {
                    "mode": self.rng.choice(["cash", "upi"]), "amount": str(due)}, format="json"), "pay medicines")
        return note + (f", {missing} out of stock" if missing else "")

    @staticmethod
    def _ok(response, step):
        if response.status_code >= 300:
            raise RuntimeError(f"{step} failed ({response.status_code}): {getattr(response, 'data', '')}")
