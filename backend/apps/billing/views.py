from datetime import date as date_cls
from decimal import Decimal

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.audit.services import log_action

from .models import CreditNote, Invoice
from .payments import upi_link_for
from .pdf import SIZES, render_pdf
from .serializers import CancelInput, CreditNoteSerializer, InvoiceListSerializer, InvoiceSerializer, PaymentInput
from .services import create_credit_note, day_summary, record_payment


def _day(raw, default=None):
    if not raw:
        return default
    try:
        return date_cls.fromisoformat(raw)
    except ValueError:
        raise ValidationError({"date": "Date must look like 2026-10-05."})


def pdf_response(content: bytes, filename: str, download: bool):
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'{"attachment" if download else "inline"}; filename="{filename}"'
    return response


class InvoiceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Bills of the current branch. ?date= / ?date_from= ?date_to=  ?status=  ?series=PH  ?q= (number / patient)
    Viewing, printing and payments are written to the audit log. Bills are never deleted.
    """

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True
    required_permissions = {
        "list": "billing.view", "retrieve": "billing.view", "pdf": "billing.view", "upi": "billing.view",
        "summary": "billing.view", "pay": "billing.create", "cancel": "billing.refund",
    }

    def get_serializer_class(self):
        return InvoiceListSerializer if self.action == "list" else InvoiceSerializer

    def get_queryset(self):
        qs = Invoice.objects.filter(branch=self.request.branch).select_related("patient", "created_by", "branch")
        if self.action != "list":
            return qs.prefetch_related("lines", "payments__created_by", "credit_notes__lines__invoice_line")
        p = self.request.query_params
        if p.get("date"):
            qs = qs.filter(invoice_date=_day(p["date"]))
        if p.get("date_from"):
            qs = qs.filter(invoice_date__gte=_day(p["date_from"]))
        if p.get("date_to"):
            qs = qs.filter(invoice_date__lte=_day(p["date_to"]))
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("series"):
            qs = qs.filter(series=p["series"])
        if p.get("patient"):
            qs = qs.filter(patient_id=p["patient"])
        if p.get("q", "").strip():
            q = p["q"].strip()
            qs = qs.filter(Q(number__icontains=q) | Q(customer_name__icontains=q) | Q(patient__uhid__icontains=q))
        return qs

    def retrieve(self, request, *args, **kwargs):
        invoice = self.get_object()
        log_action(request, "view", invoice, changes={"patient": str(invoice.patient_id or "")})
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        data = PaymentInput(data=request.data)
        data.is_valid(raise_exception=True)
        invoice = self.get_object()
        payment = record_payment(invoice, request.user, **data.validated_data)
        log_action(request, "update", invoice, changes={"payment": {"mode": payment.mode, "amount": str(payment.amount)}})
        return Response(self.get_serializer(self.get_queryset().get(pk=invoice.pk)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel the whole bill with a credit note. Pharmacy bills also put the medicines back in stock."""
        data = CancelInput(data=request.data)
        data.is_valid(raise_exception=True)
        invoice = self.get_object()
        if invoice.status == "cancelled":
            raise ValidationError({"detail": "Already cancelled."})
        if invoice.dispense_id:
            from apps.pharmacy.services import take_back

            items = [{"dispense_item": i, "quantity": i.quantity - i.returned_quantity, "back_to_stock": True}
                     for i in invoice.dispense.items.all() if i.quantity > i.returned_quantity]
            take_back(invoice.dispense, request.branch, request.user, items=items, reason=data.validated_data["reason"],
                      refund_mode=data.validated_data["refund_mode"])
        else:
            items = [(line, line.quantity - line.credited_quantity) for line in invoice.lines.all()
                     if line.quantity > line.credited_quantity]
            create_credit_note(invoice, request.user, items=items, **data.validated_data)
        log_action(request, "update", invoice, changes={"cancelled": data.validated_data["reason"]})
        return Response(self.get_serializer(self.get_queryset().get(pk=invoice.pk)).data)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        """?size=a4|a5|80mm  ?download=1. The first print is the original; later prints say DUPLICATE COPY."""
        invoice = self.get_object()
        size = request.query_params.get("size", "a4")
        if size not in SIZES:
            raise ValidationError({"size": "Choose a4, a5 or 80mm."})
        duplicate = invoice.print_count > 0
        content = render_pdf(invoice=invoice, size=size, duplicate=duplicate)
        Invoice.objects.filter(pk=invoice.pk).update(print_count=invoice.print_count + 1)
        log_action(request, "print", invoice, changes={"size": size, "duplicate": duplicate,
                                                       "patient": str(invoice.patient_id or "")})
        return pdf_response(content, f"{invoice.number.replace('/', '-')}.pdf", request.query_params.get("download") == "1")

    @action(detail=True, methods=["get"])
    def upi(self, request, pk=None):
        invoice = self.get_object()
        return Response({"link": upi_link_for(invoice), "amount": str(invoice.balance), "vpa": request.branch.upi_vpa})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Daily closing for one day (default today)."""
        data = day_summary(request.branch, _day(request.query_params.get("date"), timezone.localdate()))

        def text(value):  # money as "60.00" like everywhere else in the API
            if isinstance(value, dict):
                return {k: text(v) for k, v in value.items()}
            return str(value) if isinstance(value, Decimal) else value

        return Response(text(data))


class CreditNoteViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True
    required_permissions = {"list": "billing.view", "retrieve": "billing.view", "pdf": "billing.view"}

    def get_queryset(self):
        qs = CreditNote.objects.filter(branch=self.request.branch).select_related("invoice").prefetch_related("lines__invoice_line")
        if self.request.query_params.get("date"):
            qs = qs.filter(note_date=_day(self.request.query_params["date"]))
        return qs

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        note = self.get_object()
        size = request.query_params.get("size", "a4")
        if size not in SIZES:
            raise ValidationError({"size": "Choose a4, a5 or 80mm."})
        content = render_pdf(invoice=note.invoice, credit_note=note, size=size)
        log_action(request, "print", note, changes={"size": size})
        return pdf_response(content, f"{note.number.replace('/', '-')}.pdf", request.query_params.get("download") == "1")
