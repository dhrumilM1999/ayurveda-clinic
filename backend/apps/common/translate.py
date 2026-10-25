"""
Auto-translate a short English name into Gujarati / Hindi (the "Translate" button next to the GU / HI boxes).

Free provider: Ollama running on this PC (AI_PROVIDER=ollama in .env) - nothing leaves the PC and nothing is paid.
If Ollama is not running, TranslateUnavailable is raised and the screen says "AI is offline"; typing by hand still works.
The translation is only a SUGGESTION: it is filled into the boxes and the user can edit it before saving.
Tests use AI_PROVIDER=fake. The instruction text is in backend/templates/ai/translate_v1.txt (SAFE TO EDIT).
Only names of clinic lists are sent (never patient details).
"""
import json
import urllib.error
import urllib.request

from django.conf import settings

LANGUAGE_NAMES = {"gu": "Gujarati (gu)", "hi": "Hindi (hi)"}
PROMPT_VERSION = "translate_v1"


class TranslateUnavailable(Exception):
    """The translator is not reachable (Ollama off) or gave an unusable answer."""


def _prompt(text: str, targets: list[str]) -> str:
    raw = (settings.BASE_DIR / "templates" / "ai" / "translate_v1.txt").read_text(encoding="utf-8")
    body = raw.split("---\n", 1)[1]
    return body.format(text=text, languages=", ".join(LANGUAGE_NAMES[t] for t in targets))


def _ollama(text: str, targets: list[str]) -> dict:
    # keep_alive: the model stays in memory (so the next answer is quick); num_predict / num_ctx: a short name needs a short answer
    payload = json.dumps({"model": settings.OLLAMA_MODEL, "prompt": _prompt(text, targets), "stream": False, "format": "json",
                          "keep_alive": settings.OLLAMA_KEEP_ALIVE,
                          "options": {"temperature": 0, "num_predict": 160, "num_ctx": 1024}}).encode()
    request = urllib.request.Request(f"{settings.OLLAMA_URL}/api/generate", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=settings.AI_TIMEOUT_SECONDS) as response:
            answer = json.loads(json.loads(response.read())["response"])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
        raise TranslateUnavailable("AI is offline")
    return {lang: str(answer.get(lang, "")).strip() for lang in targets}


def _fake(text: str, targets: list[str]) -> dict:
    return {lang: f"[{lang}] {text}" for lang in targets}


PROVIDERS = {"ollama": _ollama, "fake": _fake}


def translate(text: str, targets: list[str]) -> dict:
    """{"gu": "...", "hi": "..."} for the asked languages."""
    provider = PROVIDERS.get(settings.AI_PROVIDER)
    if provider is None:
        raise TranslateUnavailable("AI is switched off")
    result = provider(text.strip(), targets)
    if not any(result.values()):
        raise TranslateUnavailable("AI gave no translation")
    return result
