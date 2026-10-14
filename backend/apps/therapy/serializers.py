from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.appointments.serializers import patient_summary

from .models import TherapyPlan, TherapyPlanItem, TherapySession, TherapyType
from .services import check_free


class TherapyTypeSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True, default=None)
    price = serializers.DecimalField(source="service.price", max_digits=12, decimal_places=2, read_only=True, default=None)

    class Meta:
        model = TherapyType
        fields = ["id", "name", "name_gu", "name_hi", "stage", "duration_minutes", "default_material", "instructions",
                  "service", "service_name", "price", "is_active", "sort_order", "is_sample"]

    def validate_service(self, service):
        org_id = self.context["request"].user.organization_id
        if service is not None and service.organization_id != org_id:
            raise serializers.ValidationError("Choose a service from your own list.")
        return service


class TherapySessionSerializer(serializers.ModelSerializer):
    patient_detail = serializers.SerializerMethodField()
    therapy_name = serializers.CharField(source="therapy.name", read_only=True)
    therapy_name_gu = serializers.CharField(source="therapy.name_gu", read_only=True)
    therapy_name_hi = serializers.CharField(source="therapy.name_hi", read_only=True)
    stage = serializers.CharField(source="item.stage", read_only=True)
    plan_title = serializers.CharField(source="plan.title", read_only=True)
    therapist_name = serializers.CharField(source="therapist.full_name", read_only=True, default=None)
    room_name = serializers.CharField(source="room.name", read_only=True, default=None)
    session_no = serializers.SerializerMethodField()
    sessions_planned = serializers.IntegerField(source="item.sessions_planned", read_only=True)

    class Meta:
        model = TherapySession
        fields = ["id", "plan", "plan_title", "item", "patient", "patient_detail", "therapy", "therapy_name",
                  "therapy_name_gu", "therapy_name_hi", "stage", "therapist", "therapist_name", "room", "room_name",
                  "date", "start_time", "end_time", "status", "session_no", "sessions_planned", "material_used",
                  "quantity_ml", "patient_response", "notes", "started_at", "completed_at"]
        read_only_fields = ["plan", "item", "patient", "therapy", "started_at", "completed_at"]

    def get_patient_detail(self, obj):
        return patient_summary(obj.patient)

    def get_session_no(self, obj):
        """1st, 2nd ... session of this therapy in the plan (by date)."""
        cache = self.context.setdefault("_session_no", {})
        if obj.item_id not in cache:
            ids = TherapySession.objects.filter(item_id=obj.item_id).exclude(status="cancelled") \
                .order_by("date", "start_time", "created_at").values_list("id", flat=True)
            cache[obj.item_id] = {sid: n for n, sid in enumerate(ids, 1)}
        return cache[obj.item_id].get(obj.id)

    def validate(self, attrs):
        branch = self.context["branch"]
        org_id = self.context["request"].user.organization_id
        for key in ("therapist", "room"):
            obj = attrs.get(key)
            if obj is not None and obj.organization_id != org_id:
                raise serializers.ValidationError({key: "Not found in your clinic."})
        if self.instance is not None:
            inst = self.instance
            date = attrs.get("date", inst.date)
            start = attrs.get("start_time", inst.start_time)
            end = attrs.get("end_time", inst.end_time)
            therapist = attrs.get("therapist", inst.therapist)
            room = attrs.get("room", inst.room)
            status = attrs.get("status", inst.status)
            if status in ("scheduled", "in_progress", "done"):
                check_free(branch, date, start, end, therapist, room, exclude_id=inst.pk)
        return attrs


class PlanItemSerializer(serializers.ModelSerializer):
    therapy_name = serializers.CharField(source="therapy.name", read_only=True)
    therapy_name_gu = serializers.CharField(source="therapy.name_gu", read_only=True)
    therapy_name_hi = serializers.CharField(source="therapy.name_hi", read_only=True)
    price = serializers.DecimalField(source="therapy.service.price", max_digits=12, decimal_places=2, read_only=True, default=None)
    sessions_booked = serializers.SerializerMethodField()
    sessions_done = serializers.SerializerMethodField()

    class Meta:
        model = TherapyPlanItem
        fields = ["id", "therapy", "therapy_name", "therapy_name_gu", "therapy_name_hi", "stage", "sessions_planned",
                  "sessions_booked", "sessions_done", "price", "notes", "sort_order"]
        read_only_fields = ["id", "sort_order"]

    def _counts(self, obj):
        counts = getattr(obj, "_counts", None)
        if counts is None:
            qs = obj.sessions.exclude(status="cancelled")
            counts = obj._counts = (qs.count(), qs.filter(status="done").count())
        return counts

    def get_sessions_booked(self, obj):
        return self._counts(obj)[0]

    def get_sessions_done(self, obj):
        return self._counts(obj)[1]


