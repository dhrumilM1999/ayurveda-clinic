from datetime import date as date_cls

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
from .services import change_status, doctor_slots, event_for, notify_patient

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
    ordering_fields = ["date", "start_time", "token_number", "created_at"]

    def check_permissions(self, request):
        super().check_permissions(request)
        branch = getattr(request, "branch", None)
        if branch is not None and not is_feature_enabled(branch, "appointments"):
            raise PermissionDenied("Appointments are switched off for this branch (Settings → Modules).")

    def get_queryset(self):
        qs = super().get_queryset()
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
    def cancel(self, request, pk=None):
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = self._change(request, "cancel", cancel_reason=serializer.validated_data.get("reason", ""))
        return self._response(appointment, notify_patient(appointment, "cancelled"))

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status != "booked":
            raise ValidationError({"detail": "Only booked appointments (patient not yet arrived) can be moved."})
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
