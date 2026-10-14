from decimal import Decimal

from rest_framework import serializers

from .models import (
    Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem, Rack, StockBatch, StockMovement, StockVerification,
    StockVerificationItem, Supplier,
)

MAX_LINES = 300
POSITIVE = {"max_digits": 12, "decimal_places": 3, "min_value": Decimal("0.001")}
MONEY = {"max_digits": 12, "decimal_places": 2, "min_value": Decimal("0")}


class RackSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Rack
        fields = ["id", "code", "name", "shelves", "sort_order", "is_active", "product_count"]
        read_only_fields = ["id", "product_count"]

    def validate_code(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Please enter the rack code, e.g. A.")
        branch = self.context["branch"]
        clash = Rack.objects.filter(branch=branch, code=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("This rack code already exists.")
        return value


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "email", "gstin", "drug_licence_no", "address", "state",
                  "payment_terms_days", "is_active"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Please enter the supplier name.")
        return value.strip()

    def validate_gstin(self, value):
        value = (value or "").strip().upper()
        if value and len(value) != 15:
            raise serializers.ValidationError("GSTIN has 15 characters.")
        return value


class BatchSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default="")
    sale_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = StockBatch
        fields = ["id", "medicine", "medicine_name", "batch_no", "mfg_date", "expiry_date", "mrp", "selling_price",
                  "sale_price", "purchase_rate", "gst_rate", "barcode", "supplier_name", "quantity"]


class MovementSerializer(serializers.ModelSerializer):
    batch_no = serializers.CharField(source="batch.batch_no", read_only=True)
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    by = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta:
        model = StockMovement
        fields = ["id", "medicine", "medicine_name", "batch_no", "kind", "quantity", "balance_after", "reason",
                  "reference", "reference_label", "by", "created_at"]


class PurchaseItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    batch_no = serializers.CharField(source="batch.batch_no", read_only=True)
    mfg_date = serializers.DateField(source="batch.mfg_date", read_only=True)
    expiry_date = serializers.DateField(source="batch.expiry_date", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ["id", "medicine", "medicine_name", "batch", "batch_no", "mfg_date", "expiry_date", "quantity",
                  "free_quantity", "purchase_rate", "discount_percent", "gst_rate", "mrp", "selling_price",
                  "taxable_amount", "gst_amount", "amount"]


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default="")
    items = PurchaseItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta:
        model = Purchase
        fields = ["id", "supplier", "supplier_name", "invoice_no", "invoice_date", "is_opening", "taxable_amount",
                  "discount_amount", "gst_amount", "other_charges", "round_off", "total_amount", "notes", "items",
                  "created_by_name", "created_at"]


class PurchaseLineInput(serializers.Serializer):
    medicine = serializers.UUIDField()
    # Empty is allowed only when "Batch tracking" is off (the view then fills an automatic batch)
    batch_no = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    mfg_date = serializers.DateField(required=False, allow_null=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    quantity = serializers.DecimalField(**POSITIVE)
    free_quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0"), required=False, default=0)
    purchase_rate = serializers.DecimalField(required=False, allow_null=True, **MONEY)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0"),
                                                max_value=Decimal("100"), required=False, default=0)
    gst_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("40"),
                                        required=False)
    # Needed while "Selling price / MRP" is on (checked in the view)
    mrp = serializers.DecimalField(required=False, allow_null=True, default=None, **MONEY)
    selling_price = serializers.DecimalField(required=False, allow_null=True, **MONEY)
    barcode = serializers.CharField(max_length=64, required=False, allow_blank=True)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = {k: (None if v == "" and k in ("mfg_date", "expiry_date", "purchase_rate", "selling_price") else v)
                    for k, v in data.items()}
        return super().to_internal_value(data)

    def validate_batch_no(self, value):
        return (value or "").strip().upper()


class PurchaseInput(serializers.Serializer):
    supplier = serializers.UUIDField(required=False, allow_null=True)
    invoice_no = serializers.CharField(max_length=60, required=False, allow_blank=True)
    invoice_date = serializers.DateField(required=False)
    is_opening = serializers.BooleanField(required=False, default=False)
    other_charges = serializers.DecimalField(required=False, default=0, **MONEY)
    notes = serializers.CharField(max_length=300, required=False, allow_blank=True)
    items = PurchaseLineInput(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Add at least one medicine.")
        if len(value) > MAX_LINES:
            raise serializers.ValidationError(f"At most {MAX_LINES} lines.")
        return value

    def validate(self, attrs):
        if not attrs.get("is_opening") and not attrs.get("invoice_date"):
            raise serializers.ValidationError({"invoice_date": "Please enter the invoice date."})
        return attrs


class PurchaseReturnItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    batch_no = serializers.CharField(source="batch.batch_no", read_only=True)

    class Meta:
        model = PurchaseReturnItem
        fields = ["id", "medicine_name", "batch_no", "quantity", "rate", "amount"]


class PurchaseReturnSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default="")
    items = PurchaseReturnItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta:
        model = PurchaseReturn
        fields = ["id", "supplier", "supplier_name", "return_date", "reference", "reason", "total_amount", "items",
                  "created_by_name", "created_at"]


