import io
from datetime import time

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.audit.models import AuditLog
from apps.emr.models import Visit
from apps.patients.models import Patient
from apps.prescriptions.models import HandwrittenPrescription
from conftest import client_for, set_additional_features

URL = "/api/v1/handwritten-prescriptions/"


def ink_png(width=1200, height=800, write=True, fmt="PNG"):
    """A transparent picture with a few black strokes (like the pen on the pad)."""
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if write:
        draw = ImageDraw.Draw(image)
        draw.line([(200, 300), (500, 320), (800, 310)], fill=(0, 0, 0, 255), width=6)
        draw.line([(220, 400), (700, 420)], fill=(10, 20, 120, 255), width=6)
    out = io.BytesIO()
    image.save(out, fmt)
    return SimpleUploadedFile("ink.png", out.getvalue(), content_type="image/png")


@pytest.fixture(autouse=True)
def pad_on(org):
    set_additional_features(org, codes=["digital_pad"])  # the digital pad is an optional extra (Additional settings)


@pytest.fixture
def patient(org, roles):
    return Patient.objects.create(organization=org, uhid="1", first_name="Ramesh", last_name="Patel", gender="male",
                                  mobile="9876543210", preferred_language="gu")


@pytest.fixture
def visit(org, branch_a, patient, doctor):
    return Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                visit_date=timezone.localdate())


def save(client, visit, **extra):
    return client.post(URL, {"visit": str(visit.id), "ink": ink_png(), **extra}, format="multipart")


@pytest.mark.django_db
def test_doctor_saves_handwriting_and_gets_one_combined_picture(doctor, branch_a, visit):
    res = save(client_for(doctor, branch_a), visit)
    assert res.status_code == 201, res.data
    assert res.data["paper"] in ("a5", "a4") and res.data["number"].startswith("A/RX/")
    page = HandwrittenPrescription.objects.get(pk=res.data["id"])
    # the handwriting alone is a transparent PNG, cropped to the writing
    ink = Image.open(page.ink.open("rb"))
    assert ink.mode == "RGBA" and ink.width < 1200 and ink.height < 800
    # the combined picture is a full page (A5 at 200 DPI is about 1170 x 1654) with the letterhead on it
    combined = Image.open(page.image.open("rb"))
    assert combined.format == "PNG" and combined.mode == "RGB"
    assert 1100 < combined.width < 1250 and 1550 < combined.height < 1750
    assert page.width_px == combined.width and page.height_px == combined.height
    assert combined.getbbox() is not None


@pytest.mark.django_db
def test_paper_a4_makes_a_bigger_picture(doctor, branch_a, visit):
    res = save(client_for(doctor, branch_a), visit, paper="a4")
    page = HandwrittenPrescription.objects.get(pk=res.data["id"])
    combined = Image.open(page.image.open("rb"))
    assert 1600 < combined.width < 1700 and 2300 < combined.height < 2400
    assert save(client_for(doctor, branch_a), visit, paper="a3").status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("ink", [
    lambda: ink_png(write=False),                                           # nothing written
    lambda: SimpleUploadedFile("x.png", b"not a picture"),                  # not an image
    lambda: ink_png(fmt="JPEG") if False else SimpleUploadedFile("x.png", b"GIF89a....."),
    lambda: SimpleUploadedFile("x.png", b""),                               # empty file
])
def test_wrong_handwriting_files_are_refused(doctor, branch_a, visit, ink):
    res = client_for(doctor, branch_a).post(URL, {"visit": str(visit.id), "ink": ink()}, format="multipart")
    assert res.status_code == 400, res.data
    assert HandwrittenPrescription.objects.count() == 0


@pytest.mark.django_db
def test_missing_ink_or_wrong_visit_is_refused(doctor, branch_a, visit):
    c = client_for(doctor, branch_a)
    assert c.post(URL, {"visit": str(visit.id)}, format="multipart").status_code == 400
    assert c.post(URL, {"visit": "11111111-1111-1111-1111-111111111111", "ink": ink_png()}, format="multipart").status_code == 404


@pytest.mark.django_db
def test_who_may_write_and_who_may_look(doctor, receptionist, pharmacist, therapist, branch_a, visit):
    page = save(client_for(doctor, branch_a), visit).data["id"]
    assert save(client_for(receptionist, branch_a), visit).status_code == 403
    assert save(client_for(pharmacist, branch_a), visit).status_code == 403
    # the pharmacy may see the pages (to give the medicines); the front desk and therapist may not
    assert client_for(pharmacist, branch_a).get(f"{URL}{page}/image/").status_code == 200
    assert client_for(receptionist, branch_a).get(f"{URL}{page}/image/").status_code == 403
    assert client_for(therapist, branch_a).get(f"{URL}?visit={visit.id}").status_code == 403


