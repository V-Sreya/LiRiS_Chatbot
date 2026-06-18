import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.chatbot_service import chatbot_service
from app.services.currency_service import currency_service
from app.services.translation_service import (
    SUPPORTED_LANGUAGES,
    translation_service,
)
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.dependencies import get_session_id

log = logging.getLogger("api")

router = APIRouter(tags=["chat", "tools"])

# Escalations are persisted to a JSONL file so demo handlers can inspect them
# without spinning up an extra service. Each line is a single escalation event.
ESCALATIONS_PATH = Path(
    os.getenv("ESCALATIONS_PATH", "./data/escalations.jsonl")
).resolve()
ESCALATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    # Target language (ISO 639-1, e.g. "en", "hi", "ta"). "auto" detects from
    # the user's message and replies in the detected language. Defaults to "en"
    # so behaviour is unchanged when the frontend doesn't pass a language.
    language: Optional[str] = "en"


class CurrencyRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str


@router.post("/chat")
async def chat(
    session_id: str = Depends(get_session_id), request: ChatRequest | None = None
):
    """Chat endpoint with history + multilingual support."""
    if not request or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message required")

    message = request.message.strip()
    requested = (request.language or "en").strip() or "en"

    # Decide the reply language. "auto" → detect from the message; otherwise
    # honour the explicit choice.
    reply_lang = (
        translation_service.detect(message) if requested == "auto" else requested
    )

    # Always run the chatbot pipeline on English text — embeddings and intent
    # heuristics are English-only.
    english_query = (
        translation_service.translate(message, target="en", source="auto")
        if reply_lang != "en"
        else message
    )

    english_response = await chatbot_service.get_response(english_query, session_id)

    final = (
        translation_service.translate(english_response, target=reply_lang, source="en")
        if reply_lang != "en"
        else english_response
    )

    return {
        "response": final,
        "language": reply_lang,
        "translated": reply_lang != "en",
    }


@router.get("/languages")
async def list_languages():
    """Languages exposed by the frontend's language selector."""
    return {
        "languages": [{"code": k, "name": v} for k, v in SUPPORTED_LANGUAGES.items()],
        "available": translation_service.available,
    }


class TranslateRequest(BaseModel):
    text: str
    target: str
    source: Optional[str] = "auto"


@router.post("/translate")
async def translate(request: TranslateRequest):
    """Translate arbitrary text. Used by the frontend when the user changes
    language so previously-shown messages can be re-rendered in the new one."""
    if not request.text or not request.text.strip():
        return {"text": request.text, "language": request.target}
    out = translation_service.translate(
        request.text, target=request.target, source=request.source or "auto"
    )
    return {"text": out, "language": request.target}


class TranslateBatchRequest(BaseModel):
    # Map of key -> source text. The response echoes the same keys with
    # translated text. We keep the contract key-stable so the frontend can
    # cache UI strings per (locale, build) without worrying about ordering.
    texts: Dict[str, str]
    target: str
    source: Optional[str] = "en"


@router.post("/translate/batch")
async def translate_batch(request: TranslateBatchRequest):
    """Translate every value in `texts` to `target`. Returns the same keys.

    Used by the frontend to localize *the whole UI* (sidebar labels, buttons,
    suggestion chips, welcome card) — not just chat replies. The previous
    implementation looped through N strings and made N separate Google Translate
    requests; with ~50 UI strings that's 50 round-trips per language switch and
    almost always hit a rate-limit timeout, leaving the sidebar in English.
    We now join all values with a unique delimiter, translate once, and split
    back. One round-trip per language switch.
    """
    target = (request.target or "en").strip() or "en"
    source = (request.source or "en").strip() or "en"
    if target in ("en", "auto") or not request.texts:
        return {"texts": dict(request.texts), "language": target}

    out: Dict[str, str] = dict(request.texts)
    keys: list[str] = []
    values: list[str] = []
    for key, value in request.texts.items():
        if value and str(value).strip():
            keys.append(key)
            values.append(str(value))

    if not values:
        return {"texts": out, "language": target}

    # `‖` (U+2016 DOUBLE VERTICAL LINE) is rare enough to survive translation
    # unchanged across the languages we ship. Newlines around it keep Google
    # Translate from joining adjacent strings.
    delimiter = "\n‖‖‖\n"
    joined = delimiter.join(values)
    translated = translation_service.translate(joined, target=target, source=source)
    parts = translated.split(delimiter)

    if len(parts) == len(values):
        for key, part in zip(keys, parts):
            out[key] = part.strip() or out[key]
    else:
        # Splitting failed (translator mangled the delimiter). Fall back to
        # per-string translation so the user still sees translated labels.
        log.warning(
            "translate/batch delimiter split mismatch (%d parts, expected %d) — "
            "falling back to per-string translation for %s",
            len(parts), len(values), target,
        )
        for key, value in zip(keys, values):
            out[key] = translation_service.translate(
                value, target=target, source=source
            )
    return {"texts": out, "language": target}


