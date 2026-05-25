"""Lightweight multilingual support using deep-translator + langdetect.

The chatbot's retrieval and intent layers all run in English (English embeddings,
English heuristics). To accept queries in other languages we:

  1. Detect the source language of the user's query (or accept an explicit hint).
  2. Translate the query to English before dispatching it to the chatbot.
  3. Translate the English response back to the user's language.

Falls back gracefully — if detection or translation fails, the original text is
passed through unchanged so the chatbot still works offline.
"""

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger("translation")

# Supported UI languages — keep the list small and Indic-friendly since the
# product targets ecommerce shoppers in India. "auto" uses langdetect.
SUPPORTED_LANGUAGES: dict[str, str] = {
    "auto": "Auto-detect",
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "ar": "Arabic",
    "zh-CN": "Chinese (Simplified)",
    "ja": "Japanese",
}


def _normalize_lang(code: str | None) -> str:
    if not code:
        return "en"
    code = code.strip()
    if not code:
        return "en"
    # Map a couple of common langdetect codes to deep-translator equivalents
    aliases = {"zh-cn": "zh-CN", "zh": "zh-CN"}
    return aliases.get(code.lower(), code)


class TranslationService:
    def __init__(self) -> None:
        self._available = self._probe()

    @staticmethod
    def _probe() -> bool:
        try:
            from deep_translator import GoogleTranslator  # noqa: F401
            from langdetect import detect  # noqa: F401
            return True
        except Exception as e:
            log.warning("Translation unavailable: %s", e)
            return False

    @property
    def available(self) -> bool:
        return self._available

    def detect(self, text: str) -> str:
        """Return an ISO-639-1 language code, or 'en' if detection fails."""
        if not text or not text.strip() or not self._available:
            return "en"
        try:
            from langdetect import DetectorFactory, detect

            DetectorFactory.seed = 0
            return _normalize_lang(detect(text))
        except Exception:
            return "en"

    def translate(self, text: str, target: str, source: str = "auto") -> str:
        """Translate `text` into `target` language. Best-effort, never raises."""
        if not text or not text.strip() or not self._available:
            return text
        target = _normalize_lang(target)
        source = _normalize_lang(source)
        if target == "en" and source == "en":
            return text
        # Skip translation when source already equals target.
        if source != "auto" and source == target:
            return text
        try:
            from deep_translator import GoogleTranslator

            # GoogleTranslator has a 5000-char limit per call; chunk if needed.
            chunks = self._split(text, 4500)
            out: list[str] = []
            for chunk in chunks:
                out.append(
                    GoogleTranslator(source=source, target=target).translate(chunk)
                    or chunk
                )
            return "".join(out)
        except Exception as e:
            log.warning("Translation failed (%s -> %s): %s", source, target, e)
            return text

    @staticmethod
    def _split(text: str, size: int) -> list[str]:
        if len(text) <= size:
            return [text]
        parts: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                cut = text.rfind("\n", start, end)
                if cut == -1 or cut <= start + size // 2:
                    cut = text.rfind(" ", start, end)
                if cut == -1 or cut <= start:
                    cut = end
                parts.append(text[start:cut])
                start = cut
            else:
                parts.append(text[start:end])
                break
        return parts


translation_service = TranslationService()
