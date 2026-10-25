"""
The clinic's letterhead as a picture (Settings -> Branch details). The owner uploads the A4 letterhead file
(a PDF from the printer / designer, or a PNG / JPG); prescriptions are then printed on top of it, so the preview and
the PDF look exactly like that file.

  picture_from_upload(upload)  PDF / PNG / JPG -> one A4 PNG picture (bytes)
  suggest_margins(png_bytes)   where the empty writing area starts and ends (mm from the top / bottom of the page)
"""
import io

from rest_framework.exceptions import ValidationError

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
A4_RATIO = 297 / 210
RENDER_DPI = 200
MAX_WIDTH_PX = 1654  # A4 at 200 dpi: sharp on screen and on a printer, and not heavy
PAGE_HEIGHT_MM = 297.0


def picture_from_upload(upload) -> bytes:
    """Return the letterhead as PNG bytes. Raises a friendly ValidationError for anything that is not an A4 portrait page."""
    from PIL import Image

    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError({"file": "The file must be smaller than 12 MB."})
    head = upload.read(8)
    upload.seek(0)
    try:
        if head.startswith(b"%PDF"):
            import pypdfium2

            document = pypdfium2.PdfDocument(upload.read())
            if len(document) < 1:
                raise ValueError
            image = document[0].render(scale=RENDER_DPI / 72).to_pil()
        else:
            image = Image.open(upload)
            image.load()
            if image.format not in ("PNG", "JPEG"):
                raise ValueError
    except Exception:  # noqa: BLE001 - whatever is wrong with the file, the message is the same
        raise ValidationError({"file": "Use the letterhead as a PDF, PNG or JPG file (one A4 page)."})
    image = image.convert("RGB")
    width, height = image.size
    if abs(height / width - A4_RATIO) > 0.06:
        raise ValidationError({"file": "The letterhead must be one A4 page, standing (portrait)."})
    if width > MAX_WIDTH_PX:
        image = image.resize((MAX_WIDTH_PX, round(MAX_WIDTH_PX * height / width)), Image.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _runs(flags):
    """[(first_row, last_row)] of consecutive True values."""
    runs, start = [], None
    for index, flag in enumerate(flags):
        if flag and start is None:
            start = index
        if not flag and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(flags) - 1))
    return runs


def suggest_margins(png_bytes: bytes) -> tuple[int, int]:
    """
    Where the writing area is: below the last coloured band in the top part of the page and above the first coloured band in
    the bottom part (a band = rows that are coloured across at least 90 % of the width). Returns (top_mm, bottom_mm)
    with 3 mm of air. Falls back to 45 / 20 mm when the picture has no such bands.
    """
    from PIL import Image

    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    small = image.resize((100, 141), Image.BILINEAR)
    pixels = small.load()
    rows = 141
    banded = [sum(1 for x in range(100) if min(pixels[x, y]) < 200) >= 90 for y in range(rows)]
    runs = _runs(banded)
    top_runs = [r for r in runs if r[1] < rows * 0.45]
    bottom_runs = [r for r in runs if r[0] > rows * 0.8]
    top = round((top_runs[-1][1] + 1) / rows * PAGE_HEIGHT_MM + 3) if top_runs else 45
    bottom = round((rows - bottom_runs[0][0]) / rows * PAGE_HEIGHT_MM + 3) if bottom_runs else 20
    return min(max(top, 0), 120), min(max(bottom, 0), 80)
