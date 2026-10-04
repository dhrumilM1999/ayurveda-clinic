from rest_framework.routers import DefaultRouter

from .views import DispensingViewSet, PurchaseViewSet, StockViewSet, SupplierViewSet

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("purchases", PurchaseViewSet, basename="purchase")
router.register("stock", StockViewSet, basename="stock")
router.register("dispensing", DispensingViewSet, basename="dispensing")

urlpatterns = router.urls
