from django.urls import path
from rest_framework.routers import DefaultRouter

from .labels import MedicineLabelView
from .products import ProductViewSet

from .views import (
    CounterSaleViewSet, DispensingViewSet, PharmacyReportViewSet, PurchaseReturnViewSet, PurchaseViewSet, RackViewSet, SaleViewSet,
    StockViewSet, SupplierAccountViewSet, SupplierPaymentViewSet, SupplierViewSet, VerificationViewSet,
)

router = DefaultRouter()
router.register("racks", RackViewSet, basename="rack")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("purchases", PurchaseViewSet, basename="purchase")
router.register("purchase-returns", PurchaseReturnViewSet, basename="purchase-return")
router.register("stock", StockViewSet, basename="stock")
router.register("stock-checks", VerificationViewSet, basename="stock-check")
router.register("dispensing", DispensingViewSet, basename="dispensing")
router.register("sales", SaleViewSet, basename="sale")
router.register("pharmacy-reports", PharmacyReportViewSet, basename="pharmacy-report")
router.register("counter-sales", CounterSaleViewSet, basename="counter-sale")
router.register("products", ProductViewSet, basename="product")
router.register("supplier-accounts", SupplierAccountViewSet, basename="supplier-account")
router.register("supplier-payments", SupplierPaymentViewSet, basename="supplier-payment")

urlpatterns = [path("medicine-labels/", MedicineLabelView.as_view(), name="medicine-labels")] + router.urls
