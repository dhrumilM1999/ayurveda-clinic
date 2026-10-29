from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet
from apps.organizations.models import Room
from apps.organizations.services import is_feature_enabled

from .models import TherapyPlan, TherapyPlanItem, TherapySession, TherapyType
from .serializers import ScheduleSerializer, SessionRescheduleSerializer, TherapyPlanSerializer, TherapySessionSerializer, TherapyTypeSerializer
from .services import bill_finished_session, session_reminder, check_free, end_for, load_sample_therapies, refresh_plan_status, therapists_in_branch, undo_last_step

FEATURE = "panchakarma"


class ModuleSwitch:
    """Every therapy screen needs the "Panchakarma and therapy" module switched on for the branch."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        branch = getattr(request, "branch", None)
        if branch is not None and not is_feature_enabled(branch, FEATURE):
            raise PermissionDenied("Panchakarma and therapy is switched off for this branch (Settings, Modules).")


class TherapyTypeViewSet(ModuleSwitch, AuditedModelViewSet):
    """The clinic's list of therapies. GET /therapies/  POST /therapies/load-sample/ adds the starting list."""

    queryset = TherapyType.objects.select_related("service")
    serializer_class = TherapyTypeSerializer
    permission_prefix = "therapy"
    branch_required = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["stage", "is_active"]
    search_fields = ["name", "name_gu", "name_hi"]
    required_permissions = {"load_sample": "therapy.manage"}
    pagination_class = None

    @action(detail=False, methods=["post"], url_path="load-sample")
    def load_sample(self, request):
        added = load_sample_therapies(request.user.organization)
        return Response({"added": added})


