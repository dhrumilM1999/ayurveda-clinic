"""PDF settings: merge order, defaults unchanged, every document honours the settings, API and live preview."""
import pytest

from apps.billing.tests.test_opd import appointment, consultation_line, fee, patient  # noqa: F401  (fixtures)
from apps.documents import services
from apps.documents.models import IssuedDocument, PrintSetting
from apps.documents.print_settings import DEFAULTS, DOC_TYPES, page_settings, resolve, save
from apps.documents.tests.test_documents import rx, visit  # noqa: F401  (fixtures)
from conftest import client_for

RED = "#8a1c1c"


@pytest.fixture
def seen(monkeypatch):
    """The HTML of every document made during the test."""
    html = []
    real = services.render_html
    monkeypatch.setattr(services, "render_html", lambda *a, **k: html.append(real(*a, **k)) or html[-1])
    import apps.billing.pdf as bill_pdf

    real_render = bill_pdf.render_to_string
    monkeypatch.setattr(bill_pdf, "render_to_string", lambda *a, **k: html.append(real_render(*a, **k)) or html[-1])
    return html


def put(client, scope, doc_type, values):
    return client.put("/api/v1/print-settings/", {"scope": scope, "doc_type": doc_type, "values": values}, format="json")


@pytest.mark.django_db
def test_defaults_are_the_old_look(branch_a):
    assert resolve(branch_a, "prescription") == DEFAULTS
    a5 = page_settings(branch_a, "prescription", "a5")
    assert (a5["paper"], a5["base_pt"], a5["margin"]) == ("a5", 9, "8mm")
    assert page_settings(branch_a, "opd_bill")["paper"] == "a4" and page_settings(branch_a, "opd_bill")["base_pt"] == 9.5
    assert page_settings(branch_a, "follow_up_card")["paper"] == "a6"
    assert page_settings(branch_a, "opd_bill", "58mm")["base_pt"] == 7


