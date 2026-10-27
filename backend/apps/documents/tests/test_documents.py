from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.documents.models import IssuedDocument
from apps.emr.models import Visit
from apps.medicines.models import Medicine
from apps.medicines.services import add_sample_medicines
from apps.patients.models import Patient
from apps.prescriptions.services import save_prescription
from conftest import client_for, make_user

TODAY = timezone.localdate()


@pytest.fixture
def visit(org, branch_a, doctor):
    patient = Patient.objects.create(organization=org, uhid="D-9", first_name="Mira", last_name="Joshi", gender="female",
                                     mobile="9876500011", preferred_language="gu")
    return Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, visit_date=TODAY,
                                follow_up_date=TODAY + timedelta(days=15))


@pytest.fixture
def rx(org, roles, visit, doctor):
    add_sample_medicines(org)
    medicine = Medicine.objects.get(organization=org, name="Triphala Churna")
    return save_prescription(visit, [{"medicine": medicine, "medicine_name": medicine.name, "dose": "3", "frequency": "1-0-1",
                                      "duration": 30}], "Take after food", doctor)


@pytest.mark.django_db
def test_detailed_prescription_has_the_full_checkup(doctor, pharmacist, branch_a, visit, rx):
    from django.template.loader import render_to_string

    from apps.audit.models import AuditLog
    from apps.documents.services import detailed_context, page_context, prescription_context

    visit.history_notes = "Pain since monsoon, worse in the morning"
    visit.complaints = [{"label": "Knee pain", "duration": 2, "duration_unit": "weeks", "severity": "moderate"}]
    visit.diagnoses = [{"label": "Sandhivata", "code": "SM-1", "kind": "final"}]
    visit.save()
    client = client_for(doctor, branch_a)
    url = f"/api/v1/documents/prescription/{rx.id}/"
    res = client.get(url, {"detail": "1", "size": "a4", "preview": "1", "lang": "en"})
    assert res.status_code == 200 and res["Content-Type"] == "application/pdf"
    assert AuditLog.objects.filter(action="view", changes__detailed=True).exists()
    # The detailed print-out shows medical history, so it needs "See full medical history"
    pharmacy = client_for(pharmacist, branch_a)
    assert pharmacy.get(url, {"detail": "1", "preview": "1"}).status_code == 403
    assert pharmacy.get(url, {"preview": "1"}).status_code == 200
    html = render_to_string("documents/prescription.html", {
        **prescription_context(rx, "en"), **detailed_context(rx, "en"), **page_context("a4")})
    for text in ("Check-up summary and prescription", "Pain since monsoon", "Knee pain", "for 2 weeks",
                 "Sandhivata", "SM-1", "Triphala Churna"):
        assert text in html


@pytest.mark.django_db
def test_pre_printed_pad_leaves_space_and_skips_letterhead(org_admin, branch_a, rx):
    from django.template.loader import render_to_string

    from apps.documents.services import pad_for, page_context, prescription_context

    client = client_for(org_admin, branch_a)
    res = client.patch(f"/api/v1/branches/{branch_a.id}/", {"print_on_pad": True, "pad_top_mm": 50, "pad_bottom_mm": 25},
                       format="json")
    assert res.status_code == 200, res.data
    assert client.patch(f"/api/v1/branches/{branch_a.id}/", {"pad_top_mm": 500}, format="json").status_code == 400
    branch_a.refresh_from_db()
    assert pad_for(branch_a, "a5") == {"top": "50mm", "bottom": "25mm", "image": ""}
    assert pad_for(branch_a, "a6") is None  # follow-up cards are never on the pad
    context = {**prescription_context(rx, "en"), **page_context("a5")}
    on_pad = render_to_string("documents/prescription.html", {**context, "pad": pad_for(branch_a, "a5")})
    normal = render_to_string("documents/prescription.html", context)
    assert "margin: 50mm 8mm 25mm" in on_pad and 'class="head"' not in on_pad
    assert 'class="head"' in normal
    assert client.get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": "1"}).status_code == 200