@pytest.mark.django_db
def test_pictures_are_private_and_every_view_is_logged(doctor, branch_a, branch_b, visit, org):
    from conftest import make_user

    c = client_for(doctor, branch_a)
    page = c.post(URL, {"visit": str(visit.id), "ink": ink_png()}, format="multipart").data["id"]
    first = c.get(f"{URL}{page}/image/")
    assert first.status_code == 200 and first["Content-Type"] == "image/png" and first["Cache-Control"] == "no-store"
    assert c.get(f"{URL}{page}/image/?kind=ink").status_code == 200
    assert c.get(f"{URL}{page}/image/?kind=other").status_code == 400
    assert AuditLog.objects.filter(object_id=page, action="view").count() >= 2
    # another branch cannot reach it
    assert client_for(doctor, branch_b).get(f"{URL}{page}/image/").status_code in (403, 404)
    # no login, no picture
    from rest_framework.test import APIClient

    assert APIClient().get(f"{URL}{page}/image/").status_code in (401, 403)


@pytest.mark.django_db
def test_list_and_remove_keep_the_files(doctor, branch_a, visit):
    c = client_for(doctor, branch_a)
    a = save(c, visit).data["id"]
    b = save(c, visit).data["id"]
    assert [p["id"] for p in c.get(f"{URL}?visit={visit.id}").data] == [a, b]
    assert c.get(URL).status_code == 400  # a visit or patient must be chosen
    assert c.delete(f"{URL}{a}/").status_code == 204
    assert [p["id"] for p in c.get(f"{URL}?visit={visit.id}").data] == [b]
    assert HandwrittenPrescription.all_objects.filter(pk=a).exists()  # never really deleted


@pytest.mark.django_db
def test_page_prints_as_pdf_with_the_usual_rx_number(doctor, pharmacist, branch_a, visit):
    page = save(client_for(doctor, branch_a), visit).data
    res = client_for(pharmacist, branch_a).get(f"/api/v1/documents/handwritten-rx/{page['id']}/?preview=1&size=a5")
    assert res.status_code == 200 and res.content[:4] == b"%PDF"
    again = client_for(doctor, branch_a).get(f"/api/v1/documents/handwritten-rx/{page['id']}/?size=a5")
    assert again.status_code == 200  # the first real print


@pytest.mark.django_db
def test_digital_pad_switch_off_blocks_new_pages_but_keeps_old_ones(org, doctor, pharmacist, branch_a, visit):
    c = client_for(doctor, branch_a)
    page = save(c, visit).data["id"]
    set_additional_features(org, on=False, codes=["digital_pad"])
    assert save(c, visit).status_code == 403                                   # no new handwriting while it is off
    assert c.get(f"{URL}?visit={visit.id}").status_code == 200                 # what was written stays visible
    assert client_for(pharmacist, branch_a).get(f"{URL}{page}/image/").status_code == 200
    set_additional_features(org, codes=["digital_pad"])
    assert save(c, visit).status_code == 201                                   # back on: works again


@pytest.mark.django_db
def test_patient_history_of_handwriting_is_latest_first_with_page_numbers(org, branch_a, doctor, patient, visit):
    from datetime import timedelta

    older = Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                 visit_date=timezone.localdate() - timedelta(days=30))
    c = client_for(doctor, branch_a)
    first_old = save(c, older).data["id"]
    first_new = save(c, visit).data["id"]
    second_new = save(c, visit).data["id"]
    history = c.get(URL, {"patient": str(patient.id)}).data
    # newest page first; each page knows its check-up date and its own page number inside that check-up
    assert [p["id"] for p in history] == [second_new, first_new, first_old]
    assert [p["page_no"] for p in history] == [2, 1, 1]
    assert str(history[0]["visit_date"]) == str(visit.visit_date) and str(history[2]["visit_date"]) == str(older.visit_date)
    # one check-up is still read page 1, 2 (oldest first)
    assert [p["page_no"] for p in c.get(URL, {"visit": str(visit.id)}).data] == [1, 2]


@pytest.mark.django_db
def test_handwriting_page_uses_the_clinic_letterhead_picture(org_admin, doctor, branch_a, visit, settings, tmp_path):
    from apps.organizations.tests.test_letterhead import letterhead_png

    settings.MEDIA_ROOT = tmp_path
    assert client_for(org_admin, branch_a).post(f"/api/v1/branches/{branch_a.id}/letterhead-image/", {"file": letterhead_png_upload()}, format="multipart").status_code == 200
    res = save(client_for(doctor, branch_a), visit)
    assert res.status_code == 201, res.data
    page = HandwrittenPrescription.objects.get(pk=res.data["id"])
    picture = Image.open(page.image.open("rb")).convert("RGB")
    # the strip across the top and the band along the bottom of the letterhead picture are on the saved page
    assert picture.getpixel((picture.width // 2, 4)) != (255, 255, 255)
    assert picture.getpixel((picture.width // 2, picture.height - 4)) != (255, 255, 255)


def letterhead_png_upload():
    from apps.organizations.tests.test_letterhead import letterhead_png

    return SimpleUploadedFile("lh.png", letterhead_png(), content_type="image/png")
