from decimal import Decimal

from rest_framework import serializers

from apps.appointments.serializers import patient_summary
from apps.common.serializers import MasterField

from .models import PAYMENT_MODES, ConsultationFee, CreditNote, CreditNoteLine, Invoice, InvoiceLine, Payment, ServiceCharge


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id", "kind", "description", "medicine", "batch", "service", "batch_no", "expiry_date", "hsn_code", "quantity",
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
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True, default="")
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "series", "care_type", "invoice_date", "customer_name", "patient_detail", "doctor_name",
            "total_amount",
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
            "credit_notes", "dispense", "prescription", "created_by_name", "appointment", "visit",
        ]


class PaymentInput(serializers.Serializer):
    mode = serializers.ChoiceField(choices=PAYMENT_MODES)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)


class CancelInput(serializers.Serializer):
    reason = serializers.CharField(max_length=200)
    refund_mode = serializers.ChoiceField(choices=PAYMENT_MODES, default="cash")


# --- OPD: services, fees, charges ------------------------------------------------------------------
class ServiceChargeSerializer(serializers.ModelSerializer):
    category = MasterField("service_category")
    # This branch's own price / on-off (filled by the view)
    branch_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, allow_null=True, default=None)
    branch_active = serializers.BooleanField(read_only=True, default=True)
    effective_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, allow_null=True, default=None)

    class Meta:
        model = ServiceCharge
        fields = [
            "id", "name", "name_gu", "name_hi", "category", "price", "gst_rate", "sac_code", "is_active", "sort_order",
            "is_sample", "branch_price", "branch_active", "effective_price", "updated_at",
        ]
        read_only_fields = ["id", "is_sample", "updated_at"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be below 0.")
        return value

    def validate_gst_rate(self, value):
        if not 0 <= value <= 40:
            raise serializers.ValidationError("GST must be between 0 and 40 %.")
        return value


class BranchPriceInput(serializers.Serializer):
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False)
    is_active = serializers.BooleanField(default=True)


class ConsultationFeeInput(serializers.Serializer):
    doctor = serializers.UUIDField()
    new_case_fee = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    follow_up_fee = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    follow_up_days = serializers.IntegerField(min_value=0, max_value=365)


class ChargeLineInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["consultation", "service", "other"])
    service = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(max_length=250, required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"), default=Decimal("1"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0"),
                                                max_value=Decimal("100"), default=Decimal("0"))


class PaymentNow(serializers.Serializer):
    mode = serializers.ChoiceField(choices=PAYMENT_MODES)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)


class ChargeInput(serializers.Serializer):
    """Put charges on an OPD bill. Give an appointment, a visit, or (a bill without a visit) a patient."""

    appointment = serializers.UUIDField(required=False, allow_null=True)
    visit = serializers.UUIDField(required=False, allow_null=True)
    patient = serializers.UUIDField(required=False, allow_null=True)
    doctor = serializers.UUIDField(required=False, allow_null=True)
    lines = ChargeLineInput(many=True, allow_empty=False)
    payment = PaymentNow(required=False, allow_null=True)
