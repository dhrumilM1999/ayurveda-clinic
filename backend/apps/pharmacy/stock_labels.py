"""
Pharmacy stock labels: one small label per pack, stuck on the medicine in the pharmacy. No patient details.
Each label: medicine, strength, pack size, MRP (and our price if lower), GST %, batch, expiry and a barcode.

- The barcode is the batch's own barcode (for example the maker's barcode, typed or scanned at purchase).
  A batch without one gets a clinic code the first time its labels are printed: 12 digits starting with "29"
  (the range shops use for their own codes, so it never clashes with a maker's barcode).
- Scanning the label at pharmacy billing (prescription sale or counter sale) finds that exact batch.
- Which fields are printed follows the Medicine stock switches (batch, expiry, selling price).
- The look is in templates/documents/stock_label.html (SAFE TO EDIT there).
"""
import secrets
from base64 import b64encode
from io import BytesIO

from django.db import transaction
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError

from apps.organizations.services import branch_features

from .models import StockBatch

FORMATS = {  # width, height, space for the barcode (mm)
    "compact": ("50mm", "25mm", 44),
    "standard": ("75mm", "50mm", 66),
}
MAX_LABELS = 500


def new_code(branch) -> str:
    """A clinic barcode not used by any batch of this branch: 29 + 10 random digits."""
    while True:
        code = "29" + "".join(secrets.choice("0123456789") for _ in range(10))
        if not StockBatch.all_objects.filter(branch=branch, barcode=code).exists():
            return code


@transaction.atomic
def ensure_barcode(batch: StockBatch, user) -> str:
    """The batch's barcode; gives it a clinic code first if it has none."""
    if not batch.barcode:
        batch.barcode = new_code(batch.branch)
        batch.updated_by = user
        batch.save(update_fields=["barcode", "updated_by", "updated_at"])
    return batch.barcode


def barcode_svg(code: str, width_mm: float, height_mm: float) -> str:
    """Code 128 barcode as an SVG data URI, as wide as the label allows (bars not thinner than 0.19 mm)."""
    from barcode import Code128
    from barcode.writer import SVGWriter

    symbol = Code128(code, writer=SVGWriter())
    modules = sum(len(part) for part in symbol.build())
    quiet = 1.5
    module_width = max(0.19, min(0.33, (width_mm - 2 * quiet) / modules))
    out = BytesIO()
    symbol.write(out, {"module_width": module_width, "module_height": height_mm, "quiet_zone": quiet,
                       "write_text": False, "background": "white", "foreground": "black"})
    return "data:image/svg+xml;base64," + b64encode(out.getvalue()).decode()


def build_stock_labels(branch, user, wanted: list[tuple[StockBatch, int]], label_format: str) -> dict:
    """wanted: [(batch, copies)] -> the data for the template (one entry per printed label)."""
    if label_format not in FORMATS:
        raise ValidationError({"layout": "Choose compact or standard."})
    total = sum(copies for _, copies in wanted)
    if total < 1:
        raise ValidationError({"detail": "Choose how many labels to print."})
    if total > MAX_LABELS:
        raise ValidationError({"detail": f"At most {MAX_LABELS} labels at a time."})
    show = branch_features(branch)
    width, height, code_width = FORMATS[label_format]
    labels = []
    for batch, copies in wanted:
        medicine = batch.medicine
        code = ensure_barcode(batch, user)
        price = batch.sale_price
        label = {
            "medicine": medicine.name, "strength": medicine.strength, "pack": medicine.pack_size,
            "mrp": batch.mrp if show["pharmacy_selling_price"] else None,
            "price": price if show["pharmacy_selling_price"] and price is not None and price < batch.mrp else None,
            "gst": batch.gst_rate, "hsn": medicine.hsn_code,
            "batch": batch.batch_no if show["pharmacy_batch_tracking"] else "",
            "expiry": batch.expiry_date if show["pharmacy_expiry_tracking"] else None,
            "code": code,
            "barcode": barcode_svg(code, code_width, 7 if label_format == "compact" else 12),
        }
        labels.extend([label] * copies)
    return {"labels": labels, "clinic": branch.organization.name, "format": label_format,
            "width": width, "height": height}


def render_stock_labels(data) -> bytes:
    from weasyprint import HTML

    return HTML(string=render_to_string("documents/stock_label.html", data)).write_pdf()
