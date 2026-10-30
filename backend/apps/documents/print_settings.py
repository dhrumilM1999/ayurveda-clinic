"""
PDF settings: ONE place that decides how every print-out looks (Settings -> PDF settings).

What the owner can change (KEYS below) is saved in the PrintSetting table, but only the things that were changed.
resolve() merges them in this order (the last one wins):

    built-in defaults (= the look before this screen existed)
    -> whole clinic group, "all documents"
    -> this branch, "all documents"
    -> whole clinic group, one document type (e.g. only the prescription)
    -> this branch, one document type

SAFE TO EDIT: DEFAULTS (the starting look) and DOC_TYPES (which documents have which options).
ASK FIRST before changing resolve() or clean().
"""
import re

from django.core.exceptions import ValidationError

from .models import PrintSetting

PAPERS_DOCS = ["a4", "a5", "a6"]
PAPERS_BILLS = ["a4", "a5", "80mm", "58mm"]

# The look before the PDF settings screen existed. Empty text = nothing printed.
DEFAULTS = {
    "paper": "",                       # "" = the document's usual paper (DOC_TYPES[...]["paper"])
    "font_scale": 100,                 # text size in % (100 = as before)
    "accent_color": "#1f5c46",         # headings, lines and the clinic name
    "show_logo": True,                 # also needs "Logo on ..." in Settings -> Clinic
    "show_letterhead": True,           # clinic name, address and phone block at the top
    "header_text": "",                 # an extra line under the letterhead
    "footer_text": "",                 # an extra line at the very bottom (after "Footer line" of the branch)
    "show_signature": True,            # doctor's signature box / the bill's signatory box
    "show_qr": True,                   # "is this genuine?" QR (on bills: the UPI "scan to pay" QR)
    "show_duplicate_watermark": True,  # DUPLICATE COPY on reprints
    "language": "patient",             # "patient" = the patient's language, or en / gu / hi
    "margin_mm": None,                 # None = the paper's usual margin
    "show_gst_columns": True,          # HSN / batch / GST columns on bills
    "show_doctor_reg": True,           # doctor's registration number
    "terms_text": "",                  # terms and conditions printed on bills
    "thank_you_text": "",              # a line of thanks printed on bills
}

_PRINT = ["paper", "font_scale", "accent_color", "show_logo", "show_letterhead", "header_text", "footer_text",
          "show_signature", "show_qr", "show_duplicate_watermark", "language", "margin_mm", "show_doctor_reg"]
_BILL = ["paper", "font_scale", "accent_color", "show_logo", "show_letterhead", "header_text", "footer_text",
         "show_signature", "show_qr", "show_duplicate_watermark", "margin_mm", "show_gst_columns", "terms_text",
         "thank_you_text"]

# code -> what it is, usual paper, papers to choose from, and the options that make sense for it.
# "all" is not here: it has every option.
DOC_TYPES = {
    "prescription": {"label": "Prescription", "paper": "a5", "papers": PAPERS_DOCS, "keys": _PRINT},
    "follow_up_card": {"label": "Follow-up card", "paper": "a6", "papers": PAPERS_DOCS, "keys": _PRINT},
    "prakriti_report": {"label": "Prakriti report", "paper": "a4", "papers": PAPERS_DOCS, "keys": _PRINT},
    "certificate": {"label": "Certificate", "paper": "a4", "papers": PAPERS_DOCS, "keys": _PRINT},
    "therapy_plan": {"label": "Therapy plan", "paper": "a4", "papers": PAPERS_DOCS, "keys": _PRINT},
    "lab_order": {"label": "Lab test order", "paper": "a5", "papers": PAPERS_DOCS, "keys": _PRINT},
    "opd_bill": {"label": "OPD bill / receipt", "paper": "a4", "papers": PAPERS_BILLS, "keys": _BILL},
    "pharmacy_bill": {"label": "Pharmacy bill / counter sale", "paper": "a4", "papers": PAPERS_BILLS, "keys": _BILL},
    "credit_note": {"label": "Credit note", "paper": "a4", "papers": PAPERS_BILLS, "keys": _BILL},
    "medicine_label": {"label": "Medicine label", "paper": "", "papers": [], "keys": ["accent_color"]},
    "stock_label": {"label": "Pharmacy stock label", "paper": "", "papers": [], "keys": ["accent_color"]},
    "report": {"label": "Reports", "paper": "", "papers": [], "keys": ["font_scale", "accent_color", "header_text", "footer_text"]},
}
ALL_KEYS = list(DEFAULTS)

# the text size (pt) a document had before this screen existed, per paper
_BASE_PT = {
    "doc": {"a6": 8, "a5": 9, "a4": 10},
    "bill": {"a4": 9.5, "a5": 8.5, "80mm": 8.5, "58mm": 7},
}
_REPORT_PT = 9
_MARGIN_MM = {"a4": 12, "a5": 8, "a6": 6, "80mm": 3, "58mm": 2}
_TEXT_LIMITS = {"header_text": 200, "footer_text": 300, "terms_text": 600, "thank_you_text": 200}
_BOOLS = [k for k, v in DEFAULTS.items() if isinstance(v, bool)]


def is_bill(doc_type: str) -> bool:
    return doc_type in ("opd_bill", "pharmacy_bill", "credit_note")


