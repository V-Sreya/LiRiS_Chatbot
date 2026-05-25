from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


class ParseError(Exception):
    pass


class Parser:
    name: str = "base"
    confidence: float = 0.5

    def parse(self, url: str, html: str) -> dict[str, Any]:
        """Return a dict matching the canonical Product schema (no source_id)."""
        raise NotImplementedError

    @staticmethod
    def now_iso() -> datetime:
        return datetime.now(timezone.utc)


CURRENCY_SYMBOLS = {
    "₹": "INR",
    "Rs.": "INR",
    "Rs": "INR",
    "INR": "INR",
    "$": "USD",
    "US$": "USD",
    "USD": "USD",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
    "AED": "AED",
    "د.إ": "AED",
}


def parse_price(text: str | None) -> tuple[Optional[Decimal], Optional[str]]:
    if not text:
        return None, None
    raw = text.strip()
    currency = None
    for sym, code in CURRENCY_SYMBOLS.items():
        if raw.startswith(sym) or sym in raw[:6]:
            currency = code
            break
    digits = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
    if not digits or digits == ".":
        return None, currency
    try:
        return Decimal(digits), currency
    except InvalidOperation:
        return None, currency


def clean_text(s: str | None) -> str:
    if not s:
        return ""
    return " ".join(s.split())