class BatchQuantityInput(serializers.Serializer):
    batch = serializers.UUIDField()
    quantity = serializers.DecimalField(**POSITIVE)


class PurchaseReturnInput(serializers.Serializer):
    supplier = serializers.UUIDField(required=False, allow_null=True)
    reference = serializers.CharField(max_length=60, required=False, allow_blank=True)
    reason = serializers.CharField(max_length=200)
    items = BatchQuantityInput(many=True)


class AdjustInput(serializers.Serializer):
    batch = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["adjust", "damaged", "expired"], default="adjust")
    change = serializers.DecimalField(max_digits=12, decimal_places=3)
    reason = serializers.CharField(max_length=200)

    def validate_change(self, value):
        if value == 0:
            raise serializers.ValidationError("The change cannot be 0.")
        return value


class LocationInput(serializers.Serializer):
    medicine = serializers.UUIDField()
    rack = serializers.UUIDField(required=False, allow_null=True)
    shelf = serializers.CharField(max_length=20, required=False, allow_blank=True)
    bin = serializers.CharField(max_length=20, required=False, allow_blank=True)


class SellLineInput(serializers.Serializer):
    # Empty = a medicine that is not on the prescription (scanned at the counter); the batch says which medicine
    prescription_item = serializers.UUIDField(required=False, allow_null=True)
    batch = serializers.UUIDField()
    quantity = serializers.DecimalField(required=False, allow_null=True, **POSITIVE)
    loose_units = serializers.DecimalField(required=False, allow_null=True, **POSITIVE)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0"),
                                                max_value=Decimal("100"), required=False, default=0)

    def validate(self, attrs):
        if not attrs.get("quantity") and not attrs.get("loose_units"):
            raise serializers.ValidationError("Enter the quantity.")
        return attrs


class PaymentNowInput(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["cash", "upi", "card"])
    amount = serializers.DecimalField(**MONEY)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)


class SellInput(serializers.Serializer):
    items = SellLineInput(many=True)
    notes = serializers.CharField(max_length=300, required=False, allow_blank=True)
    payment = PaymentNowInput(required=False, allow_null=True)


class CounterSaleInput(SellInput):
    customer_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    customer_phone = serializers.RegexField(r"^\d{10}$", required=False, allow_blank=True,
                                            error_messages={"invalid": "Phone must be 10 digits."})


class ReturnLineInput(serializers.Serializer):
    dispense_item = serializers.UUIDField()
    quantity = serializers.DecimalField(**POSITIVE)
    back_to_stock = serializers.BooleanField(default=True)


class SaleReturnInput(serializers.Serializer):
    reason = serializers.CharField(max_length=200)
    refund_mode = serializers.ChoiceField(choices=["cash", "upi", "card"], default="cash")
    items = ReturnLineInput(many=True)


class VerificationItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="batch.medicine.name", read_only=True)
    batch_no = serializers.CharField(source="batch.batch_no", read_only=True)
    expiry_date = serializers.DateField(source="batch.expiry_date", read_only=True)
    difference = serializers.SerializerMethodField()

    class Meta:
        model = StockVerificationItem
        fields = ["id", "batch", "medicine_name", "batch_no", "expiry_date", "system_quantity", "counted_quantity",
                  "difference"]

    def get_difference(self, obj):
        return None if obj.counted_quantity is None else str(obj.counted_quantity - obj.system_quantity)


class VerificationSerializer(serializers.ModelSerializer):
    rack_code = serializers.CharField(source="rack.code", read_only=True, default="")
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")
    item_count = serializers.SerializerMethodField()
    counted_count = serializers.SerializerMethodField()
    mismatch_count = serializers.SerializerMethodField()

    class Meta:
        model = StockVerification
        fields = ["id", "title", "rack", "rack_code", "status", "notes", "completed_at", "created_at",
                  "created_by_name", "item_count", "counted_count", "mismatch_count"]

    def get_item_count(self, obj):
        return len(obj.items.all())

    def get_counted_count(self, obj):
        return sum(1 for i in obj.items.all() if i.counted_quantity is not None)

    def get_mismatch_count(self, obj):
        return sum(1 for i in obj.items.all() if i.counted_quantity is not None and i.counted_quantity != i.system_quantity)


class CountInput(serializers.Serializer):
    item = serializers.UUIDField()
    counted_quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0"), allow_null=True)