@pytest.mark.django_db
def test_clinic_logo_upload_and_where_it_prints(org_admin, receptionist, branch_a):
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    image = BytesIO()
    Image.new("RGB", (40, 20), "green").save(image, "PNG")
    client = client_for(org_admin, branch_a)
    res = client.post("/api/v1/organization/logo/", {"file": SimpleUploadedFile("logo.png", image.getvalue(), "image/png")},
                      format="multipart")
    assert res.status_code == 200 and res.data["has_logo"] is True
    assert client.get("/api/v1/organization/").data["has_logo"] is True
    assert client.get("/api/v1/organization/logo/").status_code == 200
    bad = client.post("/api/v1/organization/logo/", {"file": SimpleUploadedFile("x.png", b"not an image", "image/png")},
                      format="multipart")
    assert bad.status_code == 400
    # Only staff who may change settings can upload
    assert client_for(receptionist, branch_a).post("/api/v1/organization/logo/", {}, format="multipart").status_code == 403
    # Switching "logo on bills" off removes it from bills only
    assert client.patch("/api/v1/organization/", {"logo_on_bills": False}, format="json").status_code == 200
    from apps.billing.pdf import _logo
    from apps.documents.services import letterhead

    branch_a.organization.refresh_from_db()
    assert _logo(branch_a.organization) == "" and letterhead(branch_a, None)["logo"].startswith("data:image/png")
    assert client.delete("/api/v1/organization/logo/").data["has_logo"] is False


@pytest.mark.django_db
def test_prescription_pdf_number_duplicate_and_verify(doctor, branch_a, rx):
    client = client_for(doctor, branch_a)
    url = f"/api/v1/documents/prescription/{rx.id}/"
    res = client.get(url, {"preview": "1"})
    assert res.status_code == 200 and res["Content-Type"] == "application/pdf"
    doc = IssuedDocument.objects.get(kind="prescription", object_id=str(rx.id))
    assert doc.number.startswith("A/RX/") and doc.print_count == 0  # preview is not a print
    client.get(url, {"size": "a4"})
    client.get(url)
    doc.refresh_from_db()
    assert doc.print_count == 2  # the second print is the DUPLICATE COPY
    assert client.get(url, {"size": "huge"}).status_code == 400
    # Anyone with the QR code can check it is genuine - without medical details
    public = APIClient().get(f"/api/v1/verify/{doc.token}/")
    assert public.status_code == 200 and public.data["valid"] is True
    assert public.data["patient_initials"] == "M. J." and "medicine" not in str(public.data).lower()
    assert APIClient().get("/api/v1/verify/not-a-real-code/").status_code == 404


