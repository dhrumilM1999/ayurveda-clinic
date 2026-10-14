"""The Translate button: English name -> Gujarati and Hindi suggestion."""
import pytest

from apps.common import translate as tr
from conftest import client_for


@pytest.mark.django_db
def test_translate_suggests_gujarati_and_hindi(org_admin, branch_a):
    res = client_for(org_admin, branch_a).post("/api/v1/translate/", {"text": "Triphala Churna"}, format="json")
    assert res.status_code == 200 and set(res.data) == {"gu", "hi"} and "Triphala Churna" in res.data["gu"]
    only = client_for(org_admin, branch_a).post("/api/v1/translate/", {"text": "Abhyanga", "targets": ["hi"]}, format="json")
    assert set(only.data) == {"hi"}


@pytest.mark.django_db
def test_translate_needs_login_and_text(org_admin, branch_a, api):
    assert api.post("/api/v1/translate/", {"text": "x"}, format="json").status_code in (401, 403)
    assert client_for(org_admin, branch_a).post("/api/v1/translate/", {"text": "  "}, format="json").status_code == 400
    assert client_for(org_admin, branch_a).post("/api/v1/translate/", {"text": "x" * 301}, format="json").status_code == 400


@pytest.mark.django_db
def test_ai_offline_is_a_friendly_503(org_admin, branch_a, settings):
    settings.AI_PROVIDER = "ollama"
    settings.OLLAMA_URL = "http://127.0.0.1:9"  # nothing listens here
    settings.AI_TIMEOUT_SECONDS = 2
    res = client_for(org_admin, branch_a).post("/api/v1/translate/", {"text": "Abhyanga"}, format="json")
    assert res.status_code == 503 and res.data["detail"] == "AI is offline"


def test_prompt_file_has_the_text_and_languages():
    prompt = tr._prompt("Abhyanga", ["gu", "hi"])
    assert "Abhyanga" in prompt and "Gujarati" in prompt and "Hindi" in prompt and '{"gu"' in prompt
