"""The clinic's letterhead picture: upload (PDF / PNG), writing space found by itself, printed behind prescriptions."""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageDraw

from apps.documents.services import pad_for
from apps.organizations.letterhead import picture_from_upload, suggest_margins
from conftest import client_for


def letterhead_png(width=827, height=1169) -> bytes:
    """A4 picture like the clinic's: a thin strip and a coloured bar at the top, a coloured footer band at the bottom."""
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, 10], fill=(0, 160, 80))
    draw.rectangle([0, 180, width, 214], fill=(25, 105, 60))     # bar at about 46 mm - 54 mm
    draw.rectangle([0, height - 46, width, height], fill=(0, 160, 80))  # footer band: last 11.7 mm
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def letterhead_pdf() -> bytes:
    from weasyprint import HTML

    return HTML(string="<style>@page{size:A4;margin:0}body{margin:0}.b{background:#196b3c;height:12mm;margin-top:50mm}"
                       ".f{position:fixed;bottom:0;left:0;right:0;height:12mm;background:#00a050}</style><div class=b></div><div class=f></div>").write_pdf()


def test_the_writing_space_is_found_from_the_bars_of_the_picture():
    top, bottom = suggest_margins(letterhead_png())
    assert 54 <= top <= 62 and 13 <= bottom <= 20
    # a picture with no bars: the usual pad values
    plain = io.BytesIO()
    Image.new("RGB", (827, 1169), "white").save(plain, format="PNG")
    assert suggest_margins(plain.getvalue()) == (45, 20)


def test_a_pdf_or_a_picture_becomes_one_a4_png_and_anything_else_is_refused():
    png = picture_from_upload(SimpleUploadedFile("lh.pdf", letterhead_pdf(), content_type="application/pdf"))
    image = Image.open(io.BytesIO(png))
    assert image.format == "PNG" and abs(image.size[1] / image.size[0] - 297 / 210) < 0.01
    assert Image.open(io.BytesIO(picture_from_upload(SimpleUploadedFile("lh.png", letterhead_png())))).format == "PNG"
    for bad in (SimpleUploadedFile("x.txt", b"hello"), SimpleUploadedFile("wide.png", letterhead_png(1169, 827))):
        with pytest.raises(Exception) as err:
            picture_from_upload(bad)
        assert "A4" in str(err.value) or "PDF" in str(err.value)


@pytest.mark.django_db
def test_upload_sets_the_space_prints_behind_prescriptions_and_can_be_removed(org_admin, receptionist, branch_a):
    admin = client_for(org_admin, branch_a)
    url = f"/api/v1/branches/{branch_a.id}/letterhead-image/"
    assert admin.get(url).status_code == 404
    res = admin.post(url, {"file": SimpleUploadedFile("lh.pdf", letterhead_pdf(), content_type="application/pdf")}, format="multipart")
    assert res.status_code == 200 and res.data["has_letterhead_image"] and res.data["pad_top_mm"] >= 50
    branch_a.refresh_from_db()
    assert branch_a.letterhead_image and branch_a.pad_top_mm == res.data["pad_top_mm"]
    assert admin.get(url).status_code == 200 and admin.get(f"/api/v1/branches/{branch_a.id}/").data["has_letterhead_image"] is True

    # A4 gets the picture behind the page; A5 gets the same picture, with the free space scaled to A5; A6 never
    pad = pad_for(branch_a, "a4")
    assert pad and pad["image"].startswith("data:image/png;base64,") and pad["top"] == f"{branch_a.pad_top_mm}mm"
    small = pad_for(branch_a, "a5")
    assert small["image"] == pad["image"] and float(small["top"][:-2]) == round(branch_a.pad_top_mm * 0.70711, 1)
    assert pad_for(branch_a, "a6") is None
    branch_a.letterhead_picture_on = False                     # switched off: printing on the clinic's own paper
    assert pad_for(branch_a, "a4") is None
    branch_a.letterhead_picture_on = True

    # others cannot change it
    assert client_for(receptionist, branch_a).post(url, {"file": SimpleUploadedFile("a.png", letterhead_png())}, format="multipart").status_code == 403
    assert client_for(receptionist, branch_a).delete(url).status_code == 403
    assert admin.post(url, {}, format="multipart").status_code == 400
    assert admin.delete(url).status_code == 200 and admin.get(url).status_code == 404


@pytest.mark.django_db
def test_the_prescription_pdf_is_made_with_the_letterhead_picture(org_admin, doctor, branch_a, settings, tmp_path):
    from apps.emr.models import Visit
    from apps.patients.models import Patient
    from apps.prescriptions.services import save_prescription
    from django.utils import timezone

    settings.MEDIA_ROOT = tmp_path
    admin = client_for(org_admin, branch_a)
    admin.post(f"/api/v1/branches/{branch_a.id}/letterhead-image/", {"file": SimpleUploadedFile("lh.png", letterhead_png())}, format="multipart")
    patient = Patient.objects.create(organization=branch_a.organization, uhid="9", first_name="Kamla", last_name="Shah", gender="female", mobile="9825011111")
    visit = Visit.objects.create(organization=branch_a.organization, branch=branch_a, patient=patient, doctor=doctor, visit_date=timezone.localdate())
    rx = save_prescription(visit, [{"medicine": None, "medicine_name": "Ginger tea"}], "", doctor)
    with_picture = client_for(doctor, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": 1, "size": "a4"})
    assert with_picture.status_code == 200 and with_picture.content[:4] == b"%PDF"
    branch_a.refresh_from_db()
    branch_a.letterhead_picture_on = False
    branch_a.save(update_fields=["letterhead_picture_on"])
    without = client_for(doctor, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": 1, "size": "a4"})
    assert len(with_picture.content) > len(without.content)  # the picture is inside the PDF
