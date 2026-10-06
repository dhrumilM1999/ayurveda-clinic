"""
Makes the PDF of a bill or credit note from backend/templates/documents/invoice.html (SAFE TO EDIT there).
Paper sizes: A4, A5 and thermal 80 mm. Reprints say "DUPLICATE COPY".
"""
from decimal import Decimal

from django.template.loader import render_to_string

from .payments import upi_link_for

SIZES = {"a4": ("210mm", "297mm", "12mm"), "a5": ("148mm", "210mm", "8mm"), "80mm": ("80mm", None, "3mm"),
         "58mm": ("58mm", None, "2mm")}

ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
        "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n):
    return ONES[n] if n < 20 else f"{TENS[n // 10]} {ONES[n % 10]}".strip()


def _three(n):
    hundred, rest = divmod(n, 100)
    return " ".join(p for p in [f"{ONES[hundred]} Hundred" if hundred else "", _two(rest)] if p)


def rupees_in_words(amount: Decimal) -> str:
    """Indian style: 1,25,050.50 -> 'Rupees One Lakh Twenty Five Thousand Fifty and Fifty Paise Only'."""
    amount = Decimal(amount).quantize(Decimal("0.01"))
    whole, paise = int(amount), int((amount - int(amount)) * 100)
    if whole == 0 and paise == 0:
        return "Rupees Zero Only"
    parts = []
    crore, whole = divmod(whole, 10_000_000)
    lakh, whole = divmod(whole, 100_000)
    thousand, whole = divmod(whole, 1000)
    if crore:
        parts.append(f"{_three(crore)} Crore")
    if lakh:
        parts.append(f"{_two(lakh)} Lakh")
    if thousand:
        parts.append(f"{_two(thousand)} Thousand")
    if whole:
        parts.append(_three(whole))
    words = "Rupees " + " ".join(parts) if parts else "Rupees Zero"
    if paise:
        words += f" and {_two(paise)} Paise"
    return words + " Only"


def _qr_data_uri(link: str) -> str:
    import segno

    return segno.make(link, error="m").svg_data_uri(scale=3, border=1)


def _gst_summary(lines):
    """Taxable / CGST / SGST grouped by GST rate (needed on GST bills)."""
    groups = {}
    for line in lines:
        g = groups.setdefault(line.gst_rate, {"rate": line.gst_rate, "taxable": 0, "cgst": 0, "sgst": 0})
        g["taxable"] += line.taxable_amount
        g["cgst"] += line.cgst_amount
        g["sgst"] += line.sgst_amount
    return sorted(groups.values(), key=lambda g: g["rate"])


def render_pdf(*, invoice, size="a4", duplicate=False, credit_note=None) -> bytes:
    from weasyprint import HTML

    width, height, margin = SIZES.get(size, SIZES["a4"])
    lines = list(invoice.lines.all()) if credit_note is None else [cl.invoice_line for cl in credit_note.lines.all()]
    if height is None:  # thermal roll: height grows with the number of lines
        height = f"{150 + 14 * len(lines)}mm"
    upi = upi_link_for(invoice) if credit_note is None else ""
    html = render_to_string("documents/invoice.html", {
        "invoice": invoice, "lines": lines, "credit_note": credit_note,
        "credit_lines": list(credit_note.lines.all()) if credit_note else [],
        "branch": invoice.branch, "organization": invoice.branch.organization,
        "patient": invoice.patient,
        "doctor": invoice.doctor or (invoice.prescription.doctor if invoice.prescription_id else None),
        "is_opd": invoice.series == "OP", "has_gst": any(line.gst_rate for line in lines),
        "has_batches": any(line.batch_no for line in lines),
        "gst_summary": _gst_summary(lines),
        "amount_words": rupees_in_words(credit_note.total_amount if credit_note else invoice.total_amount),
        "upi_qr": _qr_data_uri(upi) if upi else "", "duplicate": duplicate,
        "size": size, "narrow": size in ("80mm", "58mm"), "page_width": width, "page_height": height, "page_margin": margin,
    })
    return HTML(string=html).write_pdf()