@pytest.mark.django_db
def test_who_can_print(org, roles, branch_a, rx, pharmacist):
    therapist = make_user(org, "ther9", {branch_a: roles["therapist"]})
    assert client_for(therapist, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/").status_code == 403
    assert client_for(pharmacist, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": "1"}).status_code == 200


@pytest.mark.django_db
def test_follow_up_card_and_prakriti_need_their_data(doctor, branch_a, visit):
    client = client_for(doctor, branch_a)
    assert client.get(f"/api/v1/documents/follow-up-card/{visit.id}/").status_code == 200
    assert client.get(f"/api/v1/documents/prakriti/{visit.id}/").status_code == 400  # no Prakriti answers yet
    visit.follow_up_date = None
    visit.save()
    assert client.get(f"/api/v1/documents/follow-up-card/{visit.id}/").status_code == 400


@pytest.mark.django_db
def test_certificate_create_print_cancel(doctor, branch_a, visit):
    client = client_for(doctor, branch_a)
    bad = client.post("/api/v1/certificates/", {"patient": str(visit.patient_id), "doctor": str(doctor.id), "kind": "medical"},
                      format="json")
    assert bad.status_code == 400  # rest dates needed
    res = client.post("/api/v1/certificates/", {
        "patient": str(visit.patient_id), "doctor": str(doctor.id), "visit": str(visit.id), "kind": "medical",
        "diagnosis": "Acute gastritis", "rest_from": str(TODAY), "rest_to": str(TODAY + timedelta(days=2))}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["number"].startswith("A/MC/")
    cert_id = res.data["id"]
    assert client.get(f"/api/v1/documents/certificate/{cert_id}/").status_code == 200
    token = IssuedDocument.objects.get(kind="certificate", object_id=cert_id).token
    assert client.post(f"/api/v1/certificates/{cert_id}/cancel/", {}, format="json").status_code == 400
    assert client.post(f"/api/v1/certificates/{cert_id}/cancel/", {"reason": "Wrong dates"}, format="json").status_code == 200
    public = APIClient().get(f"/api/v1/verify/{token}/").data
    assert public["valid"] is False and public["cancelled"] is True


@pytest.mark.django_db
def test_whatsapp_share_needs_consent(doctor, branch_a, rx):
    res = client_for(doctor, branch_a).post(f"/api/v1/documents/prescription/{rx.id}/whatsapp/")
    assert res.status_code == 200 and res.data["consent"] is False and res.data["link"] == ""


@pytest.mark.django_db
def test_ayurveda_case_sheet_design_is_one_a4_page(org_admin, doctor, branch_a, visit, rx):
    from django.template.loader import render_to_string

    from apps.documents.services import case_sheet_context, page_context, prescription_context

    branch_a.prescription_design = "ayurveda_pad"
    branch_a.print_subtitle = "Ayurveda & Panchakarma Hospital"
    branch_a.print_closed_note = "Sunday closed"
    branch_a.print_services = "Consulting | Panchakarma | Medicine"
    branch_a.save()
    visit.complaints = [{"label": "Cough", "duration": 3, "duration_unit": "months"}]
    visit.save()
    res = client_for(doctor, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": "1", "size": "a5"})
    assert res.status_code == 200
    branch_a.refresh_from_db()
    context = {**prescription_context(rx, "en"), **case_sheet_context(rx, "en"), **page_context("a4")}
    html = render_to_string("documents/prescription_ayurveda.html", context)
    for text in ("Ayurveda &amp; Panchakarma Hospital", "Sunday closed", "Panchakarma", "Agni", "Srotas", "Symptoms",
                 "Cough", "3 months", "Triphala Churna"):
        assert text in html
    assert [label for label, _ in context["case_lines"]][:2] == ["Agni", "Koshta"]
    # On the pre-printed pad the top (logo, doctor) and bottom (services, address) are left blank
    on_pad = render_to_string("documents/prescription_ayurveda.html", {**context, "pad": {"top": "60mm", "bottom": "40mm"}})
    assert 'class="head"' not in on_pad and 'class="services"' not in on_pad and "Cough" in on_pad


@pytest.mark.django_db
def test_ayurveda_case_sheet_fits_seven_medicines_on_one_page(doctor, branch_a, visit):
    """A busy prescription (7 medicines, notes, advice, next visit) must fit above the QR code and signature.
    The page hides anything that does not fit, so this checks the laid-out PDF, not just the HTML."""
    import base64
    from io import BytesIO

    from django.template.loader import render_to_string
    from PIL import Image
    from weasyprint import HTML

    from apps.documents.services import case_sheet_context, page_context, prescription_context

    # Everything the branch can print at the top and bottom, so the space left for medicines is the smallest
    branch_a.print_subtitle, branch_a.print_closed_note = "Ayurveda & Panchakarma Hospital", "Sunday closed"
    branch_a.letterhead_footer, branch_a.print_quote = "Time: 10 to 1 & 5 to 8", "आरोग्यं परमं भाग्यं"
    branch_a.print_services, branch_a.address = "Consulting | Panchakarma | Medicine", "12, Shanti Complex, C.G. Road"
    branch_a.save()
    visit.complaints = [{"label": f"Complaint {n}", "duration": 2, "duration_unit": "weeks"} for n in range(5)]
    visit.advice_notes = "No curd at night. Less fried food."
    visit.follow_up_notes = "Bring reports"
    visit.save()
    lines = [{"medicine": None, "medicine_name": f"Mahamanjishthadi Kwath Ashwagandha Ghan Vati No. {n}", "dose": "1", "frequency": "1-0-1",
              "duration": 15, "instructions": "Not on an empty stomach, with warm water after food"} for n in range(1, 8)]
    rx = save_prescription(visit, lines, "Take medicines regularly.\nWalk 15 minutes after meals.", doctor)
    context = {**prescription_context(rx, "gu"), **case_sheet_context(rx, "gu"), **page_context("a4")}
    # A square logo takes the most height at the top (up to 26 mm)
    square_logo = BytesIO()
    Image.new("RGB", (300, 300), "orange").save(square_logo, "PNG")
    context["logo"] = "data:image/png;base64," + base64.b64encode(square_logo.getvalue()).decode()
    document = HTML(string=render_to_string("documents/prescription_ayurveda.html", context)).render()
    assert len(document.pages) == 1

    # Walk the laid-out boxes (WeasyPrint's layout tree) and compare positions on the page
    content_bottom, sign_top = 0, None

    def walk(box):
        nonlocal content_bottom, sign_top
        element = getattr(box, "element", None)
        css_class = element.get("class") if element is not None else None
        if css_class in ("med", "after"):
            content_bottom = max(content_bottom, box.position_y + box.margin_height())
        if css_class == "sign-row" and sign_top is None:
            sign_top = box.position_y
        for child in getattr(box, "children", []):
            walk(child)

    walk(document.pages[0]._page_box)
    assert sign_top is not None and content_bottom <= sign_top


@pytest.mark.django_db(transaction=True)
def test_certificate_number_works_outside_a_test_transaction(doctor, branch_a, visit):
    """Tests normally run inside one big transaction, which hides a missing transaction.atomic. This one does not."""
    client = client_for(doctor, branch_a)
    res = client.post("/api/v1/certificates/", {
        "patient": str(visit.patient_id), "doctor": str(doctor.id), "kind": "medical", "diagnosis": "Fever",
        "rest_from": str(TODAY), "rest_to": str(TODAY + timedelta(days=1))}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["number"].endswith("00001")