class TherapyPlanViewSet(ModuleSwitch, AuditedModelViewSet):
    """
    A patient's therapy plan. GET /therapy-plans/?patient=&status=   POST creates it with its `items`.
    POST /therapy-plans/<id>/schedule/ books sessions of one item.   POST /therapy-plans/<id>/cancel/
    """

    queryset = TherapyPlan.objects.select_related("patient", "doctor").prefetch_related("items__therapy__service")
    serializer_class = TherapyPlanSerializer
    permission_prefix = "therapy"
    branch_scoped = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["patient", "status", "doctor"]
    search_fields = ["title", "patient__first_name", "patient__last_name", "patient__uhid", "patient__mobile"]
    required_permissions = {"schedule": "therapy.manage", "cancel": "therapy.manage"}

    def perform_create(self, serializer):
        if serializer.validated_data["patient"].is_deleted:
            raise ValidationError({"patient": "Patient not found."})
        serializer.validated_data.setdefault("doctor", self.request.user if self.request.user.is_doctor else None)
        super().perform_create(serializer)

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        plan = self.get_object()
        data = ScheduleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        if plan.status in ("completed", "cancelled"):
            raise ValidationError({"detail": "This plan is closed."})
        item = TherapyPlanItem.objects.filter(plan=plan, pk=v["item"]).select_related("therapy").first()
        if item is None:
            raise ValidationError({"item": "Therapy not found in this plan."})
        org = request.user.organization_id
        therapist = None
        if v.get("therapist"):
            therapist = next((u for u in therapists_in_branch(request.branch) if u.id == v["therapist"]), None)
            if therapist is None:
                raise ValidationError({"therapist": "This person cannot be booked for therapy in this branch."})
        room = None
        if v.get("room"):
            room = Room.objects.filter(pk=v["room"], branch=request.branch, organization_id=org, is_active=True).first()
            if room is None:
                raise ValidationError({"room": "Room not found in this branch."})
        start = v["start_time"]
        end = v.get("end_time") or end_for(start, item.therapy.duration_minutes)
        dates = sorted(set(v["dates"]))
        booked = item.sessions.exclude(status="cancelled").count()
        if booked + len(dates) > item.sessions_planned:
            raise ValidationError({"dates": f"Only {max(item.sessions_planned - booked, 0)} more session(s) are planned for "
                                            f"{item.therapy.name}. Raise the number in the plan first."})
        with transaction.atomic():
            created = []
            for day in dates:
                check_free(request.branch, day, start, end, therapist, room)
                created.append(TherapySession.objects.create(
                    organization_id=org, branch=request.branch, plan=plan, item=item, patient=plan.patient,
                    therapy=item.therapy, therapist=therapist, room=room, date=day, start_time=start, end_time=end,
                    created_by=request.user, updated_by=request.user))
            refresh_plan_status(plan)
        log_action(request, "create", plan, changes={"sessions_booked": [str(d) for d in dates], "therapy": item.therapy.name})
        ctx = self.get_serializer_context()
        return Response(TherapySessionSerializer(created, many=True, context=ctx).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        plan = self.get_object()
        with transaction.atomic():
            plan.sessions.filter(status__in=["scheduled"]).update(status="cancelled", updated_by=request.user)
            plan.status = "cancelled"
            plan.updated_by = request.user
            plan.save(update_fields=["status", "updated_by", "updated_at"])
        log_action(request, "update", plan, changes={"status": {"to": "cancelled"}})
        return Response(self.get_serializer(plan).data)


class TherapySessionViewSet(ModuleSwitch, AuditedModelViewSet):
    """
    The booked sessions. GET /therapy-sessions/?date=2026-10-15&therapist=&room=&status=&plan=&patient=
    PATCH to move or edit; POST .../start/, .../complete/ (oil, quantity, response), .../missed/, .../cancel/.
    GET /therapy-sessions/options/ gives the therapists and rooms that can be booked.
    """

    queryset = TherapySession.objects.select_related("patient", "therapy", "therapist", "room", "plan", "item")
    serializer_class = TherapySessionSerializer
    permission_prefix = "therapy"
    branch_scoped = True
    http_method_names = ["get", "patch", "post", "head", "options"]
    filterset_fields = {"date": ["exact", "gte", "lte"], "therapist": ["exact"], "room": ["exact"], "status": ["exact", "in"],
                        "plan": ["exact"], "patient": ["exact"]}
    ordering_fields = ["date", "start_time"]
    pagination_class = None
    required_permissions = {"start": "therapy.manage", "complete": "therapy.manage", "missed": "therapy.manage",
                            "cancel": "therapy.manage", "reschedule": "therapy.manage", "undo": "therapy.manage", "options": "therapy.view",
                            "whatsapp": "therapy.manage"}

    def create(self, request, *args, **kwargs):
        raise ValidationError({"detail": "Book sessions from the plan (POST /therapy-plans/<id>/schedule/)."})

    def perform_update(self, serializer):
        super().perform_update(serializer)
        refresh_plan_status(serializer.instance.plan)

    def _set(self, request, status, **extra):
        session = self.get_object()
        if session.status in ("done", "cancelled"):
            raise ValidationError({"detail": f"This session is already {session.get_status_display().lower()}."})
        if status in ("in_progress", "done") and session.date > timezone.localdate():
            raise ValidationError({"detail": "This session is on a later day. It can be started on that day."})
        if status in ("scheduled", "in_progress", "done"):
            check_free(request.branch, session.date, session.start_time, session.end_time, session.therapist, session.room,
                       exclude_id=session.pk)
        before = session.status
        session.status = status
        for key, value in extra.items():
            setattr(session, key, value)
        session.updated_by = request.user
        session.save()
        refresh_plan_status(session.plan)
        if status == "done":
            bill_finished_session(session, request.user)
        log_action(request, "update", session, changes={"status": {"from": before, "to": status}})
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._set(request, "in_progress", started_at=timezone.now())

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        session = self.get_object()
        fields = {k: request.data[k] for k in ("material_used", "quantity_ml", "patient_response", "notes") if k in request.data}
        if fields.get("quantity_ml") in ("", None):
            fields.pop("quantity_ml", None)
        elif not str(fields["quantity_ml"]).isdigit():
            raise ValidationError({"quantity_ml": "Enter the quantity in ml as a number."})
        if not session.started_at:
            fields["started_at"] = timezone.now()
        return self._set(request, "done", completed_at=timezone.now(), **fields)

    @action(detail=True, methods=["post"])
    def whatsapp(self, request, pk=None):
        """A click-to-chat WhatsApp reminder for this session (Additional settings -> WhatsApp reminders)."""
        if not is_feature_enabled(request.branch, "whatsapp_reminders"):
            raise PermissionDenied("WhatsApp reminders are switched off. Switch them on in Additional settings.")
        session = self.get_object()
        therapy = session.therapy
        language = session.patient.preferred_language
        name = (getattr(therapy, f"name_{language}", "") if language in ("gu", "hi") else "") or therapy.name
        notification = session_reminder(session, name)
        if notification["consent"]:
            log_action(request, "share", session, changes={"channel": "whatsapp"})
        return Response(notification)

    @action(detail=True, methods=["post"])
    def missed(self, request, pk=None):
        return self._set(request, "missed")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._set(request, "cancelled")

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        """Move a session that was not done (still booked, or marked 'did not come') to a new day and time."""
        session = self.get_object()
        if session.status not in ("scheduled", "missed"):
            raise ValidationError({"detail": f"This session is {session.get_status_display().lower()} and cannot be moved."})
        if session.plan.status in ("cancelled", "completed"):
            raise ValidationError({"detail": "This therapy plan is closed."})
        serializer = SessionRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new = serializer.validated_data
        if new["date"] < timezone.localdate():
            raise ValidationError({"date": "The date has already passed."})
        duration = (session.end_time.hour * 60 + session.end_time.minute) - (session.start_time.hour * 60 + session.start_time.minute)
        end = end_for(new["start_time"], max(duration, 5))
        therapist, room = session.therapist, session.room
        if "therapist" in new:
            therapist = None
            if new["therapist"]:
                therapist = next((u for u in therapists_in_branch(request.branch) if u.id == new["therapist"]), None)
                if therapist is None:
                    raise ValidationError({"therapist": "This person cannot be booked for therapy in this branch."})
        if "room" in new:
            room = None
            if new["room"]:
                room = Room.objects.filter(pk=new["room"], branch=request.branch, organization_id=request.user.organization_id,
                                           is_active=True).first()
                if room is None:
                    raise ValidationError({"room": "Room not found in this branch."})
        check_free(request.branch, new["date"], new["start_time"], end, therapist, room, exclude_id=session.pk)
        before = {"date": str(session.date), "start_time": session.start_time.strftime("%H:%M"), "status": session.status}
        session.date, session.start_time, session.end_time = new["date"], new["start_time"], end
        session.therapist, session.room, session.status = therapist, room, "scheduled"
        session.updated_by = request.user
        session.save()
        refresh_plan_status(session.plan)
        log_action(request, "update", session, changes={"rescheduled": {"from": before, "to": {
            "date": str(session.date), "start_time": session.start_time.strftime("%H:%M"), "status": "scheduled"}}})
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def undo(self, request, pk=None):
        session = self.get_object()
        change = undo_last_step(session, request.user)
        log_action(request, "update", session, changes={"status": change})
        return Response(self.get_serializer(session).data)

    @action(detail=False, methods=["get"])
    def options(self, request):
        rooms = Room.objects.filter(branch=request.branch, organization_id=request.user.organization_id, is_active=True)
        return Response({
            "therapists": [{"id": str(u.id), "name": u.full_name} for u in therapists_in_branch(request.branch)],
            "rooms": [{"id": str(r.id), "name": r.name, "capacity": r.capacity} for r in rooms],
        })
