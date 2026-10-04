from rest_framework.routers import DefaultRouter

from .views import (
    DispensingViewSet, PurchaseReturnViewSet, PurchaseViewSet, RackViewSet, SaleViewSet, StockViewSet, SupplierViewSet,
    VerificationViewSet,
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

urlpatterns = router.urls
