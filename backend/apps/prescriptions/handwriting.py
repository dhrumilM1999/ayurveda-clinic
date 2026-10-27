"""
Handwritten prescriptions: the doctor writes on the digital pad; the software keeps
1. the handwriting alone (transparent PNG), and
2. ONE combined picture: clinic letterhead + patient details + the handwriting + doctor signature and QR.
The combined picture is made the same way as every other print-out (HTML template -> PDF -> picture), so it follows
Settings -> PDF settings (paper, colour, letterhead on/off, pre-printed pad) and prints later with the same look.
"""
import io

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image
from rest_framework.exceptions import ValidationError

from .models import HandwrittenPrescription

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_SIDE = 4000          # pixels, handwriting is scaled down above this
KEEP_PADDING = 16        # empty border kept around the writing (pixels)
PAPERS = ("a5", "a4")
PICTURE_DPI = 200        # sharpness of the combined picture (A5 = about 1170 x 1650 px)


def clean_ink(upload) -> tuple[bytes, int, int]:
    """
    The handwriting as a tidy transparent PNG: refuses anything that is not a real picture, empty pages and giant
    files; crops the empty space around the writing; scales it down if huge.
    """
    if upload is None:
        raise ValidationError({"ink": "There is no handwriting to save."})
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError({"ink": "The handwriting picture is too large."})
    try:
        image = Image.open(io.BytesIO(upload.read()))
        image.load()
    except Exception:
        raise ValidationError({"ink": "This is not a real picture."})
    if image.format != "PNG":
        raise ValidationError({"ink": "The handwriting must be a PNG picture."})
    if image.width > 12000 or image.height > 12000:
        raise ValidationError({"ink": "The picture is too large."})
    image = image.convert("RGBA")
    box = image.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if box is None:
        raise ValidationError({"ink": "Nothing is written yet."})
    left, top, right, bottom = box
    box = (max(left - KEEP_PADDING, 0), max(top - KEEP_PADDING, 0),
           min(right + KEEP_PADDING, image.width), min(bottom + KEEP_PADDING, image.height))
    image = image.crop(box)
    if max(image.size) > MAX_SIDE:
        image.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue(), image.width, image.height


def render_picture(pdf_bytes: bytes) -> tuple[bytes, int, int]:
    """First page of a PDF as a PNG picture."""
    import pypdfium2 as pdfium

    page = pdfium.PdfDocument(pdf_bytes)[0]
    picture = page.render(scale=PICTURE_DPI / 72).to_pil().convert("RGB")
    out = io.BytesIO()
    picture.save(out, "PNG", optimize=True)
    return out.getvalue(), picture.width, picture.height


def build_combined(handwriting: HandwrittenPrescription) -> bytes:
    """(Re)make the combined picture of one handwritten page and return the PNG bytes."""
    from weasyprint import HTML

    from apps.documents.print_settings import page_settings
    from apps.documents.services import _qr, handwritten_rx_context, issue, language_of, render_html, verify_url

    branch = handwriting.branch
    ps = page_settings(branch, "prescription", handwriting.paper)
    size = handwriting.paper
    doc = issue("handwritten_rx", handwriting.id, branch=branch, patient=handwriting.patient, doctor=handwriting.doctor,
                issued_on=handwriting.visit.visit_date, series="RX")
    handwriting.number = doc.number
    lang = language_of(handwriting.patient, None, ps)
    # The clinic's own letterhead picture (Settings -> Branch details) is used when it is switched on; otherwise the
    # software draws its own letterhead
    from apps.documents.services import pad_for

    pad = pad_for(branch, size)
    pad = pad if pad and pad.get("image") else None
    context = {
        **handwritten_rx_context(handwriting, lang),
        "number": doc.number, "duplicate": False, "qr": _qr(verify_url(doc)), "is_cancelled": False,
        # The saved picture is the digital copy: it ALWAYS carries the letterhead. (Printing later on the clinic pre-printed
        # pad still leaves the letterhead out, see documents/views.py.)
        "pad": pad,
    }
    pdf = HTML(string=render_html("prescription_handwritten.html", size, context, ps)).write_pdf()
    png, width, height = render_picture(pdf)
    handwriting.width_px, handwriting.height_px = width, height
    return png


@transaction.atomic
def save_handwriting(visit, user, ink_upload, paper: str | None = None) -> HandwrittenPrescription:
    """Keep the handwriting and make the combined picture for this check-up."""
    from apps.documents.print_settings import page_settings

    from .models import Prescription

    if paper is not None and paper not in PAPERS:
        raise ValidationError({"paper": "Choose A5 (half A4) or A4."})
    if paper is None:
        paper = page_settings(visit.branch, "prescription")["paper"]
        paper = paper if paper in PAPERS else "a5"
    ink_bytes, _, _ = clean_ink(ink_upload)
    handwriting = HandwrittenPrescription(
        organization_id=visit.organization_id, branch=visit.branch, visit=visit, patient=visit.patient,
        doctor=visit.doctor, prescription=Prescription.objects.filter(visit=visit).first(), paper=paper,
        created_by=user, updated_by=user,
    )
    handwriting.ink.save("ink.png", ContentFile(ink_bytes), save=False)
    handwriting.save()
    combined = build_combined(handwriting)
    handwriting.image.save("page.png", ContentFile(combined), save=False)
    handwriting.save()
    return handwriting
