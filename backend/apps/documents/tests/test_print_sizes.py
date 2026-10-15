"""Paper sizes: a normal prescription must stay on ONE page on half-A4 (A5), and the case sheet must shrink to A5."""
import pytest
from django.template.loader import render_to_string
from weasyprint import HTML

from apps.documents.services import case_sheet_context, page_context, prescription_context
from apps.documents.tests.test_documents import rx, visit  # noqa: F401  (fixtures)
from apps.medicines.models import Medicine
from apps.prescriptions.services import save_prescription


def _pages(template: str, size: str, context: dict) -> int:
    html = render_to_string(f"documents/{template}", {**context, **page_context(size)})
    return len(HTML(string=html).render().pages)


@pytest.fixture
def nine_medicines(org, visit, doctor, rx):  # noqa: F811
    items = [{"medicine": m, "medicine_name": m.name, "dose": "1 tsp", "frequency": "1-0-1", "duration": 15}
             for m in Medicine.objects.filter(organization=org)[:9]]
    assert len(items) == 9
    return save_prescription(visit, items, "Take after food with warm water.", doctor)


@pytest.mark.django_db
@pytest.mark.parametrize("size", ["a4", "a5"])
def test_prescription_with_nine_medicines_is_one_page(nine_medicines, size):
    assert _pages("prescription.html", size, prescription_context(nine_medicines, "gu")) == 1


@pytest.mark.django_db
def test_case_sheet_shrinks_to_half_a4_on_one_page(nine_medicines):
    for size, scale in (("a4", "1"), ("a5", "0.70711")):
        context = {**prescription_context(nine_medicines, "en"), **case_sheet_context(nine_medicines, "en"), "sheet_scale": scale}
        assert _pages("prescription_ayurveda.html", size, context) == 1
