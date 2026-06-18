# Deployment Guide: Manus Chatbot

How to run the AI-powered e-commerce chatbot locally — either with Docker (recommended for production-style runs) or directly on your machine (faster for development).

## Prerequisites

**For Docker deployment**
- **Docker** ≥ 20.x and **Docker Compose** v2 (`docker compose`) or v1 (`docker-compose`).

**For local (non-Docker) deployment**
- **Python 3.11+**
- **Tesseract OCR** (`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Debian/Ubuntu) — needed for OCR.
- **zbar** (`brew install zbar` / `apt-get install libzbar0`) — needed for QR code detection.
- **Internet access** — only needed if you want the multilingual feature to translate responses (it calls Google Translate's free endpoint). With no internet the bot still answers in English.

## Option A — Docker (recommended)

1. **Configure environment** (optional): copy `chatbot.env` to `.env` in the project root. Compose reads `.env` automatically. All keys have working defaults, so this step is only needed if you want to override them.
   ```bash
   cp chatbot.env .env
   ```
2. **Build and start both services**:
   ```bash
   docker compose up --build
   ```
   First build takes 3–5 minutes (installs Tesseract, zbar, OpenCV, Chroma, sentence-transformers).
3. **Open the app**:
   - **Frontend (Streamlit chat UI)**: http://localhost:8501
   - **Backend (Swagger API docs)**: http://localhost:8000/docs
4. **Stop**: `Ctrl+C`, then `docker compose down`. Add `-v` to also wipe the `chroma_data` volume.

## Option B — Local development (no Docker)

1. **Create and activate a virtualenv** (one-time):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   pip install -r frontend/requirements.txt
   ```
2. **Start the backend** (terminal 1):
   ```bash
   cd backend && python main.py
   ```
   Listens on `http://0.0.0.0:8000` with auto-reload.
3. **Start the frontend** (terminal 2):
   ```bash
   cd frontend && streamlit run app.py
   ```
   Opens automatically at `http://localhost:8501`.

## Environment variables

Defined in `chatbot.env`. Every key is optional — the app boots without any of them.

| Key | Used by | Notes |
|---|---|---|
| `EXCHANGE_RATE_API_KEY` | `currency_service` | Currently a placeholder — the service uses the free public `exchangerate-api.com` endpoint regardless. |
| `SECRET_KEY` | `app/core/config.py` | Reserved for future JWT/auth; defaults to `"supersecretkey"`. |
| `DATABASE_URL` | `app/core/database.py` | Defaults to local SQLite (`chat_history.db`). |
| `WHATSAPP_API_TOKEN` | declared in config | No active WhatsApp integration in the current code — kept for future use. |

## Features available after deployment

- **Product Q&A (RAG)** — ChromaDB-backed catalog of 16 demo products (ShopWave). Seeds automatically on first boot.
- **Document upload + RAG** — PDF / TXT / CSV / MD / log files; chunked, embedded, and queried alongside the catalog.
- **Computer vision** — QR code authenticity check on uploaded images (`AUTH-` prefix marks authentic).
- **OCR** — Tesseract extracts text from invoice / warranty / receipt images.
- **URL ingestion** — paste any e-commerce URL via sidebar → 🌐 Add website. Dedicated parsers for Amazon and Flipkart; falls back to schema.org JSON-LD for everything else. Sends realistic browser headers and rotates User-Agent across retries to get past basic anti-bot gates. Heavily JS-rendered sites (Meesho/Myntra/Ajio) surface a clear actionable failure rather than a cryptic *"anti-bot challenge"*.
- **Smarter answer relevance** — chatbot understands `under X / over X / between X and Y` price filters, category vocabulary (shoes, makeup, phone, …), and category disqualifiers (asking for *shoes* won't return a *shoe rack*). When nothing matches, it explicitly says so instead of returning the nearest unrelated product.
- **Multilingual chat** — sidebar 🌍 Language picker, 18 languages plus auto-detect. The bot translates each query to English internally so retrieval still works, then replies in the user's language. Powered by `deep-translator` + `langdetect`; needs internet at chat time, otherwise falls back to English passthrough.
- **Currency conversion** — sidebar tool. Supported codes: USD, EUR, GBP, INR, AED.
- **Session persistence** — every message and upload is saved to SQLite (`backend/chat_history.db`) keyed by `X-Session-ID`.

For demo prompts and example queries, see [DEMO_GUIDE.md](DEMO_GUIDE.md).

## Embedding on a website

```html
<iframe
  src="http://your-deployment-url:8501/?embed=true"
  style="height: 600px; width: 100%; border: none;"
></iframe>
```

The Streamlit `?embed=true` query strips the toolbar and footer.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Port 8000/8501 is already in use` | Previous run still up | `lsof -i :8000 -i :8501` then `kill <pid>`. |
| Frontend shows "Backend unavailable" | `BACKEND_URL` not reachable | In Docker the default `http://backend:8000/api/v1` is correct. For local dev set `BACKEND_URL=http://localhost:8000/api/v1`. |
| Tesseract / zbar import error in local mode | System libs missing | macOS: `brew install tesseract zbar`. Linux: `apt-get install tesseract-ocr libzbar0`. |
| URL ingestion stuck in *Queued* | Site blocked by `robots.txt` or DNS failure | Try a different URL; check `backend` logs for the `sources_api` logger. |
| Ingestion fails with *"…blocks server-side scrapers"* | Site (Flipkart/Meesho/Myntra/Ajio/Snapdeal) is JS-rendered and cannot be scraped server-side | Try a direct product URL (e.g. `/dp/<ASIN>` for Amazon, `/p/itm…` for Flipkart). The fix would require a headless browser, which we don't ship. |
| Frontend says *"Ingestion still running — check Active sites"* but products eventually appear | Streamlit's polling loop times out after ~120 s; backend keeps working | Refresh the page or check the *Active sites* panel — the backend completes independently. |
| Multilingual reply comes back in English even though Hindi/Tamil/etc. is selected | `deep-translator` couldn't reach Google Translate's free endpoint | Check internet connectivity; the service falls back to passthrough on network errors. |
| QR / OCR returns nothing | Image too small or low contrast | Re-upload at higher resolution; ensure printed text is legible. |
| ChromaDB persistence lost on `docker compose down` | Volume removed | Don't pass `-v` unless you want a clean reset. The named volume `chroma_data` keeps the index between runs. |
| `chatbot.env` keys not picked up by Compose | Compose only reads `.env`, not `chatbot.env` | `cp chatbot.env .env` (Option A step 1). |

## Health check

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"healthy","session_id":"<uuid>"}
```

If both ports respond and the Streamlit UI loads, the deployment is good.
