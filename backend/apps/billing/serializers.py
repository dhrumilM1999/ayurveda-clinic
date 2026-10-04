from decimal import Decimal

from rest_framework import serializers

from apps.appointments.serializers import patient_summary

from .models import PAYMENT_MODES, CreditNote, CreditNoteLine, Invoice, InvoiceLine, Payment


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id", "kind", "description", "medicine", "batch", "batch_no", "expiry_date", "hsn_code", "quantity",
            "unit_label", "unit_price", "discount_percent", "gross_amount", "discount_amount", "gst_rate",
            "taxable_amount", "cgst_amount", "sgst_amount", "total_amount", "credited_quantity",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    received_by = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta:
        model = Payment
        fields = ["id", "mode", "amount", "reference", "paid_at", "received_by"]


class CreditNoteLineSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source="invoice_line.description", read_only=True)

    class Meta:
        model = CreditNoteLine
        fields = ["id", "description", "quantity", "taxable_amount", "cgst_amount", "sgst_amount", "total_amount"]


class CreditNoteSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.number", read_only=True)
    customer_name = serializers.CharField(source="invoice.customer_name", read_only=True)
    lines = CreditNoteLineSerializer(many=True, read_only=True)

    class Meta:
        model = CreditNote
        fields = [
            "id", "number", "note_date", "invoice", "invoice_number", "customer_name", "reason", "taxable_amount",
            "cgst_amount", "sgst_amount", "total_amount", "refund_mode", "refund_amount", "lines", "created_at",
        ]


class InvoiceListSerializer(serializers.ModelSerializer):
    patient_detail = serializers.SerializerMethodField()
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "series", "invoice_date", "customer_name", "patient_detail", "total_amount",
            "paid_amount", "credited_amount", "refunded_amount", "balance", "status", "print_count", "created_at",
        ]

    def get_patient_detail(self, obj):
        return patient_summary(obj.patient) if obj.patient_id else None


class InvoiceSerializer(InvoiceListSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    credit_notes = CreditNoteSerializer(many=True, read_only=True)
    dispense = serializers.UUIDField(source="dispense_id", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + [
            "financial_year", "place_of_supply", "gross_amount", "discount_amount", "taxable_amount", "cgst_amount",
            "sgst_amount", "igst_amount", "round_off", "notes", "cancelled_at", "cancel_reason", "lines", "payments",
            "credit_notes", "dispense", "prescription", "created_by_name",
        ]


class PaymentInput(serializers.Serializer):
    mode = serializers.ChoiceField(choices=PAYMENT_MODES)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)


class CancelInput(serializers.Serializer):
    reason = serializers.CharField(max_length=200)
    refund_mode = serializers.ChoiceField(choices=PAYMENT_MODES, default="cash")
