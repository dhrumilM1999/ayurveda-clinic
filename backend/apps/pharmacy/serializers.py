from decimal import Decimal

from rest_framework import serializers

from .models import Purchase, PurchaseItem, StockBatch, StockMovement, Supplier

MAX_LINES = 200


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "gstin", "address", "is_active"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Please enter the supplier name.")
        return value.strip()


class BatchSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)

    class Meta:
        model = StockBatch
        fields = ["id", "medicine", "medicine_name", "batch_no", "expiry_date", "mrp", "purchase_rate", "quantity"]


class MovementSerializer(serializers.ModelSerializer):
    batch_no = serializers.CharField(source="batch.batch_no", read_only=True)
    by = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta:
        model = StockMovement
        fields = ["id", "batch_no", "kind", "quantity", "balance_after", "reason", "reference", "by", "created_at"]


class PurchaseItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    batch_no = serializers.CharField(source="batch.batch_no", read_only=True)
    expiry_date = serializers.DateField(source="batch.expiry_date", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ["id", "medicine", "medicine_name", "batch_no", "expiry_date", "quantity", "purchase_rate", "mrp", "amount"]


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default="")
    items = PurchaseItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta:
        model = Purchase
        fields = ["id", "supplier", "supplier_name", "invoice_no", "invoice_date", "total_amount", "notes", "items",
                  "created_by_name", "created_at"]


class PurchaseLineInput(serializers.Serializer):
    medicine = serializers.UUIDField()
    batch_no = serializers.CharField(max_length=60)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    purchase_rate = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True)
    mrp = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)

    def to_internal_value(self, data):
        if isinstance(data, dict) and data.get("expiry_date") == "":
            data = {**data, "expiry_date": None}  # empty box = no expiry date
        return super().to_internal_value(data)

    def validate_batch_no(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Please enter the batch number.")
        return value


class PurchaseInput(serializers.Serializer):
    supplier = serializers.UUIDField(required=False, allow_null=True)
    invoice_no = serializers.CharField(max_length=60, required=False, allow_blank=True)
    invoice_date = serializers.DateField()
    notes = serializers.CharField(max_length=300, required=False, allow_blank=True)
    items = PurchaseLineInput(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Add at least one medicine.")
        if len(value) > MAX_LINES:
            raise serializers.ValidationError(f"At most {MAX_LINES} lines.")
        return value


class AdjustInput(serializers.Serializer):
    batch = serializers.UUIDField()
    change = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.CharField(max_length=200)

    def validate_change(self, value):
        if value == 0:
            raise serializers.ValidationError("The change cannot be 0.")
        return value


class DispenseLineInput(serializers.Serializer):
    prescription_item = serializers.UUIDField()
    batch = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))


class DispenseInput(serializers.Serializer):
    items = DispenseLineInput(many=True)
    notes = serializers.CharField(max_length=300, required=False, allow_blank=True)