@router.post("/upload")
async def upload_file(
    session_id: str = Depends(get_session_id), file: UploadFile = File(...)
):
    """Upload file for analysis (QR/OCR)."""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    response = await chatbot_service.handle_file_upload(
        content,
        file.content_type or "application/octet-stream",
        file.filename or "unknown",
        len(content),
        session_id,
    )
    return {"response": response, "session_id": session_id}


@router.post("/convert-currency")
async def convert_currency(
    session_id: str = Depends(get_session_id), request: CurrencyRequest | None = None
):
    """Convert currency."""
    if not request:
        raise HTTPException(status_code=400, detail="Currency request required")

    result = currency_service.convert(
        request.amount, request.from_currency, request.to_currency
    )
    if result.get("success"):
        return {"success": True, **result}
    raise HTTPException(
        status_code=400, detail=result.get("error", "Conversion failed")
    )


class EscalationRequest(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None  # email or phone
    reason: Optional[str] = None
    priority: Optional[str] = "normal"  # low | normal | high
    transcript: Optional[List[Dict[str, str]]] = None


@router.post("/escalate")
async def escalate_to_agent(
    session_id: str = Depends(get_session_id),
    request: EscalationRequest | None = None,
):
    """Hand the conversation off to a human agent.

    For the demo this writes the escalation to a JSONL log; in production this
    would push to a ticketing system / Slack / pager. The endpoint always
    returns a ticket id so the UI has something to surface to the user.
    """
    if not request:
        raise HTTPException(status_code=400, detail="Escalation payload required")
    if not (request.contact and request.contact.strip()):
        raise HTTPException(
            status_code=400, detail="A contact (email or phone) is required"
        )

    priority = (request.priority or "normal").lower()
    if priority not in {"low", "normal", "high"}:
        priority = "normal"

    ticket_id = f"ESC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{session_id[:6]}"
    record = {
        "ticket_id": ticket_id,
        "session_id": session_id,
        "name": (request.name or "").strip() or None,
        "contact": request.contact.strip(),
        "reason": (request.reason or "").strip() or None,
        "priority": priority,
        "transcript": request.transcript or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with ESCALATIONS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        log.exception("Failed to persist escalation %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Could not save escalation")

    return {
        "success": True,
        "ticket_id": ticket_id,
        "status": "queued",
        "priority": priority,
        "message": (
            f"Ticket {ticket_id} created. A human agent will reach out to "
            f"{record['contact']} shortly."
        ),
    }


@router.get("/escalations")
async def list_escalations(session_id: str = Depends(get_session_id)):
    """Return every escalation for the current session (newest first)."""
    if not ESCALATIONS_PATH.exists():
        return {"escalations": []}
    out: List[Dict[str, Any]] = []
    try:
        with ESCALATIONS_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("session_id") == session_id:
                    out.append(rec)
    except Exception as e:
        log.exception("Failed to read escalations: %s", e)
        return {"escalations": []}
    out.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"escalations": out}


class WhatsAppShareRequest(BaseModel):
    phone: Optional[str] = None  # E.164-ish digits, no plus
    transcript: Optional[List[Dict[str, str]]] = None
    note: Optional[str] = None


def _format_transcript(transcript: List[Dict[str, str]] | None) -> str:
    if not transcript:
        return ""
    lines: List[str] = []
    for msg in transcript:
        role = (msg.get("role") or "").strip().lower()
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        speaker = "You" if role == "user" else "LiRiS"
        lines.append(f"*{speaker}:* {content}")
    return "\n\n".join(lines)


@router.post("/whatsapp/share")
async def whatsapp_share(
    session_id: str = Depends(get_session_id),
    request: WhatsAppShareRequest | None = None,
):
    """Build a wa.me deep link that pre-fills a transcript export.

    No actual WhatsApp send happens server-side — we hand the frontend back a
    URL that opens WhatsApp on the user's device with the message ready to go.
    This avoids the need for the WhatsApp Business API (which requires a
    pre-approved template) in the demo path.
    """
    if not request:
        raise HTTPException(status_code=400, detail="Share payload required")

    body_parts: List[str] = ["💬 *LiRiS Conversation Export*"]
    if request.note and request.note.strip():
        body_parts.append(request.note.strip())
    transcript_body = _format_transcript(request.transcript)
    if transcript_body:
        body_parts.append(transcript_body)
    else:
        body_parts.append("_(No conversation yet.)_")
    body_parts.append(f"\n_Session: {session_id[:8]}…_")

    text = "\n\n".join(body_parts)
    encoded = quote(text, safe="")

    digits = "".join(ch for ch in (request.phone or "") if ch.isdigit())
    if digits:
        share_url = f"https://wa.me/{digits}?text={encoded}"
    else:
        # Universal share — user picks the recipient in WhatsApp.
        share_url = f"https://wa.me/?text={encoded}"

    return {
        "success": True,
        "share_url": share_url,
        "preview": text,
        "char_count": len(text),
    }


@router.get("/health")
async def health_check(session_id: str = Depends(get_session_id)):
    """Health check."""
    return {"status": "healthy", "session_id": session_id}
