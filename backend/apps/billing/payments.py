"""
Payment adapter. PAYMENT_PROVIDER in .env:
- "static_upi" (free): a UPI link / QR code with the amount; the patient pays with any UPI app and staff
  mark the bill as paid. No money passes through this software.
- "fake": used by automated tests.
A paid gateway (Razorpay) can be added later as one more class here.
"""
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings

from apps.common.adapters import load_provider


class BasePaymentProvider:
    name = "base"

    def payment_link(self, *, vpa: str, payee: str, amount: Decimal, note: str) -> str:
        raise NotImplementedError


class StaticUpiProvider(BasePaymentProvider):
    name = "static_upi"

    def payment_link(self, *, vpa, payee, amount, note):
        return (f"upi://pay?pa={quote(vpa)}&pn={quote(payee)}&am={Decimal(amount):.2f}"
                f"&cu=INR&tn={quote(note)}")


class FakePaymentProvider(StaticUpiProvider):
    name = "fake"


PROVIDERS = {
    "static_upi": "apps.billing.payments.StaticUpiProvider",
    "fake": "apps.billing.payments.FakePaymentProvider",
}


def get_payment_provider() -> BasePaymentProvider:
    return load_provider("Payment", settings.PAYMENT_PROVIDER, PROVIDERS)


def upi_link_for(invoice) -> str:
    """UPI link for what is still due on a bill ('' if nothing is due or the branch has no UPI ID)."""
    branch = invoice.branch
    if not branch.upi_vpa or invoice.balance <= 0:
        return ""
    payee = branch.organization.name if branch.organization_id else branch.name
    return get_payment_provider().payment_link(vpa=branch.upi_vpa, payee=payee, amount=invoice.balance,
                                               note=f"Bill {invoice.number}")
