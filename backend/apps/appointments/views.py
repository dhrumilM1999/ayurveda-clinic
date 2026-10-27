from datetime import date as date_cls
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import DoctorSchedule
from apps.accounts.services import doctors_in_branch
from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet
from apps.organizations.services import is_feature_enabled

from .models import ACTIVE_STATUSES, Appointment
from .serializers import AppointmentSerializer, CancelSerializer, QueueItemSerializer, RescheduleSerializer
from .services import change_status, doctor_slots, event_for, notify_patient, undo_last_step

SLOT_TAKEN = {"start_time": "This time was just booked by someone else. Please pick another time."}


def parse_day(value, default=None):
    if not value:
        if default is None:
            raise ValidationError({"date": "Please choose a date."})
        return default
    try:
        return date_cls.fromisoformat(value)
    except ValueError:
        raise ValidationError({"date": "Date must look like 2026-10-05."})


class AppointmentViewSet(AuditedModelViewSet):
    """
    Appointments of the current branch.
    Booking, walk-ins, check-in, cancel and reschedule need "appointments.manage";
    lists, slots and the queue need "appointments.view".
    """

    queryset = Appointment.objects.select_related("patient", "doctor", "branch", "organization")
    serializer_class = AppointmentSerializer
    permission_prefix = "appointments"
    branch_scoped = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["date", "doctor", "status", "patient", "kind"]
    ordering_fields = ["date", "start_time", "time_order", "token_number", "created_at"]

    def check_permissions(self, request):
        super().check_permissions(request)
        branch = getattr(request, "branch", None)
        if branch is not None and not is_feature_enabled(branch, "appointments"):
            raise PermissionDenied("Appointments are switched off for this branch (Settings → Modules).")

    def get_queryset(self):
        from django.db.models import Count, IntegerField, OuterRef, Subquery
        from django.db.models.functions import Coalesce, TruncTime

        from apps.emr.models import Visit

        qs = super().get_queryset()
        # previous_visits: check-ups of this patient before the appointment day (new patient = 0, follow-up = more)
        earlier = (Visit.objects.filter(patient=OuterRef("patient"), visit_date__lt=OuterRef("date"), is_deleted=False)
                   .order_by().values("patient").annotate(n=Count("id")).values("n"))
        qs = qs.annotate(previous_visits=Coalesce(Subquery(earlier, output_field=IntegerField()), 0))
        # time_order: a booked appointment sorts by its slot, a walk-in (no slot) by the time it was entered
        qs = qs.annotate(time_order=Coalesce("start_time", TruncTime("created_at", tzinfo=timezone.get_current_timezone())))
        params = self.request.query_params
        if params.get("date_from"):
            qs = qs.filter(date__gte=parse_day(params["date_from"]))
        if params.get("date_to"):
            qs = qs.filter(date__lte=parse_day(params["date_to"]))
        search = params.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(patient__first_name__icontains=search) | Q(patient__last_name__icontains=search)
                | Q(patient__uhid__icontains=search) | Q(patient__mobile__contains=search)
            )
        return qs

    def _response(self, appointment, notification=None, status=http.HTTP_200_OK):
        data = AppointmentSerializer(appointment, context=self.get_serializer_context()).data
        if notification is not None:
            data["notification"] = notification
        return Response(data, status=status)

    # --- Book / walk-in -----------------------------------------------------------
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                self.perform_create(serializer)
                appointment = serializer.instance
                if appointment.kind == "walk_in":
                    # Walk-ins are already here: they get a token straight away.
                    change = change_status(appointment, "check_in", request.user)
                    log_action(request, "update", appointment, changes={"status": change})
        except IntegrityError:
            raise ValidationError(SLOT_TAKEN)
        notification = notify_patient(appointment, "token" if appointment.kind == "walk_in" else "booked")
        return self._response(appointment, notification, status=http.HTTP_201_CREATED)

    # --- Status changes -------------------------------------------------------------
    def _change(self, request, action_name, **extra):
        appointment = self.get_object()
        change = change_status(appointment, action_name, request.user, **extra)
        log_action(request, "update", appointment, changes={"status": change})
        return appointment

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        appointment = self._change(request, "check_in")
        return self._response(appointment, notify_patient(appointment, "token"))

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._response(self._change(request, "start"))

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._response(self._change(request, "complete"))

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        return self._response(self._change(request, "no_show"))

    @action(detail=True, methods=["post"])
    def undo(self, request, pk=None):
        """Go back one step after a wrong click (check-in, start, done, did not come, cancel, a booking just made)."""
        appointment = self.get_object()
        try:
            with transaction.atomic():
                change = undo_last_step(appointment, request.user)
        except IntegrityError:
            raise ValidationError(SLOT_TAKEN)
        log_action(request, "update", appointment, changes={"status": change})
        return self._response(appointment)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = self._change(request, "cancel", cancel_reason=serializer.validated_data.get("reason", ""))
        return self._response(appointment, notify_patient(appointment, "cancelled"))

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status not in ("booked", "no_show"):
            raise ValidationError({"detail": "Only booked appointments (patient not yet arrived) or ones marked 'did not come' can be moved."})
        serializer = RescheduleSerializer(data=request.data, context={"appointment": appointment})
        serializer.is_valid(raise_exception=True)
        new = serializer.validated_data
        before = {"date": str(appointment.date), "start_time": appointment.start_time.strftime("%H:%M")}
        try:
            with transaction.atomic():
                appointment.date = new["date"]
                appointment.start_time = new["start_time"]
                appointment.end_time = new["end_time"]
                appointment.reschedule_count += 1
                appointment.status = "booked"  # a "did not come" appointment becomes a booked one again
                appointment.updated_by = request.user
                appointment.save()
        except IntegrityError:
            raise ValidationError(SLOT_TAKEN)
        after = {"date": str(appointment.date), "start_time": appointment.start_time.strftime("%H:%M")}
        log_action(request, "update", appointment, changes={
            k: {"from": before[k], "to": after[k]} for k in before if before[k] != after[k]
        })
        return self._response(appointment, notify_patient(appointment, "rescheduled"))

    @action(detail=True, methods=["post"])
    def whatsapp(self, request, pk=None):
        """A click-to-chat WhatsApp link with the right message (booking, token, change or cancel)."""
        appointment = self.get_object()
        notification = notify_patient(appointment, event_for(appointment), send_sms_now=False)
        if notification["consent"]:
            log_action(request, "share", appointment, changes={"channel": "whatsapp"})
        return Response(notification)

    # --- Lookups for the booking screen ----------------------------------------------
    @action(detail=False, methods=["get"])
    def doctors(self, request):
        """Doctors of this branch, whether they sit on the chosen day, and how busy they are."""
        day = parse_day(request.query_params.get("date"), timezone.localdate())
        schedules = DoctorSchedule.objects.filter(branch=request.branch, weekday=day.weekday(), is_active=True)
        timings = {}
        for s in schedules.order_by("start_time"):
            timings.setdefault(s.doctor_id, []).append(f"{s.start_time:%H:%M}–{s.end_time:%H:%M}")
        doctors = doctors_in_branch(request.branch).annotate(
            active_count=Count("appointments", filter=Q(
                appointments__branch=request.branch, appointments__date=day,
                appointments__status__in=ACTIVE_STATUSES, appointments__is_deleted=False,
            )),
        ).order_by("full_name")
        return Response([
            {"id": str(d.id), "full_name": d.full_name, "sits": d.id in timings,
             "timings": timings.get(d.id, []), "active_count": d.active_count}
            for d in doctors
        ])

    @action(detail=False, methods=["get"])
    def slots(self, request):
        """Time slots of one doctor on one day: free, booked or past."""
        doctor_id = request.query_params.get("doctor")
        day = parse_day(request.query_params.get("date"))
        doctor = doctors_in_branch(request.branch).filter(pk=doctor_id).first() if doctor_id else None
        if doctor is None:
            raise ValidationError({"doctor": "Please choose a doctor of this branch."})
        return Response({"date": str(day), "doctor": str(doctor.id), "slots": doctor_slots(request.branch, doctor, day)})

    @action(detail=False, methods=["get"])
    def calendar(self, request):
        """
        The calendar: for every day from ?from= to ?to= (at most 62 days) does the doctor sit, how many slots are free /
        booked, and how many patients are booked or walked in. ?doctor= one doctor (default: all doctors of the branch).
        """
        first = parse_day(request.query_params.get("from"), timezone.localdate())
        last = parse_day(request.query_params.get("to"), first + timedelta(days=30))
        if last < first or (last - first).days > 62:
            raise ValidationError({"to": "Choose a period of at most 62 days."})
        doctors = doctors_in_branch(request.branch)
        if request.query_params.get("doctor"):
            doctors = doctors.filter(pk=request.query_params["doctor"])
        doctors = list(doctors)
        counts = {}
        appts = Appointment.objects.filter(branch=request.branch, date__range=(first, last), doctor__in=doctors)             .exclude(status__in=["cancelled"]).values("date", "kind").annotate(n=Count("id"))
        for row in appts:
            entry = counts.setdefault(row["date"], {"booked": 0, "walk_in": 0})
            entry["walk_in" if row["kind"] == "walk_in" else "booked"] += row["n"]
        days = []
        day = first
        while day <= last:
            free = booked_slots = past = 0
            timings = []
            for doctor in doctors:
                for slot in doctor_slots(request.branch, doctor, day):
                    free += slot["status"] == "free"
                    booked_slots += slot["status"] == "booked"
                    past += slot["status"] == "past"
            total = free + booked_slots + past
            entry = counts.get(day, {"booked": 0, "walk_in": 0})
            days.append({"date": str(day), "sits": total > 0, "free": free, "past": past, "slots": total,
                         "booked": entry["booked"], "walk_in": entry["walk_in"]})
            day += timedelta(days=1)
        return Response({"from": str(first), "to": str(last), "days": days})

    @action(detail=False, methods=["get"])
    def queue(self, request):
        """
        The waiting queue per doctor for one day (default today): who is with the doctor now,
        who is waiting (in token order), and how many are booked / done.
        """
        day = parse_day(request.query_params.get("date"), timezone.localdate())
        qs = self.get_queryset().filter(date=day).exclude(status="cancelled")
        doctor_id = request.query_params.get("doctor")
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
        groups = {}
        for appt in qs.order_by("token_number", "start_time", "created_at"):
            group = groups.setdefault(appt.doctor_id, {
                "doctor": str(appt.doctor_id), "doctor_name": appt.doctor.full_name,
                "now": [], "waiting": [], "booked_count": 0, "done_count": 0,
            })
            if appt.status == "in_consultation":
                group["now"].append(appt)
            elif appt.status == "checked_in":
                group["waiting"].append(appt)
            elif appt.status == "booked":
                group["booked_count"] += 1
            elif appt.status == "completed":
                group["done_count"] += 1
        context = self.get_serializer_context()
        result = []
        for group in sorted(groups.values(), key=lambda g: g["doctor_name"]):
            group["now"] = QueueItemSerializer(group["now"], many=True, context=context).data
            group["waiting"] = QueueItemSerializer(group["waiting"], many=True, context=context).data
            result.append(group)
        return Response({
            "date": str(day), "branch_name": request.branch.name,
            "server_time": timezone.localtime().isoformat(), "doctors": result,
        })