@pytest.mark.django_db
def test_default_prescription_html_has_no_extra_parts(doctor, branch_a, rx, seen):  # noqa: F811
    res = client_for(doctor, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": "1", "size": "a5"})
    assert res.status_code == 200
    html = seen[-1]
    assert "font-size: 9.0pt" in html or "font-size: 9pt" in html
    assert "margin: 8mm" in html and "#1f5c46" in html
    assert "footer-line" not in html.split("<body>")[1]  # no extra footer unless the owner writes one


@pytest.mark.django_db
def test_merge_order_branch_and_document_beat_group_and_all(org, branch_a, org_admin):
    save(organization=org, branch=None, doc_type="all", values={"accent_color": "#111111", "font_scale": 110}, user=org_admin)
    save(organization=org, branch=None, doc_type="prescription", values={"accent_color": "#222222"}, user=org_admin)
    save(organization=org, branch=branch_a, doc_type="all", values={"accent_color": "#333333"}, user=org_admin)
    # group + document type beats branch + all documents
    assert resolve(branch_a, "prescription")["accent_color"] == "#222222"
    assert resolve(branch_a, "certificate")["accent_color"] == "#333333"   # branch beats group for "all"
    assert resolve(branch_a, "certificate")["font_scale"] == 110           # inherited from the group
    save(organization=org, branch=branch_a, doc_type="prescription", values={"accent_color": "#444444"}, user=org_admin)
    assert resolve(branch_a, "prescription")["accent_color"] == "#444444"
    drafts = {("branch", "prescription"): {"accent_color": "#555555"}}
    assert resolve(branch_a, "prescription", drafts)["accent_color"] == "#555555"  # unsaved draft wins in the preview


@pytest.mark.django_db
def test_saved_settings_change_the_prescription_pdf(org_admin, doctor, branch_a, rx, seen):  # noqa: F811
    admin = client_for(org_admin, branch_a)
    assert put(admin, "org", "all", {"accent_color": RED, "font_scale": 120, "footer_text": "Open 10 to 6",
                                     "show_qr": False, "show_signature": False}).status_code == 200
    assert put(admin, "org", "prescription", {"paper": "a4", "header_text": "Since 1990"}).status_code == 200
    res = client_for(doctor, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": "1"})  # no ?size
    assert res.status_code == 200
    html = seen[-1]
    assert RED in html and "font-size: 12.0pt" in html and "@page { size: 210mm 297mm" in html  # saved paper = A4
    assert "Open 10 to 6" in html and "Since 1990" in html
    assert 'class="qr"><img' not in html and 'class="sign"' not in html
    # The paper asked for in the URL still wins
    client_for(doctor, branch_a).get(f"/api/v1/documents/prescription/{rx.id}/", {"preview": "1", "size": "a5"})
    assert "@page { size: 148mm 210mm" in seen[-1]


@pytest.mark.django_db
def test_duplicate_watermark_and_fixed_language(org_admin, doctor, branch_a, rx, seen):  # noqa: F811
    from apps.documents.words import words_for

    admin, doc = client_for(org_admin, branch_a), client_for(doctor, branch_a)
    url = f"/api/v1/documents/prescription/{rx.id}/"
    doc.get(url)  # first print
    doc.get(url)  # reprint -> DUPLICATE COPY
    assert 'class="watermark"' in seen[-1]
    put(admin, "org", "all", {"show_duplicate_watermark": False, "language": "hi"})
    doc.get(url)
    assert 'class="watermark"' not in seen[-1]
    # the patient speaks Gujarati; the setting says Hindi -> Hindi words, unless ?lang= asks otherwise
    assert words_for("hi")["doctor_sign"] in seen[-1] and words_for("gu")["doctor_sign"] not in seen[-1]
    doc.get(url, {"lang": "gu"})
    assert words_for("gu")["doctor_sign"] in seen[-1]


@pytest.mark.django_db
def test_bill_settings_change_the_bill_pdf(org_admin, receptionist, branch_a, appointment, fee, seen):  # noqa: F811
    desk = client_for(receptionist, branch_a)
    bill = desk.post("/api/v1/opd-bills/charge/", {"appointment": str(appointment.id), "lines": [consultation_line(300)]}, format="json").data
    url = f"/api/v1/invoices/{bill['id']}/pdf/"
    desk.get(url, {"preview": "1"})
    plain = seen[-1]
    assert "Thank you. Please keep this bill" in plain and "HSN/SAC" in plain and "9.5pt" in plain
    admin = client_for(org_admin, branch_a)
    put(admin, "org", "opd_bill", {"paper": "80mm", "thank_you_text": "Get well soon", "terms_text": "No refund after 7 days",
                                   "show_gst_columns": False, "accent_color": RED, "font_scale": 90})
    desk.get(url, {"preview": "1"})  # no ?size: the saved 80mm
    html = seen[-1]
    assert "Get well soon" in html and "No refund after 7 days" in html and "Thank you. Please keep" not in html
    assert RED in html and "@page { size: 80mm" in html
    desk.get(url, {"preview": "1", "size": "a4"})
    assert "HSN/SAC" not in seen[-1] and "Get well soon" in seen[-1]


@pytest.mark.django_db
def test_paper_defaults_for_the_print_windows(org_admin, receptionist, branch_a):
    assert client_for(receptionist, branch_a).get("/api/v1/print-settings/paper-defaults/").data["prescription"] == "a5"
    put(client_for(org_admin, branch_a), "org", "prescription", {"paper": "a4"})
    data = client_for(receptionist, branch_a).get("/api/v1/print-settings/paper-defaults/").data
    assert data["prescription"] == "a4" and data["opd_bill"] == "a4" and "medicine_label" not in data


@pytest.mark.django_db
def test_only_settings_managers_and_bad_values_are_refused(org_admin, receptionist, branch_a):
    desk = client_for(receptionist, branch_a)
    assert desk.get("/api/v1/print-settings/").status_code == 403
    assert put(desk, "org", "all", {"accent_color": RED}).status_code == 403
    assert desk.post("/api/v1/print-settings/preview/", {"doc_type": "prescription"}, format="json").status_code == 403
    admin = client_for(org_admin, branch_a)
    for bad in ({"accent_color": "red"}, {"font_scale": 400}, {"margin_mm": -1}, {"language": "fr"}, {"footer_text": "x" * 400}):
        assert put(admin, "org", "all", bad).status_code == 400, bad
    assert put(admin, "org", "prescription", {"paper": "80mm"}).status_code == 400
    assert put(admin, "org", "nonsense", {}).status_code == 400
    # an option a document does not have is ignored (a label has no footer text)
    assert put(admin, "org", "medicine_label", {"footer_text": "x", "accent_color": RED}).data["values"] == {"accent_color": RED}


@pytest.mark.django_db
def test_save_get_and_reset(org, org_admin, branch_a):
    admin = client_for(org_admin, branch_a)
    put(admin, "branch", "all", {"accent_color": RED})
    data = admin.get("/api/v1/print-settings/").data
    assert data["saved"]["branch"]["all"] == {"accent_color": RED} and data["saved"]["org"] == {}
    assert {d["code"] for d in data["doc_types"]} == set(DOC_TYPES) and data["defaults"]["font_scale"] == 100
    put(admin, "branch", "all", {})  # reset
    assert admin.get("/api/v1/print-settings/").data["saved"]["branch"] == {}
    assert PrintSetting.objects.count() == 0
    assert PrintSetting.all_objects.count() == 1  # kept (soft delete), like every other table
    put(admin, "branch", "all", {"accent_color": RED})  # the same place can be saved again
    assert PrintSetting.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("doc_type", list(DOC_TYPES))
def test_preview_of_every_document_with_a_sample(org_admin, branch_a, doc_type):
    admin = client_for(org_admin, branch_a)
    res = admin.post("/api/v1/print-settings/preview/", {
        "doc_type": doc_type, "drafts": {"all": {"accent_color": RED}}, "duplicate": True}, format="json")
    assert res.status_code == 200, getattr(res, "data", res.content[:300])
    assert res["Content-Type"] == "application/pdf" and res.content.startswith(b"%PDF")
    assert res["X-Preview-Source"] == "sample"
    assert PrintSetting.objects.count() == 0 and not IssuedDocument.objects.exists()  # nothing was saved


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["en", "gu", "hi"])
def test_preview_of_the_case_sheet_and_languages(org_admin, branch_a, lang):
    branch_a.prescription_design = "ayurveda_pad"
    branch_a.save()
    res = client_for(org_admin, branch_a).post("/api/v1/print-settings/preview/", {"doc_type": "prescription", "lang": lang}, format="json")
    assert res.status_code == 200 and res.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_preview_uses_unsaved_settings_and_the_newest_real_record(org_admin, doctor, branch_a, rx, seen):  # noqa: F811
    admin = client_for(org_admin, branch_a)
    res = admin.post("/api/v1/print-settings/preview/", {
        "doc_type": "prescription", "paper": "a4", "drafts": {"prescription": {"accent_color": RED, "footer_text": "DRAFT FOOTER"}}}, format="json")
    assert res.status_code == 200 and res["X-Preview-Source"] == "real"
    assert RED in seen[-1] and "DRAFT FOOTER" in seen[-1] and "Triphala Churna" in seen[-1] and "@page { size: 210mm 297mm" in seen[-1]
    assert PrintSetting.objects.count() == 0  # not saved
    from apps.audit.models import AuditLog

    assert AuditLog.objects.filter(action="view", object_type="documents.printsetting").exists()  # a real patient was shown
