"""Template helpers for printed documents: Indian money format and tidy quantities."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value):
    """1250050.5 -> '12,50,050.50' (Indian grouping)."""
    try:
        value = Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return value
    sign = "-" if value < 0 else ""
    whole, _, paise = f"{abs(value):.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{sign}{whole}.{paise}"


@register.filter
def qty(value):
    """2.000 -> '2', 0.500 -> '0.5'."""
    try:
        value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    text = f"{value:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text
