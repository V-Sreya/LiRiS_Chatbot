"""Verifies the single-round-trip /translate/batch path.

Pre-fix behavior: N strings → N sequential Google Translate calls → ~50× round
trips per language switch → rate-limit timeouts → frontend falls back to
English. Post-fix: all strings are joined with `\\n‖‖‖\\n`, translated as ONE
call, then split back. This test asserts:

  * the translation_service.translate is called exactly once (not N times),
  * the returned dict has the same keys as the input,
  * each translated value matches the expected output,
  * if the delimiter is mangled by the translator, we fall back to per-string
    translation (so the user still gets something rendered).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import endpoints as endpoints_module


def _make_client(monkeypatch, fake_translate):
    """Build a FastAPI TestClient that exposes only the translate routes,
    so we don't have to spin up the full app (which needs Chroma, etc.)."""
    monkeypatch.setattr(
        endpoints_module.translation_service, "translate", fake_translate
    )
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(endpoints_module.router)
    return TestClient(app)


def test_batch_makes_single_translation_call(monkeypatch):
    """The whole point of the fix — N strings should produce 1 backend call."""
    calls: list[tuple[str, str, str]] = []

    def fake_translate(text, target, source="auto"):
        calls.append((text, target, source))
        # Echo the delimiter through unchanged and append "_<lang>" to each
        # segment so we can verify the split.
        delim = "\n‖‖‖\n"
        parts = text.split(delim)
        return delim.join(f"{p}_{target}" for p in parts)

    client = _make_client(monkeypatch, fake_translate)
    payload = {
        "texts": {"hello": "Hello", "bye": "Goodbye", "thanks": "Thanks"},
        "target": "hi",
        "source": "en",
    }
    resp = client.post("/translate/batch", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "hi"
    assert body["texts"] == {
        "hello": "Hello_hi",
        "bye": "Goodbye_hi",
        "thanks": "Thanks_hi",
    }
    # ONE backend call, not three. This is the whole bug-fix.
    assert len(calls) == 1


def test_batch_skips_translation_for_english_target(monkeypatch):
    def fake_translate(*_a, **_kw):
        raise AssertionError("translate should not be called for target=en")

    client = _make_client(monkeypatch, fake_translate)
    payload = {"texts": {"hi": "Hi"}, "target": "en", "source": "en"}
    resp = client.post("/translate/batch", json=payload)
    assert resp.status_code == 200
    assert resp.json()["texts"] == {"hi": "Hi"}


def test_batch_falls_back_to_per_string_when_delimiter_mangled(monkeypatch):
    """If the translator collapses the delimiter (sometimes Google does),
    splitting yields the wrong segment count and we re-translate string-by-
    string. This is the safety net — slow but still produces output."""
    calls: list[str] = []

    def fake_translate(text, target, source="auto"):
        calls.append(text)
        if "‖‖‖" in text:
            # Simulate a translator that ate the delimiter.
            return "MANGLED"
        return f"[{target}]{text}"

    client = _make_client(monkeypatch, fake_translate)
    payload = {
        "texts": {"a": "Apple", "b": "Banana"},
        "target": "fr",
        "source": "en",
    }
    resp = client.post("/translate/batch", json=payload)
    assert resp.status_code == 200
    assert resp.json()["texts"] == {"a": "[fr]Apple", "b": "[fr]Banana"}
    # One joined attempt + two per-string fallbacks = three calls.
    assert len(calls) == 3


def test_batch_preserves_empty_strings(monkeypatch):
    def fake_translate(text, target, source="auto"):
        delim = "\n‖‖‖\n"
        parts = text.split(delim)
        return delim.join(f"X_{p}" for p in parts)

    client = _make_client(monkeypatch, fake_translate)
    payload = {
        "texts": {"good": "Hello", "empty": "", "blank": "   "},
        "target": "hi",
        "source": "en",
    }
    resp = client.post("/translate/batch", json=payload)
    assert resp.status_code == 200
    body = resp.json()["texts"]
    # Empty/blank values pass through untouched; non-empty ones get translated.
    assert body["good"] == "X_Hello"
    assert body["empty"] == ""
    assert body["blank"] == "   "
