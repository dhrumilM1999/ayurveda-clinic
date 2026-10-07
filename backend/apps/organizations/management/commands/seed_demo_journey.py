"""
Creates about 36 FICTIONAL patients and walks each one through the clinic like real life, using the same API the
screens use, so every rule (patient ID, token, invoice number, stock, consent) is applied:

  reception registers, books / checks in -> doctor examines, prescribes, completes -> reception bills and takes
  payment -> pharmacy dispenses.

13 patients are "today" (booked, waiting, with the doctor, waiting for the bill, waiting at the pharmacy, finished),
the other 23 were seen in the last two months (their dates are moved back so reports and history look real).
The people and cases are in demo_journey_data.py. Safe to run again (patients with the same mobile are skipped).

  docker compose exec backend python manage.py seed_demo_journey
"""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.models import MasterValue
from apps.medicines.models import Medicine
from apps.organizations.models import Organization

from .demo_journey_data import CASES, PATIENTS


class Api:
    """One logged-in person (receptionist, doctor ...) calling the API."""

    def __init__(self, user, branch):
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.extra = {"HTTP_X_BRANCH_ID": str(branch.id), "HTTP_HOST": "localhost"}

    def call(self, method, url, data=None, ok=(200, 201)):
        response = getattr(self.client, method)(url, data, format="json", **self.extra)
        if response.status_code not in ok:
            body = getattr(response, "data", None) or response.content[:300]
            raise CommandError(f"{method.upper()} {url} -> {response.status_code}: {body}")
        return getattr(response, "data", None)

    def get(self, url, **params):
        response = self.client.get(url, params, **self.extra)
        if response.status_code != 200:
            raise CommandError(f"GET {url} -> {response.status_code}: {getattr(response, 'data', response.content[:300])}")
        return response.data

    def rows(self, url, **params):
        """A list screen's rows (the API gives either a plain list or a page with "results")."""
        data = self.get(url, **params)
        return data if isinstance(data, list) else data.get("results", [])

    def post(self, url, data=None, ok=(200, 201)):
        return self.call("post", url, data or {}, ok)

    def patch(self, url, data):
        return self.call("patch", url, data)


def money(value) -> Decimal:
    return Decimal(str(value))