def catalog() -> dict:
    """What the screen needs to build itself: documents, their papers and options, the defaults."""
    return {
        "defaults": DEFAULTS,
        "doc_types": [{"code": code, "label": info["label"], "paper": info["paper"], "papers": info["papers"], "keys": info["keys"]}
                      for code, info in DOC_TYPES.items()],
        "all_keys": ALL_KEYS,
    }


def clean(values: dict, doc_type: str = "all") -> dict:
    """Check what the screen sent; returns only valid, known keys (a key that is None / "" is dropped = inherit)."""
    if not isinstance(values, dict):
        raise ValidationError("Settings must be a set of values.")
    allowed = ALL_KEYS if doc_type == "all" else DOC_TYPES[doc_type]["keys"]
    out = {}
    for key, value in values.items():
        if key not in allowed:
            continue  # an option this document does not have: ignore it
        if value is None or (isinstance(value, str) and value == "" and key not in _TEXT_LIMITS):
            continue
        if key in _BOOLS:
            if not isinstance(value, bool):
                raise ValidationError({key: "Choose yes or no."})
        elif key == "font_scale":
            if isinstance(value, bool) or not isinstance(value, int) or not 70 <= value <= 150:
                raise ValidationError({key: "Text size must be between 70 and 150 percent."})
        elif key == "margin_mm":
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 30:
                raise ValidationError({key: "Margin must be between 0 and 30 mm."})
        elif key == "accent_color":
            if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                raise ValidationError({key: "Choose a colour like #1f5c46."})
            value = value.lower()
        elif key == "language":
            if value not in ("patient", "en", "gu", "hi"):
                raise ValidationError({key: "Choose the patient's language, English, Gujarati or Hindi."})
        elif key == "paper":
            if doc_type == "all":
                continue  # the paper is chosen per document, not for all
            if value not in DOC_TYPES[doc_type]["papers"]:
                raise ValidationError({key: "This paper size is not available for this document."})
        elif key in _TEXT_LIMITS:
            if not isinstance(value, str) or len(value) > _TEXT_LIMITS[key]:
                raise ValidationError({key: f"At most {_TEXT_LIMITS[key]} letters."})
            value = value.strip()
        out[key] = value
    return out


def _stored(organization_id, branch_id) -> dict:
    """{(branch_id or None, doc_type): values} of everything saved for this organization (and this branch)."""
    rows = PrintSetting.objects.filter(organization_id=organization_id)
    return {(r.branch_id, r.doc_type): r.values or {} for r in rows if r.branch_id in (None, branch_id)}


def resolve(branch, doc_type: str, drafts: dict | None = None) -> dict:
    """
    The final settings for one document of this branch (see the order at the top of this file).
    drafts: unsaved values from the screen, {(scope, doc_type): values} with scope "org" or "branch"; they replace
    the saved row of the same place (used by the live preview only).
    """
    stored = _stored(branch.organization_id, branch.id)
    for (scope, kind), values in (drafts or {}).items():
        stored[(None if scope == "org" else branch.id, kind)] = values
    merged = dict(DEFAULTS)
    for key in (( None, "all"), (branch.id, "all"), (None, doc_type), (branch.id, doc_type)):
        merged.update({k: v for k, v in stored.get(key, {}).items() if k in DEFAULTS and v is not None})
    return merged


def page_settings(branch, doc_type: str, paper: str | None = None, drafts: dict | None = None) -> dict:
    """(branch None = the built-in defaults, used by tests)
    
    resolve() plus what the templates need: the paper (asked one, else the saved one, else the usual one), the page
    size and margin, the base text size in pt, and a soft tint of the accent colour for table headings.
    """
    ps = resolve(branch, doc_type, drafts) if branch is not None else dict(DEFAULTS)
    info = DOC_TYPES.get(doc_type, {})
    ps["paper"] = paper or ps["paper"] or info.get("paper", "") or "a4"
    ps["doc_type"] = doc_type
    kind = "bill" if is_bill(doc_type) else "doc"
    ps["base_pt"] = round((_BASE_PT[kind].get(ps["paper"], 10) if doc_type != "report" else _REPORT_PT) * ps["font_scale"] / 100, 2)
    ps["margin"] = f"{ps['margin_mm']}mm" if ps["margin_mm"] is not None else f"{_MARGIN_MM.get(ps['paper'], 12)}mm"
    ps["accent_soft"] = _tint(ps["accent_color"])
    return ps


def _tint(color: str, strength: float = 0.9) -> str:
    """The accent colour mixed with white (for table heading backgrounds)."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(c + (255 - c) * strength):02x}" for c in (r, g, b))


def paper_defaults(branch) -> dict:
    """{doc_type: paper} that opens first in the print window of each document."""
    return {code: page_settings(branch, code)["paper"] for code, info in DOC_TYPES.items() if info["papers"]}


def save(*, organization, branch, doc_type: str, values: dict, user) -> dict:
    """Save one place (branch None = whole group). Empty values = reset that place (the row is removed)."""
    if doc_type != "all" and doc_type not in DOC_TYPES:
        raise ValidationError({"doc_type": "Unknown document."})
    values = clean(values, doc_type)
    row = PrintSetting.objects.filter(organization=organization, branch=branch, doc_type=doc_type).first()
    if not values:
        if row is not None:
            row.delete(user=user)
        return {}
    if row is None:
        PrintSetting.objects.create(organization=organization, branch=branch, doc_type=doc_type, values=values,
                                    created_by=user, updated_by=user)
    else:
        row.values, row.updated_by = values, user
        row.save(update_fields=["values", "updated_by", "updated_at"])
    return values
