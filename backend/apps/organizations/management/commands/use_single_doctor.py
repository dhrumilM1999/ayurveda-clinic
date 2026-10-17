"""
Keeps ONE doctor in the clinic: "doctor1" becomes Dr. Grishm Shingala, and everything the other doctors have
(appointments, check-ups, prescriptions, bills, certificates) is moved to him. The other doctors are switched off
(not erased: records are never deleted). Safe to run again.

  docker compose exec backend python manage.py use_single_doctor
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.accounts.models import DoctorSchedule, User
from apps.appointments.models import Appointment, TokenSequence
from apps.billing.models import ConsultationFee, Invoice
from apps.documents.models import Certificate, IssuedDocument
from apps.emr.models import Visit
from apps.organizations.models import Organization
from apps.prescriptions.models import Prescription

NAME = "Dr. Grishm Shingala"


class Command(BaseCommand):
    help = "Keep one doctor (Dr. Grishm Shingala); move the other doctors' records to him and switch them off."

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.IS_PRODUCTION and not settings.DEMO_MODE:
            raise CommandError("Refusing to run: this command creates demo data with a well-known password and must "
                               "never run on the live server (DEMO_MODE is not true).")
        org = Organization.objects.filter(is_deleted=False).order_by("created_at").first()
        keep = User.objects.filter(organization=org, username="doctor1", is_deleted=False).first()
        if keep is None:
            raise CommandError("The sample doctor 'doctor1' is missing.")
        keep.full_name = NAME
        keep.qualification = keep.qualification if "BAMS" in keep.qualification and "GAU" in keep.qualification else "BAMS (GAU) Ayurved Physician & Diet Consultant"
        keep.registration_number = keep.registration_number or "GB-26175"
        keep.is_doctor = True
        keep.save()
        now = timezone.now()
        for other in User.objects.filter(organization=org, is_doctor=True, is_deleted=False).exclude(pk=keep.pk):
            moved = 0
            # 1) appointments: give them tokens that do not clash with the kept doctor's tokens of the same day
            days = Appointment.objects.filter(doctor=other).values_list("branch_id", "date").distinct()
            for branch_id, day in days:
                top = Appointment.objects.filter(doctor=keep, branch_id=branch_id, date=day).aggregate(m=Max("token_number"))["m"] or 0
                for appointment in Appointment.objects.filter(doctor=other, branch_id=branch_id, date=day).order_by("token_number", "created_at"):
                    update = {"doctor": keep}
                    if appointment.token_number is not None:
                        top += 1
                        update["token_number"] = top
                    # a booked time that the kept doctor already has: move to the next free quarter hour
                    start = appointment.start_time
                    if start is not None:
                        from datetime import datetime, timedelta
                        taken = set(Appointment.objects.filter(doctor=keep, date=day, is_deleted=False).values_list("start_time", flat=True))
                        while start in taken:
                            start = (datetime.combine(day, start) + timedelta(minutes=15)).time()
                        update["start_time"] = start
                    Appointment.objects.filter(pk=appointment.pk).update(**update)
                    moved += 1
                seq, _ = TokenSequence.objects.get_or_create(branch_id=branch_id, doctor=keep, date=day)
                seq.last_number = max(seq.last_number, top)
                seq.save()
            TokenSequence.objects.filter(doctor=other).delete()  # counters only, not records
            # 2) other records simply change doctor
            for model in (Visit, Prescription, Invoice, Certificate, IssuedDocument):
                moved += model.objects.filter(doctor=other).update(doctor=keep)
            # 3) settings of the old doctor are switched off
            ConsultationFee.objects.filter(doctor=other).update(is_deleted=True, deleted_at=now)
            DoctorSchedule.objects.filter(doctor=other).update(is_deleted=True, deleted_at=now)
            other.is_active = False
            other.is_doctor = False
            other.is_deleted = True
            other.deleted_at = now
            other.save()
            self.stdout.write(f"{other.full_name}: {moved} records moved to {NAME}; switched off")
        # Timings as on the clinic's letterhead: Monday to Saturday, morning 9-1 and evening 5-8 (closed on Sunday)
        from datetime import time

        main = org.main_branch()
        if main:
            DoctorSchedule.objects.filter(doctor=keep, branch=main).update(is_deleted=True, deleted_at=now)
            for weekday in range(6):
                for start, end in ((time(9, 0), time(13, 0)), (time(17, 0), time(20, 0))):
                    DoctorSchedule.objects.create(organization=org, branch=main, doctor=keep, weekday=weekday,
                                                  start_time=start, end_time=end, slot_minutes=15)
        self.stdout.write(self.style.SUCCESS(f"Done. The clinic's only doctor: {NAME}"))