class Command(BaseCommand):
    help = "Create about 36 fictional patients and walk them through the clinic (register, check-up, bill, pharmacy)."

    def add_arguments(self, parser):
        parser.add_argument("--only", type=int, default=0, help="only the first N patients (for a quick test)")

    # ------------------------------------------------------------------ helpers
    def master_id(self, category, code):
        return str(MasterValue.objects.get(organization=self.org, category=category, code=code).id)

    def master_label(self, category, code):
        value = MasterValue.objects.filter(organization=self.org, category=category, code=code).first()
        return value.label if value else code

    def handle(self, *args, **options):
        self.org = Organization.objects.filter(is_deleted=False).order_by("created_at").first()
        if self.org is None:
            raise CommandError("No clinic yet. Run seed_demo first.")
        self.branch = self.org.main_branch()
        users = {u.username: u for u in User.objects.filter(organization=self.org)}
        for needed in ("admin", "reception1", "doctor1", "pharmacist1"):
            if needed not in users:
                raise CommandError(f"The sample user {needed} is missing. Run seed_demo first.")
        self.desk = Api(users["reception1"], self.branch)
        self.docs = [Api(users["doctor1"], self.branch)]
        self.doctor_users = [users["doctor1"]]
        self.pharmacy = Api(users["pharmacist1"], self.branch)
        self.admin = Api(users["admin"], self.branch)
        self.today = timezone.localdate()
        self.rng = random.Random(2026)
        self.services = {s["name"]: s for s in self.admin.rows("/api/v1/services/", page_size=100)}
        self.stock_up()
        self.stock_up_homeopathy()
        specs = PATIENTS[: options["only"]] if options["only"] else PATIENTS
        made = 0
        for index, spec in enumerate(specs):
            if self.walk(index, spec):
                made += 1
                self.stdout.write(f"  {spec[0]} {spec[2]:<10} {spec[8]}")
        self.stdout.write(self.style.SUCCESS(f"Done: {made} new fictional patients walked through the clinic."))

    # ------------------------------------------------------------------ pharmacy stock
    def stock_up(self):
        """Buy stock of every medicine the demo cases use (once), so the pharmacy can dispense."""
        if any(p.get("invoice_no") == "DEMO-STOCK-1" for p in self.admin.rows("/api/v1/purchases/", page_size=100)):
            return
        names = sorted({rx[0] for case in CASES.values() for rx in case["rx"]})
        medicines = {m.name: m for m in Medicine.objects.filter(organization=self.org, name__in=names)}
        missing = [n for n in names if n not in medicines]
        if missing:
            raise CommandError(f"These medicines are not in the list yet: {missing}. Run add_medicine_catalog first.")
        supplier = self.admin.post("/api/v1/suppliers/", {
            "name": "Shree Ayur Distributors (demo)", "contact_person": "Demo Supplier", "phone": "9999900100",
            "gstin": "24AAAAA0000A1Z5", "address": "Ring Road, Surat", "state": "Gujarat", "payment_terms_days": 30})
        items = []
        for number, name in enumerate(names, start=1):
            m = medicines[name]
            mrp = money(m.mrp or 100)
            items.append({
                "medicine": str(m.id), "batch_no": f"DM{number:03d}A", "mfg_date": str(self.today - timedelta(days=90)),
                "expiry_date": str(self.today + timedelta(days=900)), "quantity": 40, "free_quantity": 0,
                "purchase_rate": str((mrp * Decimal("0.62")).quantize(Decimal("0.01"))), "gst_rate": 12,
                "mrp": str(mrp), "selling_price": str(mrp)})
        self.admin.post("/api/v1/purchases/", {"supplier": supplier["id"], "invoice_no": "DEMO-STOCK-1",
                                                "invoice_date": str(self.today - timedelta(days=30)), "items": items})
        self.stdout.write(f"Stock bought: {len(items)} medicines x 40 packs")

    def stock_up_homeopathy(self):
        """Stock for the most used homeopathy remedies (once), so the pharmacy can give them."""
        if any(p.get("invoice_no") == "DEMO-STOCK-2" for p in self.admin.rows("/api/v1/purchases/", page_size=100)):
            return
        from apps.medicines.homeopathy_catalog import COMMON

        wanted = [f"{name} {potency}" for name in sorted(COMMON) for potency in ("30C", "200C")] + [
            "Arnica Montana Q", "Calendula Officinalis Q", "Arnica Ointment", "Calendula Ointment",
            "Natrum Muriaticum 6X (biochemic)", "Calcarea Phosphorica 6X (biochemic)", "Ferrum Phosphoricum 6X (biochemic)"]
        medicines = list(Medicine.objects.filter(organization=self.org, name__in=wanted))
        supplier = next((s for s in self.admin.rows("/api/v1/suppliers/", page_size=50) if "Ayur Distributors" in s["name"]), None)
        items = []
        for number, m in enumerate(medicines, start=1):
            mrp = money(m.mrp or 80)
            items.append({
                "medicine": str(m.id), "batch_no": f"HM{number:03d}B", "mfg_date": str(self.today - timedelta(days=60)),
                "expiry_date": str(self.today + timedelta(days=1000)), "quantity": 20, "free_quantity": 0,
                "purchase_rate": str((mrp * Decimal("0.6")).quantize(Decimal("0.01"))), "gst_rate": 12,
                "mrp": str(mrp), "selling_price": str(mrp)})
        self.admin.post("/api/v1/purchases/", {"supplier": supplier["id"] if supplier else None, "invoice_no": "DEMO-STOCK-2",
                                                "invoice_date": str(self.today - timedelta(days=20)), "items": items})
        self.stdout.write(f"Homeopathy stock bought: {len(items)} medicines x 20")

    # ------------------------------------------------------------------ one patient
    def walk(self, index, spec):
        first, father, last, gender, age, mobile, area, case_key, when, conditions, allergy = spec
        from apps.patients.models import Patient

        existing = Patient.objects.filter(organization=self.org, mobile=mobile).first()
        if existing:  # a patient from an earlier (interrupted) run: only finish the pharmacy step if it is still open
            from apps.prescriptions.models import Prescription

            rx = Prescription.objects.filter(patient=existing, status="final").order_by("-created_at").first()
            if rx and when in ("today_done",) and not rx.dispenses.exists():
                self.dispense(str(rx.id), index)
                return True
            from apps.appointments.models import Appointment

            if when == "today_booked" and not Appointment.objects.filter(patient=existing).exists():
                doctor = self.doctor_users[0]
                self.book({"id": str(existing.id)}, doctor, when, index, CASES[case_key]["diagnosis"][1].split(" (")[0])
                return True
            return False
        case = CASES[case_key]
        doctor_api, doctor = self.docs[0], self.doctor_users[0]
        title = "master" if age < 12 else "baby" if age < 3 else ("mr" if gender == "male" else "mrs")
        payload = {
            "first_name": first, "middle_name": father, "last_name": last, "gender": gender, "age": age, "mobile": mobile,
            "city": "Surat", "state": "Gujarat", "address_line2": area, "preferred_language": "gu",
            "title": self.master_id("title", title), "referral_source": self.master_id(
                "referral_source", ["walk_in", "family_friend", "existing_patient", "google", "doctor"][index % 5]),
            "conditions": [{"condition": self.master_id("medical_condition", c)} for c in conditions],
            "allergies": [{"allergy_type": self.master_id("allergy_type", allergy[0]), "allergen": allergy[1],
                           "severity": "moderate"}] if allergy else [],
        }
        if age < 18:
            payload["guardian_name"] = f"{father} {last}"
        patient = self.desk.post("/api/v1/patients/", payload)
        for code in ("treatment", "communication"):
            from apps.patients.models import ConsentPurpose

            purpose = ConsentPurpose.objects.get(organization=self.org, code=code)
            self.desk.post("/api/v1/patient-consents/", {"patient": patient["id"], "purpose": str(purpose.id), "granted": True,
                                                         "method": "signed_form", "language": "gu"})

        reason = case["diagnosis"][1].split(" (")[0] + (" - follow-up" if when.startswith("past") and index % 3 == 0 else "")
        appointment = self.book(patient, doctor, when, index, reason)
        if when == "today_booked":
            return True
        if appointment["status"] == "booked":  # walk-ins are already waiting
            self.desk.post(f"/api/v1/appointments/{appointment['id']}/check-in/")
        if when == "today_waiting":
            return True

        # ---- doctor
        visit = doctor_api.post("/api/v1/visits/", {"appointment": appointment["id"]})
        sys_, dia, pulse, weight, height = case["vitals"]
        sys_ += self.rng.randint(-4, 6)
        pulse += self.rng.randint(-4, 6)
        weight += self.rng.randint(-3, 5)
        doctor_api.post("/api/v1/patient-vitals/", {
            "patient": patient["id"], "bp_systolic": sys_, "bp_diastolic": dia + self.rng.randint(-2, 3), "pulse": pulse,
            "weight_kg": weight, "height_cm": height, "temperature_f": "98.4", "spo2": 98})
        doctor_api.patch(f"/api/v1/visits/{visit['id']}/", {
            "complaints": [{"code": c[0], "label": c[1], "duration": c[2], "duration_unit": c[3], "severity": c[4]}
                           for c in case["complaints"]],
            "history_notes": case["history"],
        })
        if when == "today_doctor":
            return True
        follow_up = self.today + timedelta(days=case["follow_up"])
        doctor_api.patch(f"/api/v1/visits/{visit['id']}/", {
            "diagnoses": [{"label": case["diagnosis"][1], "master": case["diagnosis"][0], "kind": "final"}],
            "advice": [self.master_label("advice", code) for code in case["advice"]],
            "follow_up_date": str(follow_up), "follow_up_notes": "Bring the old prescription and reports",
        })
        medicines = {m.name: m for m in Medicine.objects.filter(organization=self.org, name__in=[r[0] for r in case["rx"]])}
        items = []
        for name, dose, unit, freq, timing, anupana, days, note in case["rx"]:
            items.append({"medicine": str(medicines[name].id), "dose": dose, "dose_unit": self.master_label("dose_unit", unit),
                          "frequency": freq, "timing": self.master_label("medicine_timing", timing),
                          "anupana": self.master_label("anupana", anupana), "duration": days, "duration_unit": "days",
                          "quantity": "1 pack", "instructions": note})
        prescription = doctor_api.post("/api/v1/prescriptions/", {"visit": visit["id"], "items": items,
                                                                   "notes": "Take medicines regularly. Avoid heavy meals at night."})
        doctor_api.post(f"/api/v1/visits/{visit['id']}/complete/")
        if when == "today_billing":
            return True

        # ---- reception: bill and payment
        invoice = self.bill(visit, patient, doctor_api, case, index, full=(index % 7 != 3))
        if when == "today_pharmacy":
            return True

        # ---- pharmacy
        self.dispense(prescription["id"], index)
        if when.startswith("past"):
            self.move_back(patient, appointment, visit, prescription, invoice, int(when.split(":")[1]), index)
        return True

    # ------------------------------------------------------------------ steps
    def book(self, patient, doctor, when, index, reason):
        """Today's patients walk in (or hold a booked time); old patients are booked for today and moved back later."""
        data = {"patient": patient["id"], "doctor": str(doctor.id), "date": str(self.today), "reason": reason}
        if when == "today_booked":
            # the next working morning (evening slots may already be over), 15 minutes apart
            day = self.today + timedelta(days=1)
            if day.weekday() == 6:
                day += timedelta(days=1)
            start = datetime.combine(day, time(10, 0)) + timedelta(minutes=15 * (index % 6))
            data.update({"kind": "booked", "date": str(day), "start_time": start.strftime("%H:%M")})
        else:
            data["kind"] = "walk_in"
        return self.desk.post("/api/v1/appointments/", data)

    def bill(self, visit, patient, doctor_api, case, index, full):
        suggest = self.desk.get("/api/v1/opd-bills/suggest/", visit=visit["id"])
        fee = money(suggest["consultation"]["fee"])
        lines = [{"kind": "consultation", "description": "OPD consultation", "quantity": 1, "unit_price": str(fee)}]
        service = case.get("service")
        if service:
            match = next((s for name, s in self.services.items() if name.startswith(service)), None)
            if match:
                lines.append({"kind": "service", "service": match["id"], "description": match["name"], "quantity": 1,
                              "unit_price": str(match["price"])})
        total = sum(money(line["unit_price"]) * money(line["quantity"]) for line in lines)
        mode = ["cash", "upi", "cash", "card", "upi"][index % 5]
        paid = total if full else (total / 2).quantize(Decimal("1"))
        return self.desk.post("/api/v1/opd-bills/charge/", {
            "visit": visit["id"], "lines": lines, "payment": {"mode": mode, "amount": str(paid)}})

    def dispense(self, prescription_id, index):
        detail = self.pharmacy.get(f"/api/v1/dispensing/{prescription_id}/")
        items = []
        for line in detail["lines"]:
            batches = [b for b in line["batches"] if money(b.get("quantity_available", b.get("quantity", 1))) > 0] or line["batches"]
            items.append({"prescription_item": line["id"], "batch": batches[0]["id"], "quantity": 1})
        sold = self.pharmacy.post(f"/api/v1/dispensing/{prescription_id}/sell/", {"items": items})
        total = sold.get("total_amount")
        if sold.get("invoice") and total and money(total) > 0:
            mode = ["cash", "upi", "card"][index % 3]
            self.pharmacy.post(f"/api/v1/invoices/{sold['invoice']}/pay/", {"mode": mode, "amount": str(total)})

    def move_back(self, patient, appointment, visit, prescription, invoice, days_ago, index):
        """Make an old patient's records carry the date they were seen (so history, reports and the queue look real)."""
        from apps.appointments.models import Appointment
        from apps.billing.models import Invoice, Payment
        from apps.emr.models import Visit
        from apps.patients.models import Patient, PatientConsent, PatientVital
        from apps.pharmacy.models import Dispense
        from apps.prescriptions.models import Prescription

        day = self.today - timedelta(days=days_ago)
        # skip Sundays (the clinic is closed)
        if day.weekday() == 6:
            day -= timedelta(days=1)
        moment = timezone.make_aware(datetime.combine(day, time(10 + index % 6, (index * 7) % 60)))
        patient_id = patient["id"]
        used = Appointment.objects.filter(branch=self.branch, date=day).count()
        Appointment.objects.filter(pk=appointment["id"]).update(
            date=day, token_number=used + 1, checked_in_at=moment, consultation_started_at=moment + timedelta(minutes=8),
            completed_at=moment + timedelta(minutes=22), created_at=moment - timedelta(hours=2))
        Visit.objects.filter(pk=visit["id"]).update(visit_date=day, completed_at=moment + timedelta(minutes=22),
                                                    created_at=moment + timedelta(minutes=8))
        Patient.objects.filter(pk=patient_id).update(created_at=moment - timedelta(hours=2))
        PatientConsent.objects.filter(patient_id=patient_id).update(created_at=moment - timedelta(hours=2))
        PatientVital.objects.filter(patient_id=patient_id).update(recorded_at=moment + timedelta(minutes=5))
        Prescription.objects.filter(pk=prescription["id"]).update(created_at=moment + timedelta(minutes=20),
                                                                  finalized_at=moment + timedelta(minutes=22))
        invoices = Invoice.objects.filter(patient_id=patient_id)
        invoices.update(invoice_date=day, created_at=moment + timedelta(minutes=25))
        Payment.objects.filter(invoice__in=invoices).update(paid_at=moment + timedelta(minutes=26))
        Dispense.objects.filter(patient_id=patient_id).update(created_at=moment + timedelta(minutes=35))
