import os
import time
import uuid

import requests
import streamlit as st

st.set_page_config(
    page_title="LiRiS - Professional AI Assistant",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600;700&display=swap');

:root {
    --gold: #d4af37;
    --gold-bright: #f1c40f;
    --bg-0: #0a0a0a;
    --bg-1: #14142a;
    --bg-2: #1e1e2f;
    --border: #2a2a3a;
    --text: #f5f5f5;
    --text-muted: #b8b8c4;
    --space-1: 8px;
    --space-2: 16px;
    --space-3: 24px;
    --space-4: 32px;
    --radius: 14px;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--text); }
h1, h2, h3, h4 { font-family: 'Playfair Display', serif !important; color: var(--gold) !important; letter-spacing: 0.5px; }

.stApp, .main { background: linear-gradient(135deg, #0a0a0a 0%, #14142a 50%, #16213e 100%) !important; }
section[data-testid="stSidebar"] { background: rgba(10, 10, 16, 0.95) !important; border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] * { color: var(--text) !important; }

.liris-hero {
    text-align: center;
    padding: var(--space-3) 0 var(--space-2);
    border-bottom: 1px solid var(--border);
    margin-bottom: var(--space-3);
}
.liris-hero h1 {
    font-size: 3.2rem !important;
    margin: 0 !important;
    background: linear-gradient(135deg, var(--gold) 0%, var(--gold-bright) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.liris-hero p {
    color: var(--text-muted) !important;
    font-size: 0.95rem;
    margin-top: 4px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

.stTextInput > div > div > input,
.stNumberInput input,
.stSelectbox > div > div,
.stTextArea textarea {
    background-color: var(--bg-2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.25) !important;
    outline: none !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--gold) 0%, var(--gold-bright) 100%) !important;
    color: #000 !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(212, 175, 55, 0.35) !important;
}
.stButton > button:focus-visible {
    outline: 2px solid var(--gold-bright) !important;
    outline-offset: 2px !important;
}

.stButton > button[kind="secondary"] {
    background: var(--bg-2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--gold) !important;
    color: var(--gold) !important;
    box-shadow: none !important;
}

[data-testid="stFileUploader"] section {
    background: var(--bg-2) !important;
    border: 1px dashed var(--border) !important;
    border-radius: var(--radius) !important;
}
[data-testid="stFileUploader"] section:hover { border-color: var(--gold) !important; }

[data-testid="stChatMessage"] {
    background: rgba(30, 30, 47, 0.6) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: var(--space-2) !important;
    margin-bottom: var(--space-2) !important;
}
[data-testid="stChatMessageContent"] p { color: var(--text) !important; line-height: 1.6; }

[data-testid="stChatInput"] {
    background: var(--bg-1) !important;
    border-top: 1px solid var(--border) !important;
}
[data-testid="stChatInput"] textarea {
    background: var(--bg-2) !important;
    color: var(--text) !important;
    border-radius: var(--radius) !important;
}

[data-testid="stMetric"] {
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: var(--space-2);
}
[data-testid="stMetricValue"] { color: var(--gold) !important; }

[data-testid="stExpander"] {
    background: rgba(30, 30, 47, 0.4);
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}
[data-testid="stExpander"] summary { color: var(--gold) !important; font-weight: 500; }

.liris-welcome {
    text-align: center;
    padding: var(--space-4) var(--space-2);
    background: rgba(30, 30, 47, 0.4);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: var(--space-3);
}
.liris-welcome h3 { margin: 0 0 8px !important; }
.liris-welcome p { color: var(--text-muted); margin: 0; }

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }

.stCaption, [data-testid="stCaptionContainer"] { color: var(--text-muted) !important; }
</style>
""",
    unsafe_allow_html=True,
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")

# ─── UI string table ───────────────────────────────────────────────────────
# Every user-facing label lives here so the language picker can re-translate
# the whole UI, not just the chat. Keys are stable; English values are the
# source-of-truth; the backend's /translate/batch endpoint produces the rest
# on demand (and we cache per language in session_state so we only call it
# once per locale per session).
UI_STRINGS_EN: dict[str, str] = {
    "hero_subtitle": "Professional AI Assistant",
    "session_header": "Session",
    "metric_files": "Files",
    "metric_messages": "Messages",
    "btn_new_chat": "New Chat",
    "language_label": "Language",
    "language_help": (
        "Pick a language to translate the whole interface and chat. "
        "Choose Auto-detect to use whichever language you type in."
    ),
    "exp_upload": "Upload Document",
    "upload_label": "PDF, image, or text file",
    "upload_caption": "I'll use uploads to answer your questions.",
    "exp_website": "Add Website",
    "url_label": "Ecommerce URL",
    "max_pages_label": "Max pages",
    "btn_ingest": "Ingest site",
    "url_required": "Please enter a URL",
    "ingesting_queue": "Queuing ingestion…",
    "ingestion_running": "Ingestion still running — check Active sites below.",
    "active_sites": "Active sites in this chat:",
    "detach_tooltip": "Detach this site",
    "detached": "Detached",
    "detach_failed": "Detach failed",
    "exp_currency": "Currency Converter",
    "currency_amount": "Amount",
    "currency_from": "From",
    "currency_to": "To",
    "btn_convert": "Convert",
    "currency_failed": "Conversion failed",
    "currency_unavailable": "Conversion unavailable",
    "exp_whatsapp": "Share via WhatsApp",
    "whatsapp_phone_label": "Recipient phone (optional, include country code)",
    "whatsapp_phone_help": (
        "Leave blank to let WhatsApp ask you to pick a contact when the "
        "share sheet opens."
    ),
    "whatsapp_note_label": "Add a note (optional)",
    "btn_whatsapp_share": "Build WhatsApp link",
    "whatsapp_empty": "No messages yet — say something to LiRiS first.",
    "whatsapp_ready": "Tap the button below to open WhatsApp with your conversation prefilled.",
    "btn_open_whatsapp": "Open WhatsApp",
    "whatsapp_failed": "Could not build a WhatsApp link.",
    "exp_escalate": "Escalate to Agent",
    "escalate_intro": "Hand this conversation off to a human agent.",
    "escalate_name": "Your name (optional)",
    "escalate_contact": "Email or phone",
    "escalate_reason": "What do you need help with?",
    "escalate_priority": "Priority",
    "btn_escalate": "Escalate",
    "escalate_need_contact": "Please share an email or phone number so the agent can reach you.",
    "escalate_success": "Escalation queued",
    "escalate_failed": "Could not escalate right now — try again in a moment.",
    "welcome_title": "Welcome to LiRiS",
    "welcome_body": (
        "Your professional AI assistant. Ask me anything, upload a document, "
        "or try a suggestion below."
    ),
    "suggest_summary": "Summarize the key features of your platform",
    "suggest_product": "Help me select a product with specific features",
    "suggest_docs": "Explain what you can do with uploaded documents",
    "suggest_currency": "Convert 1000 USD to INR",
    "chat_placeholder": "Ask LiRiS anything…",
    "thinking": "LiRiS is thinking…",
    "footer_caption": "Upload files · Ask about products · Convert currency",
    "backend_unavailable": "Backend unavailable — is the API running?",
    "request_timeout": "Request timed out. Try again.",
    "translating_chat": "Re-translating chat history…",
    "translating_ui": "Translating interface…",
    "processing_doc": "Processing document…",
}

# Cache of translated UI string tables. Key = language code → dict[key, str].
if "ui_strings_cache" not in st.session_state:
    st.session_state.ui_strings_cache = {"en": UI_STRINGS_EN}

defaults = {
    "messages": [],
    "session_id": str(uuid.uuid4()),
    "files_uploaded": 0,
    "uploader_key": 0,
    "processed_uploads": set(),
    "pending_prompt": None,
    "ingested_sources": [],
    "language": "en",
    "language_options": None,
    "_applied_lang": "en",
    "whatsapp_share_url": None,
    "whatsapp_preview": None,
    "last_escalation": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def fetch_languages():
    """Pull supported UI languages from the backend (cached in session)."""
    if st.session_state.language_options is not None:
        return st.session_state.language_options
    try:
        resp = requests.get(f"{BACKEND_URL}/languages", timeout=5)
        if resp.status_code == 200:
            st.session_state.language_options = resp.json().get("languages", [])
            return st.session_state.language_options
    except Exception:
        pass
    st.session_state.language_options = [
        {"code": "en", "name": "English"},
        {"code": "auto", "name": "Auto-detect"},
        {"code": "hi", "name": "Hindi"},
        {"code": "ta", "name": "Tamil"},
        {"code": "te", "name": "Telugu"},
        {"code": "kn", "name": "Kannada"},
        {"code": "ml", "name": "Malayalam"},
        {"code": "mr", "name": "Marathi"},
        {"code": "bn", "name": "Bengali"},
        {"code": "gu", "name": "Gujarati"},
        {"code": "pa", "name": "Punjabi"},
        {"code": "ur", "name": "Urdu"},
        {"code": "fr", "name": "French"},
        {"code": "es", "name": "Spanish"},
        {"code": "de", "name": "German"},
        {"code": "ar", "name": "Arabic"},
        {"code": "zh-CN", "name": "Chinese (Simplified)"},
        {"code": "ja", "name": "Japanese"},
    ]
    return st.session_state.language_options


def _current_language() -> str:
    label = st.session_state.get("lang_picker")
    if not label or not st.session_state.get("language_options"):
        return "en"
    for opt in st.session_state.language_options:
        if opt["name"] == label:
            return opt["code"]
    return "en"


def _ensure_ui_strings(lang: str) -> dict[str, str]:
    """Return the UI string table for `lang`, fetching+caching if needed."""
    if lang in ("en", "auto"):
        return UI_STRINGS_EN
    cache = st.session_state.ui_strings_cache
    if lang in cache:
        return cache[lang]
    try:
        resp = requests.post(
            f"{BACKEND_URL}/translate/batch",
            json={"texts": UI_STRINGS_EN, "target": lang, "source": "en"},
            timeout=45,
        )
        if resp.status_code == 200:
            translated = resp.json().get("texts") or {}
            # Backfill any missing keys with English so the UI never shows a
            # blank label even when one string round-trips badly.
            merged = {**UI_STRINGS_EN, **{k: v for k, v in translated.items() if v}}
            cache[lang] = merged
            return merged
    except Exception:
        pass
    cache[lang] = UI_STRINGS_EN
    return UI_STRINGS_EN


def t(key: str) -> str:
    """Look up the current-language string for `key`. Falls back to English."""
    table = st.session_state.get("_ui_strings") or UI_STRINGS_EN
    return table.get(key, UI_STRINGS_EN.get(key, key))


def send_message(text):
    headers = {
        "X-Session-ID": st.session_state.session_id,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": text, "language": _current_language()},
            headers=headers,
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()["response"], None
        return None, f"Server returned {response.status_code}"
    except requests.exceptions.ConnectionError:
        return None, t("backend_unavailable")
    except requests.exceptions.Timeout:
        return None, t("request_timeout")
    except Exception as e:
        return None, f"Unexpected error: {e}"


def translate_text(text: str, target: str, source: str = "auto") -> str:
    if not text or not text.strip() or target == "en":
        return text
    try:
        resp = requests.post(
            f"{BACKEND_URL}/translate",
            json={"text": text, "target": target, "source": source},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json().get("text", text)
    except Exception:
        pass
    return text


def upload_file(file):
    headers = {"X-Session-ID": st.session_state.session_id}
    try:
        files = {
            "file": (
                file.name,
                file.getvalue(),
                file.type or "application/octet-stream",
            )
        }
        response = requests.post(
            f"{BACKEND_URL}/upload", files=files, headers=headers, timeout=60
        )
        st.session_state.files_uploaded += 1
        if response.status_code == 200:
            return response.json().get("response", "Upload processed")
        return "Upload failed"
    except Exception:
        return "Upload error — check backend connection."


def reset_chat():
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.files_uploaded = 0
    st.session_state.processed_uploads = set()
    st.session_state.uploader_key += 1
    st.session_state.ingested_sources = []
    st.session_state.whatsapp_share_url = None
    st.session_state.whatsapp_preview = None
    st.session_state.last_escalation = None


def submit_url_for_ingestion(url: str, max_pages: int = 50):
    headers = {
        "X-Session-ID": st.session_state.session_id,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(
            f"{BACKEND_URL}/sources/url",
            json={
                "url": url,
                "max_pages": max_pages,
                "session_id": st.session_state.session_id,
            },
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 202:
            return resp.json(), None
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return None, f"{resp.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return None, t("backend_unavailable")
    except Exception as e:
        return None, f"Unexpected error: {e}"


def poll_source_status(source_id: str):
    headers = {"X-Session-ID": st.session_state.session_id}
    try:
        resp = requests.get(
            f"{BACKEND_URL}/sources/{source_id}", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"{resp.status_code}"
    except Exception as e:
        return None, str(e)


def detach_source(source_id: str):
    headers = {"X-Session-ID": st.session_state.session_id}
    try:
        resp = requests.delete(
            f"{BACKEND_URL}/sources/{source_id}", headers=headers, timeout=10
        )
        return resp.status_code == 200
    except Exception:
        return False


def fetch_session_sources():
    headers = {"X-Session-ID": st.session_state.session_id}
    try:
        resp = requests.get(f"{BACKEND_URL}/sources", headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("sources", [])
    except Exception:
        return []
    return []


def build_whatsapp_link(phone: str, note: str) -> tuple[dict | None, str | None]:
    headers = {
        "X-Session-ID": st.session_state.session_id,
        "Content-Type": "application/json",
    }
    transcript = [
        {"role": m["role"], "content": m.get("original") or m.get("content", "")}
        for m in st.session_state.messages
    ]
    try:
        resp = requests.post(
            f"{BACKEND_URL}/whatsapp/share",
            json={"phone": phone, "note": note, "transcript": transcript},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"{resp.status_code}"
    except requests.exceptions.ConnectionError:
        return None, t("backend_unavailable")
    except Exception as e:
        return None, str(e)


def submit_escalation(
    name: str, contact: str, reason: str, priority: str
) -> tuple[dict | None, str | None]:
    headers = {
        "X-Session-ID": st.session_state.session_id,
        "Content-Type": "application/json",
    }
    transcript = [
        {"role": m["role"], "content": m.get("original") or m.get("content", "")}
        for m in st.session_state.messages
    ]
    try:
        resp = requests.post(
            f"{BACKEND_URL}/escalate",
            json={
                "name": name,
                "contact": contact,
                "reason": reason,
                "priority": priority,
                "transcript": transcript,
            },
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json(), None
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return None, f"{resp.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return None, t("backend_unavailable")
    except Exception as e:
        return None, str(e)


# ─── Resolve language and load UI strings BEFORE rendering ────────────────
languages = fetch_languages()
lang_codes = [l["code"] for l in languages]
lang_labels = [l["name"] for l in languages]

if "lang_picker" not in st.session_state:
    try:
        seed_idx = lang_codes.index(st.session_state.get("language", "en"))
    except ValueError:
        seed_idx = 0
    st.session_state.lang_picker = lang_labels[seed_idx]

active_lang = _current_language()
# When the user picks Auto-detect we keep the UI in English (we can't know
# what they'll type yet); chat replies still come back in their actual lang.
ui_lang = "en" if active_lang == "auto" else active_lang
st.session_state._ui_strings = _ensure_ui_strings(ui_lang)

# ─── Hero header ───────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="liris-hero">
        <h1>LiRiS</h1>
        <p>{t('hero_subtitle')}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### {t('session_header')}")
    col1, col2 = st.columns(2)
    col1.metric(t("metric_files"), st.session_state.files_uploaded)
    col2.metric(t("metric_messages"), len(st.session_state.messages))
    st.caption(f"ID · {st.session_state.session_id[:8]}…")

    if st.button(t("btn_new_chat"), use_container_width=True, type="secondary"):
        reset_chat()
        st.rerun()

    st.markdown("---")

    # Language picker
    selected_label = st.selectbox(
        f"🌍 {t('language_label')}",
        options=lang_labels,
        key="lang_picker",
        help=t("language_help"),
    )
    new_lang = lang_codes[lang_labels.index(selected_label)]
    st.session_state.language = new_lang

    applied = st.session_state.get("_applied_lang", new_lang)
    if new_lang != applied:
        if st.session_state.messages:
            target = "en" if new_lang in ("en", "auto") else new_lang
            with st.spinner(t("translating_chat")):
                for msg in st.session_state.messages:
                    if msg.get("role") != "assistant":
                        continue
                    original = msg.get("original") or msg.get("content")
                    msg["original"] = original
                    msg["content"] = (
                        original
                        if target == "en"
                        else translate_text(original, target)
                    )
        st.session_state._applied_lang = new_lang
        st.rerun()
    else:
        st.session_state._applied_lang = new_lang

    st.markdown("---")

    # ── Upload Document ──
    with st.expander(f"📎 {t('exp_upload')}", expanded=False):
        uploaded_file = st.file_uploader(
            t("upload_label"),
            type=["pdf", "png", "jpg", "jpeg", "txt", "md", "csv", "log"],
            key=f"uploader_{st.session_state.uploader_key}",
            label_visibility="collapsed",
        )
        st.caption(t("upload_caption"))

    # ── Add Website ──
    with st.expander(f"🌐 {t('exp_website')}", expanded=False):
        url_input = st.text_input(
            t("url_label"),
            placeholder="https://www.amazon.in/s?k=wireless+earbuds",
            key="url_to_ingest",
            label_visibility="collapsed",
        )
        max_pages = st.slider(
            t("max_pages_label"), min_value=1, max_value=200, value=50,
            key="max_pages_slider",
        )
        if st.button(t("btn_ingest"), use_container_width=True, key="ingest_btn"):
            if url_input and url_input.strip():
                with st.spinner(t("ingesting_queue")):
                    data, error = submit_url_for_ingestion(
                        url_input.strip(), max_pages=max_pages
                    )
                if error:
                    st.error(error)
                else:
                    src_id = data["source_id"]
                    progress = st.progress(0, text="Queued…")
                    status_text = st.empty()
                    final = None
                    for tick in range(60):
                        status, _ = poll_source_status(src_id)
                        if status:
                            stat = status.get("status", "queued")
                            count = status.get("products_indexed", 0)
                            seen = status.get("pages_seen", 0)
                            status_text.caption(
                                f"Status: {stat} · pages seen {seen} · indexed {count}"
                            )
                            if stat in ("complete", "partial", "failed"):
                                final = status
                                progress.progress(100, text=stat)
                                break
                            progress.progress(min(20 + tick * 2, 95), text=stat)
                        time.sleep(2)
                    if final:
                        if final["products_indexed"] > 0:
                            st.success(
                                f"Indexed {final['products_indexed']} products"
                            )
                        else:
                            errs = final.get("errors") or []
                            reason = errs[0]["reason"] if errs else "no products extracted"
                            st.warning(f"Ingestion finished: {reason}")
                    else:
                        st.info(t("ingestion_running"))
                    st.session_state.ingested_sources = fetch_session_sources()
            else:
                st.warning(t("url_required"))

        st.session_state.ingested_sources = fetch_session_sources()
        if st.session_state.ingested_sources:
            st.caption(t("active_sites"))
            for src in st.session_state.ingested_sources:
                cols = st.columns([4, 1])
                cols[0].markdown(
                    f"`{src['domain']}` — {src['products_indexed']} products"
                )
                if cols[1].button(
                    "✕",
                    key=f"detach_{src['source_id']}",
                    help=t("detach_tooltip"),
                ):
                    if detach_source(src["source_id"]):
                        st.success(t("detached"))
                    else:
                        st.error(t("detach_failed"))
                    st.session_state.ingested_sources = fetch_session_sources()
                    st.rerun()

    # ── Currency Converter ──
    with st.expander(f"💱 {t('exp_currency')}", expanded=False):
        amount = st.number_input(
            t("currency_amount"), min_value=0.01, value=100.0, step=0.01
        )
        currencies = ["USD", "EUR", "GBP", "INR", "AED"]
        c1, c2 = st.columns(2)
        from_curr = c1.selectbox(t("currency_from"), currencies, index=0)
        to_curr = c2.selectbox(t("currency_to"), currencies, index=3)

        if st.button(t("btn_convert"), use_container_width=True):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/convert-currency",
                    json={
                        "amount": amount,
                        "from_currency": from_curr,
                        "to_currency": to_curr,
                    },
                    headers={
                        "X-Session-ID": st.session_state.session_id,
                        "Content-Type": "application/json",
                    },
                    timeout=10,
                )
                if response.status_code == 200:
                    result = response.json()
                    st.success(
                        f"{result.get('converted_amount', 0):.2f} {to_curr}"
                    )
                else:
                    st.error(t("currency_failed"))
            except Exception:
                st.error(t("currency_unavailable"))

    # ── Share via WhatsApp ──
    with st.expander(f"📱 {t('exp_whatsapp')}", expanded=False):
        wa_phone = st.text_input(
            t("whatsapp_phone_label"),
            placeholder="+91 9876543210",
            key="wa_phone_input",
            help=t("whatsapp_phone_help"),
        )
        wa_note = st.text_area(
            t("whatsapp_note_label"),
            placeholder="Hi! Sharing my chat with LiRiS.",
            key="wa_note_input",
            height=80,
        )
        if st.button(
            t("btn_whatsapp_share"),
            use_container_width=True,
            key="wa_build_btn",
        ):
            if not st.session_state.messages:
                st.warning(t("whatsapp_empty"))
            else:
                data, error = build_whatsapp_link(wa_phone.strip(), wa_note.strip())
                if error or not data:
                    st.error(error or t("whatsapp_failed"))
                else:
                    st.session_state.whatsapp_share_url = data["share_url"]
                    st.session_state.whatsapp_preview = data.get("preview", "")

        if st.session_state.whatsapp_share_url:
            st.success(t("whatsapp_ready"))
            st.link_button(
                t("btn_open_whatsapp"),
                st.session_state.whatsapp_share_url,
                use_container_width=True,
            )
            if st.session_state.whatsapp_preview:
                with st.expander("Preview", expanded=False):
                    st.code(st.session_state.whatsapp_preview)

    # ── Escalate to Agent ──
    with st.expander(f"🙋 {t('exp_escalate')}", expanded=False):
        st.caption(t("escalate_intro"))
        esc_name = st.text_input(
            t("escalate_name"), key="esc_name_input", placeholder="Jane Doe"
        )
        esc_contact = st.text_input(
            t("escalate_contact"),
            key="esc_contact_input",
            placeholder="jane@example.com or +91 ...",
        )
        esc_reason = st.text_area(
            t("escalate_reason"), key="esc_reason_input", height=80
        )
        esc_priority = st.selectbox(
            t("escalate_priority"),
            options=["low", "normal", "high"],
            index=1,
            key="esc_priority_input",
        )
        if st.button(t("btn_escalate"), use_container_width=True, key="esc_btn"):
            if not esc_contact.strip():
                st.warning(t("escalate_need_contact"))
            else:
                data, error = submit_escalation(
                    esc_name.strip(),
                    esc_contact.strip(),
                    esc_reason.strip(),
                    esc_priority,
                )
                if error or not data:
                    st.error(error or t("escalate_failed"))
                else:
                    st.session_state.last_escalation = data
                    st.success(t("escalate_success"))

        last = st.session_state.last_escalation
        if last:
            st.info(
                f"🎫 **{last.get('ticket_id')}** · "
                f"{last.get('priority')} · {last.get('status')}\n\n"
                f"{last.get('message', '')}"
            )

    st.markdown("---")
    st.caption(t("footer_caption"))

# ─── File upload handler ───────────────────────────────────────────────────
if uploaded_file is not None:
    upload_id = getattr(uploaded_file, "file_id", None) or (
        f"{uploaded_file.name}:{uploaded_file.size}"
    )
    if upload_id not in st.session_state.processed_uploads:
        st.session_state.processed_uploads.add(upload_id)
        with st.spinner(t("processing_doc")):
            response = upload_file(uploaded_file)
            st.session_state.messages.append(
                {"role": "user", "content": f"📎 Uploaded: **{uploaded_file.name}**"}
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": response}
            )
        st.session_state.uploader_key += 1
        st.rerun()

# ─── Empty state ───────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown(
        f"""
        <div class="liris-welcome">
            <h3>{t('welcome_title')}</h3>
            <p>{t('welcome_body')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    suggestions = [
        t("suggest_summary"),
        t("suggest_email"),
        t("suggest_docs"),
        t("suggest_currency"),
    ]
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        if cols[i % 2].button(
            suggestion,
            key=f"suggest_{i}",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state.pending_prompt = suggestion
            st.rerun()

# ─── Chat history ──────────────────────────────────────────────────────────
for message in st.session_state.messages:
    avatar = "⭐" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# ─── Chat input ────────────────────────────────────────────────────────────
prompt = st.chat_input(t("chat_placeholder"))

if st.session_state.pending_prompt and not prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="⭐"):
        with st.spinner(t("thinking")):
            response, error = send_message(prompt)
            if error:
                st.error(error)
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"⚠️ {error}"}
                )
            else:
                st.markdown(response)
                lang = _current_language()
                if lang in ("en", "auto"):
                    original = response
                else:
                    original = translate_text(response, target="en", source=lang)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                        "original": original,
                    }
                )

    st.rerun()
