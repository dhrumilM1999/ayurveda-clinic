from rest_framework.routers import DefaultRouter

from .opd_views import ConsultationFeeViewSet, OpdBillViewSet, ServiceChargeViewSet
from .views import CreditNoteViewSet, InvoiceViewSet

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("credit-notes", CreditNoteViewSet, basename="credit-note")
router.register("services", ServiceChargeViewSet, basename="service-charge")
router.register("consultation-fees", ConsultationFeeViewSet, basename="consultation-fee")
router.register("opd-bills", OpdBillViewSet, basename="opd-bill")

urlpatterns = router.urls