class TherapyPlanSerializer(serializers.ModelSerializer):
    items = PlanItemSerializer(many=True)
    patient_detail = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True, default=None)
    sessions_planned = serializers.SerializerMethodField()
    sessions_done = serializers.SerializerMethodField()
    estimate = serializers.SerializerMethodField()

    class Meta:
        model = TherapyPlan
        fields = ["id", "patient", "patient_detail", "doctor", "doctor_name", "visit", "title", "start_date", "status",
                  "notes", "consent_taken", "consent_on", "items", "sessions_planned", "sessions_done", "estimate",
                  "created_at"]
        read_only_fields = ["consent_on"]

    def get_patient_detail(self, obj):
        return patient_summary(obj.patient)

    def get_sessions_planned(self, obj):
        return sum(i.sessions_planned for i in obj.items.all())

    def get_sessions_done(self, obj):
        return obj.sessions.filter(status="done").count()

    def get_estimate(self, obj):
        """Total price if every planned session is done (from the Services & charges list)."""
        total = sum((i.therapy.service.price * i.sessions_planned for i in obj.items.all()
                     if i.therapy.service_id), start=0)
        return str(total)

    def validate_patient(self, patient):
        if patient.organization_id != self.context["request"].user.organization_id:
            raise serializers.ValidationError("Patient not found.")
        return patient

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Add at least one therapy.")
        org_id = self.context["request"].user.organization_id
        for item in items:
            if item["therapy"].organization_id != org_id:
                raise serializers.ValidationError("Therapy not found.")
        return items

    def validate(self, attrs):
        if self.instance is None and "items" not in attrs:
            raise serializers.ValidationError({"items": "Add at least one therapy."})
        return attrs

    @transaction.atomic
    def create(self, validated):
        items = validated.pop("items")
        if validated.get("consent_taken"):
            validated["consent_on"] = timezone.localdate()
        plan = TherapyPlan.objects.create(**validated)
        for n, item in enumerate(items):
            TherapyPlanItem.objects.create(plan=plan, organization_id=plan.organization_id, sort_order=n,
                                           created_by=plan.created_by, updated_by=plan.updated_by, **item)
        return plan

    @transaction.atomic
    def update(self, instance, validated):
        items = validated.pop("items", None)
        if validated.get("consent_taken") and not instance.consent_taken:
            validated["consent_on"] = timezone.localdate()
        for key, value in validated.items():
            setattr(instance, key, value)
        instance.save()
        if items is not None:
            self._sync_items(instance, items)
        return instance

    def _sync_items(self, plan, items):
        """Edit the list: the same therapy keeps its sessions; a therapy with booked sessions cannot be removed."""
        existing = {i.therapy_id: i for i in plan.items.all()}
        wanted = {d["therapy"].id for d in items}
        for n, data in enumerate(items):
            old = existing.get(data["therapy"].id)
            if old is None:
                TherapyPlanItem.objects.create(plan=plan, organization_id=plan.organization_id, sort_order=n, **data)
                continue
            booked = old.sessions.exclude(status="cancelled").count()
            if data.get("sessions_planned", old.sessions_planned) < booked:
                raise serializers.ValidationError({"items": f"{old.therapy.name}: {booked} sessions are already booked."})
            for key in ("stage", "sessions_planned", "notes"):
                if key in data:
                    setattr(old, key, data[key])
            old.sort_order = n
            old.save()
        for therapy_id, old in existing.items():
            if therapy_id in wanted:
                continue
            if old.sessions.exclude(status="cancelled").exists():
                raise serializers.ValidationError({"items": f"{old.therapy.name} has booked sessions; cancel them first."})
            old.delete()


class ScheduleSerializer(serializers.Serializer):
    """Book several sessions of one plan item: pick the days, the time, the therapist and the room."""

    item = serializers.UUIDField()
    dates = serializers.ListField(child=serializers.DateField(), min_length=1, max_length=60)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField(required=False)
    therapist = serializers.UUIDField(required=False, allow_null=True)
    room = serializers.UUIDField(required=False, allow_null=True)
