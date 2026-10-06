"""
Print-outs as PDF, certificates, WhatsApp share of a prescription, and the public "is this genuine?" check.

GET /documents/<kind>/<id>/   kind: prescription (id = prescription), follow-up-card / prakriti (id = visit),
                              certificate (id = certificate).  ?size=a4|a5|a6  ?lang=en|gu|hi
                              ?preview=1 (on screen, not counted)  ?download=1
                              ?detail=1 (prescription only: the detailed prescription with the full check-up)
Every view / print / share is written to the audit log.
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status as http, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import BranchPermission
from apps.accounts.services import user_has_perm
from apps.audit.services import log_action
from apps.emr.models import Visit, VisitExam
from apps.prescriptions.models import Prescription

from .models import Certificate, IssuedDocument
from .serializers import CertificateSerializer
from .services import (
    SIZES, certificate_context, detailed_context, follow_up_context, issue, language_of, mark_printed, pad_for,
    prakriti_context, prescription_context, render, verify_url, _qr,
)
from .words import words_for

DEFAULT_SIZE = {"prescription": "a5", "follow-up-card": "a6", "prakriti": "a4", "certificate": "a4"}
PERMISSIONS = {  # any one of these codes
    "prescription": ("prescriptions.view",),
    "follow-up-card": ("emr.view", "appointments.view"),
    "prakriti": ("emr.view",),
    "certificate": ("emr.view",),
}


def _any_perm(request, codes):
    if not any(user_has_perm(request.user, code, request.branch) for code in codes):
        raise PermissionDenied()


def _load(kind, request, pk):
    """(the record, IssuedDocument, template, context-maker, patient)."""
    branch = request.branch
    if kind == "prescription":
        rx = (Prescription.objects.filter(branch=branch, pk=pk)
              .select_related("visit__appointment", "patient", "doctor", "branch__organization").first())
        if rx is None:
            raise NotFound("Prescription not found.")
        doc = issue("prescription", rx.id, branch=branch, patient=rx.patient, doctor=rx.doctor,
                    issued_on=rx.visit.visit_date, series="RX")
        return rx, doc, "prescription.html", lambda lang: prescription_context(rx, lang), rx.patient
    if kind in ("follow-up-card", "prakriti"):
        visit = Visit.objects.filter(branch=branch, pk=pk).select_related("patient", "doctor", "branch__organization").first()
        if visit is None:
            raise NotFound("Check-up not found.")
        if kind == "follow-up-card":
            if not visit.follow_up_date:
                raise ValidationError({"detail": "Set the follow-up date first."})
            doc = issue("follow_up_card", visit.id, branch=branch, patient=visit.patient, doctor=visit.doctor,
                        issued_on=visit.visit_date)
            return visit, doc, "follow_up_card.html", lambda lang: follow_up_context(visit, lang), visit.patient
        exam = VisitExam.objects.filter(visit=visit, template_code="prakriti").first()
        if exam is None or not (exam.result or {}).get("answered"):
            raise ValidationError({"detail": "Fill the Prakriti questionnaire first."})
        doc = issue("prakriti_report", visit.id, branch=branch, patient=visit.patient, doctor=visit.doctor,
                    issued_on=visit.visit_date)
        return visit, doc, "prakriti_report.html", lambda lang: prakriti_context(visit, exam, lang), visit.patient
    if kind == "certificate":
        cert = Certificate.objects.filter(branch=branch, pk=pk).select_related("patient", "doctor", "branch__organization").first()
        if cert is None:
            raise NotFound("Certificate not found.")
        doc = issue("certificate", cert.id, branch=branch, patient=cert.patient, doctor=cert.doctor,
                    issued_on=cert.issued_on, number=cert.number)
        return cert, doc, "certificate.html", lambda lang: certificate_context(cert, lang), cert.patient
    raise NotFound("Unknown document.")


class DocumentPdfView(APIView):
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True

    def get(self, request, kind, pk):
        from apps.billing.views import pdf_response

        if kind not in PERMISSIONS:
            raise NotFound("Unknown document.")
        _any_perm(request, PERMISSIONS[kind])
        size = request.query_params.get("size") or DEFAULT_SIZE[kind]
        if size not in SIZES:
            raise ValidationError({"size": "Choose a4, a5 or a6."})
        record, doc, template, make, patient = _load(kind, request, pk)
        lang = language_of(patient, request.query_params.get("lang"))
        preview = request.query_params.get("preview") == "1"
        # ?detail=1: the DETAILED prescription (full check-up summary). It has the full medical history, so it
        # needs "See full medical history" as well.
        detailed = kind == "prescription" and request.query_params.get("detail") == "1"
        if detailed:
            _any_perm(request, ("emr.view",))
        duplicate = doc.print_count > 0 if preview else mark_printed(doc)
        context = make(lang)
        if detailed:
            context.update(detailed_context(record, lang))
        content = render(template, size, {
            **context, "number": doc.number, "duplicate": duplicate, "qr": _qr(verify_url(doc)),
            "is_cancelled": doc.is_cancelled,
            # Prescriptions on the clinic's pre-printed pad (Settings -> Branch details)
            "pad": pad_for(request.branch, size) if kind == "prescription" else None,
        })
        log_action(request, "view" if preview else "print", record, changes={
            "document": kind, "number": doc.number, "size": size, "duplicate": duplicate, "patient": str(patient.id),
            **({"detailed": True} if detailed else {})})
        return pdf_response(content, f"{kind}-{doc.number or str(doc.id)[:8]}.pdf".replace("/", "-"),
                            request.query_params.get("download") == "1")


class PrescriptionShareView(APIView):
    """POST /documents/prescription/<id>/whatsapp/ -> a WhatsApp link with the medicines as text
    (only if the patient agreed to messages)."""

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True

    def post(self, request, pk):
        from apps.notifications.whatsapp import prepare_whatsapp
        from apps.patients.services import has_consent

        _any_perm(request, ("prescriptions.view",))
        rx, doc, _, make, patient = _load("prescription", request, pk)
        if not has_consent(patient, "communication"):
            return Response({"consent": False, "link": "", "message": ""})
        if not patient.mobile:
            raise ValidationError({"detail": "The patient has no mobile number."})
        lang = language_of(patient)
        data, w = make(lang), words_for(lang)
        lines = [f"{data['organization'].name} - {w['prescription']} {doc.number}", f"{w['patient']}: {patient.full_name}",
                 f"{w['date']}: {data['date']:%d-%m-%Y}", ""]
        for n, item in enumerate(data["items"], 1):
            parts = [item["dose"], item["frequency"], item["timing"], item["with_anupana"], item["duration"]]
            lines.append(f"{n}. {item['name']} - " + ", ".join(p for p in parts if p))
            if item["instructions"]:
                lines.append(f"   {item['instructions']}")
        if data["follow_up_date"]:
            lines += ["", f"{w['follow_up']}: {data['follow_up_date']:%d-%m-%Y}"]
        lines += ["", f"{w['verify']}: {verify_url(doc)}"]
        message = "\n".join(lines)
        link = prepare_whatsapp(patient.mobile, message, organization=rx.branch.organization, purpose="prescription")
        log_action(request, "share", rx, changes={"channel": "whatsapp", "number": doc.number, "patient": str(patient.id)})
        return Response({"consent": True, "link": link, "message": message})


class CertificateViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Certificates of this branch. ?patient= ?visit=. Never deleted: POST /certificates/<id>/cancel/ {reason}."""

    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True
    required_permissions = {"list": "emr.view", "retrieve": "emr.view", "create": "emr.edit", "cancel": "emr.edit"}

    def get_queryset(self):
        qs = Certificate.objects.filter(branch=self.request.branch).select_related("patient", "doctor")
        p = self.request.query_params
        if p.get("patient"):
            qs = qs.filter(patient_id=p["patient"])
        if p.get("visit"):
            qs = qs.filter(visit_id=p["visit"])
        return qs

    def perform_create(self, serializer):
        from apps.billing.services import next_number

        today = timezone.localdate()
        number, _ = next_number(self.request.branch, "MC", today)
        cert = serializer.save(organization_id=self.request.branch.organization_id, branch=self.request.branch,
                               number=number, issued_on=today, created_by=self.request.user, updated_by=self.request.user)
        log_action(self.request, "create", cert, changes={"patient": str(cert.patient_id), "kind": cert.kind, "number": number})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        cert = self.get_object()
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            raise ValidationError({"reason": "Please write the reason."})
        cert.is_cancelled, cert.cancel_reason, cert.updated_by = True, reason[:200], request.user
        cert.save(update_fields=["is_cancelled", "cancel_reason", "updated_by", "updated_at"])
        IssuedDocument.objects.filter(kind="certificate", object_id=str(cert.id)).update(is_cancelled=True)
        log_action(request, "update", cert, changes={"cancelled": reason[:200]})
        return Response(self.get_serializer(cert).data)


class VerifyView(APIView):
    """GET /verify/<token>/ - public: is this print-out genuine? Shows no medical details."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify"

    def get(self, request, token):
        doc = (IssuedDocument.objects.filter(token=token).select_related("branch__organization", "doctor", "patient")
               .filter(Q(is_deleted=False)).first())
        if doc is None:
            return Response({"valid": False}, status=http.HTTP_404_NOT_FOUND)
        patient = doc.patient
        initials = " ".join(f"{part[0]}." for part in (patient.full_name.split() if patient else []) if part)
        return Response({
            "valid": not doc.is_cancelled, "cancelled": doc.is_cancelled, "kind": doc.kind,
            "kind_label": doc.get_kind_display(), "number": doc.number, "issued_on": doc.issued_on,
            "clinic": doc.branch.organization.name, "branch": doc.branch.name,
            "doctor": doc.doctor.full_name if doc.doctor else "", "patient_initials": initials,
        })
