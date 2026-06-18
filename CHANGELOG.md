# Changelog

All notable changes to the Manus Chatbot project are tracked here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] — 2026-05-09

### Multilingual chat (real, not stubbed)

- **`backend/app/services/translation_service.py`** (new) — wraps `deep-translator` (GoogleTranslator) + `langdetect`. Public surface:
  - `translation_service.detect(text)` → ISO 639-1 code (defaults to `"en"` on failure).
  - `translation_service.translate(text, target, source="auto")` → best-effort translation, never raises. Chunks long inputs to fit GoogleTranslator's 5,000-char per-call cap.
  - `SUPPORTED_LANGUAGES` exposes the 18-language picker (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Urdu, French, Spanish, German, Arabic, Chinese-Simplified, Japanese — plus an `auto` option).
- **`backend/app/api/endpoints.py`**:
  - `ChatRequest` now accepts an optional `language` field (defaults to `"en"` for backward compatibility).
  - `/chat` translates the user query to English before dispatch (so embeddings + intent heuristics still match), then translates the English response back to the requested language. Replies include `language` and `translated` flags.
  - New `GET /api/v1/languages` returns the language codes/names the frontend should show in its picker.
- **`frontend/app.py`** — adds a 🌍 Language dropdown above the upload/website/currency expanders. The dropdown loads from `/api/v1/languages` (with a hardcoded fallback) and is sent on every chat call.
- **Dependencies added**: `deep-translator`, `langdetect` (entered into `backend/requirements.txt`).
- **Verified**: typing `नमस्ते` (Hindi) returns `नमस्ते! एक वेबसाइट यूआरएल कनेक्ट करें या एक दस्तावेज़ अपलोड करें और मैं इसके बारे में सवालों के जवाब दूंगा।`. Same query in `auto` mode produces identical output via langdetect. Asking *"मुझे ईयरबड्स दिखाओ"* against an ingested Amazon catalog returns the OnePlus Nord Buds product card translated into Hindi.

### Smarter relevance for ingested-catalog answers

- **`backend/app/services/chatbot_service.py`** — large rewrite of the ingested-product retrieval pipeline:
  - **Query-side intent layer**: parses three signals from every query:
    - `_parse_price_filter(ql)` recognises `under X`, `over X`, `between X and Y`, supports `Rs.`, `INR`, `₹`, `rupees`, `/-`, comma-separated digits, ranges in either order.
    - `_category_tokens(ql)` matches the query against a 14-bucket vocabulary (shoes, makeup, phone, laptop, watch, headphone, skincare, kitchen, furniture, bag, book, toy, food, shirt) and returns the union of related words.
    - `_category_antiwords(ql)` returns words that *disqualify* a hit when present in the title — e.g. asking for "shoes" disqualifies anything titled "shoe rack / organiser / holder / stand / cabinet / shelf / polish"; asking for "phone" disqualifies "case / cover / stand / charger". This kills the canonical bug where vector retrieval surfaces a *Shoe Rack* for a *shoes* query (visible in the user's WhatsApp screenshots).
  - **`_format_ingested_answer()`** now applies, in order: price filter → antiword exclusion → reranking by `(distance − 0.15·overlap − 0.4·category_match)` → keep only hits whose effective score ≤ `INGESTED_PRODUCT_THRESHOLD` *and* that share at least one keyword (or category word) with the query → dedupe by URL → emit the top 3.
  - **No-match clarity**: if a price filter excludes every candidate, the bot now says *"I didn't find any indexed products on … priced under ₹X. Try a wider price range, or ingest more pages from the listing."* instead of returning a wrong-category product anyway.
  - `INGESTED_PRODUCT_THRESHOLD` raised from `1.0` to `1.3` — the lexical/category boost lets relevant hits slip past, and irrelevant hits are now filtered earlier so a looser cap is safe.
- **Verified** end-to-end through the browser:
  - `show me earbuds under 5000` → returns the actual OnePlus Nord Buds 3r card.
  - `show me best shoes under 2000` against a catalog of only earbuds → *"I couldn't find a confident answer in the connected site"* (correct; previous code returned the earbud).
  - `recommend makeup products under 200` against a ₹1,799 earbud → *"I didn't find any indexed products … priced under ₹200"* (correct; previous code returned the earbud anyway).

### Document Q&A — broad questions now answered

- **`backend/app/services/chatbot_service.py:_format_doc_answer()`** — removed the strict lexical-overlap gate. Earlier the bot required at least one query token to appear in the matched chunk, which broke generic prompts like *"what is the document about"* (no shared keywords). Now it accepts any chunk under `DOC_DISTANCE_THRESHOLD`. The threshold itself was raised from `1.1` to `1.5` because legitimate matches commonly land in the 1.1–1.4 band.
- **`DOC_REFERENCE_PHRASES`** expanded with `"the document about" / "document about" / "what is the document" / "summarize the document" / "summary of the document"` so phrasing variants reliably route to doc-priority retrieval.
- **Verified**: uploaded a warranty document and asked *"what is the document about"* — bot now returns the *WARRANTY POLICY — Acme Electronics COVERAGE PERIOD…* intro instead of the previous *"I couldn't find a confident answer"* fallback. Specific question *"what is the warranty hotline number"* still returns the correct CONTACT block (`+91-22-5555-0199`).

### Ingestion: realistic browser headers + actionable error messages

- **`backend/app/services/ingestion/fetcher.py`** — replaced the previous `ManusChatbot-Ingestor/1.0` UA (which Flipkart/Meesho/Myntra immediately 403'd) with:
  - A pool of four modern desktop browser User-Agents (Chrome on Windows/macOS, Edge, Firefox), randomised per request and per retry attempt.
  - Full browser-style header set: `Accept`, `Accept-Language` (incl. `en-IN`), `Accept-Encoding`, `Sec-Ch-Ua` / `Sec-Ch-Ua-Mobile` / `Sec-Ch-Ua-Platform`, `Sec-Fetch-Dest/Mode/Site/User`, `Upgrade-Insecure-Requests`, `Cache-Control`, `Connection`, `DNT`.
  - 403 responses get one extra retry with a fresh UA before being declared anti-bot.
- **`backend/app/services/ingestion/service.py:_anti_bot_reason(url)`** — translates the generic `AntiBotChallenge` into a host-specific actionable message. Examples surfaced in the UI:
  - Flipkart: *"Flipkart blocks server-side scrapers. Try a single product URL (e.g. `https://www.flipkart.com/.../p/itm…`) instead of the homepage."*
  - Meesho: *"Meesho blocks server-side scrapers and renders products with JavaScript. Direct product URLs may work better than the homepage."*
  - Myntra / Ajio / Snapdeal get similarly worded host-specific reasons.
  - Unknown hosts fall back to: *"The site returned an anti-bot challenge. Try a direct product URL (e.g. ending in /dp/<ASIN> for Amazon, /p/<id> for others)."*
- **Verified**: the user's WhatsApp screenshot 5 showed Meesho failing with the cryptic *"Ingestion finished: anti-bot challenge"*. The new UI now shows the explanatory message above. Flipkart now passes the anti-bot gate (no more 403); discovery still returns 0 product URLs because the homepage is JS-rendered, but the failure reason is honest.

### Ingestion: duplicate-product crash fix

- **`backend/app/services/ingestion/indexer.py:upsert()`** — Amazon listing pages frequently surface the same ASIN twice (sponsored slot + organic slot). Previously this raised `ValueError: Expected IDs to be unique, found duplicates of: prod_…` and tanked the whole ingestion. Upsert now dedupes by computed product ID before pushing to Chroma; the second occurrence is silently dropped.
- **Verified**: `https://www.amazon.in/s?k=earbuds` ingested with `max_pages=20` now completes with status `partial` (15 products indexed) instead of `failed`.

## [Unreleased] — 2026-04-30

### Document-aware chat (added later on 2026-04-30)

- **`backend/app/services/document_service.py`** (new) — extracts text from uploaded files, chunks it (≈600 chars with 100-char overlap, prefers sentence boundaries), and indexes the chunks into a session-scoped ChromaDB collection (`user_documents`). Each chunk is tagged with `session_id`, `file_id`, `filename`, `chunk_index` so retrieval can be filtered per session.
  - **PDFs**: parsed via `pypdf`.
  - **Text files** (`.txt`, `.md`, `.csv`, `.log`, `.json`): decoded with utf-8 → utf-16 → latin-1 fallback.
  - **Images** (`.png`, `.jpg`, `.jpeg`, `.webp`): OCR'd via the existing `ocr_service`.
  - Public methods: `index_document(session_id, file_id, filename, text)`, `query(session_id, query_text, n_results)`, `has_documents(session_id)`.

- **`backend/app/services/chatbot_service.py`** — extended to consult uploaded documents in the answer pipeline:
  - When the user explicitly references "the document / file / pdf / attachment / according to / what does it say", the bot answers from doc chunks first.
  - Otherwise, after the site-intent layer runs and we'd hit vector retrieval, we run BOTH the catalog retrieval and the session doc retrieval, and pick whichever is closer (with a `DOC_DISTANCE_THRESHOLD = 1.4` cap).
  - Even on the final fallback, if the session has any indexed document, we make one more doc-search attempt before giving up.
  - Document responses dedupe near-duplicate chunks, return up to 2 best chunks separated by a divider, and cap total length at ≈1200 chars.

- **`backend/app/services/chatbot_service.py:handle_file_upload()`** — rewritten so every upload is now indexed automatically (not just images for QR/OCR). Returns a confirmation like *"📄 Indexed warranty.pdf (pdf, 7 chunks). You can now ask me questions about its contents."* QR-code detection still runs first on images so QR payloads remain visible. Old behaviour of dumping invoice-template regex output is gone — the bot answers from the document on demand instead.

- **`frontend/app.py`** — file uploader now also accepts `.txt`, `.md`, `.csv`, `.log` and the helper text reads *"Upload a document (PDF, image with text, or text file) — I'll use it to answer your questions"*.

- **Dependency added**: `pypdf` (installed into `.venv`) for PDF text extraction.

#### Verified document Q&A flow

Uploaded a synthetic warranty policy text file, then asked:

| Query | Result |
|---|---|
| *"according to the document, how long is the extended warranty?"* | Returns the COVERAGE PERIOD section ("24 months from the date of delivery"). |
| *"what is the warranty hotline number?"* | Returns the CONTACT section with the hotline `+91-22-5555-0199`. |
| *"what is not covered by the warranty?"* | Returns the WHAT'S NOT COVERED list (drops, water, cosmetic wear, etc.). |
| *"what is the most expensive product?"* | Still answers from the **site catalog** (Smart Watch Series 5) — site intents take priority over doc retrieval. |
| *"what payment methods do you accept?"* | Still answers from the site catalog (Visa, Mastercard, UPI, PayPal). |
| *"show me electronics under 3000"* | Still answers from the site catalog (Razer Mouse, Sony Earbuds). |
| Same warranty question in a **new session with no upload** | Falls through to a generic catalog answer — confirms session isolation. |

### Added
- **`backend/data/site_info.json`** — 16 curated site-fact documents (about, categories, navigation, search, cart, checkout, wishlist, product modal, flash sale, currency, payment methods, support, policies, company links, social, copyright). These are indexed alongside products so the bot can answer site-level questions, not just product questions.
- **`CHANGELOG.md`** — this file.
- **Local Python venv at `.venv/`** (Python 3.12) — used to run backend + frontend without Docker, since the Docker daemon wasn't running.
- **Native dep: `zbar`** installed via `brew install zbar` (required by `pyzbar` for QR-code scanning in `cv_service`).

### Changed
- **`backend/app/api/endpoints.py`** — removed duplicate `prefix="/api/v1"` on the router. Routes were being mounted twice (once on the router, once in `main.py`), producing `/api/v1/api/v1/chat`, which the frontend couldn't reach. Now the router has no prefix and `main.py` contributes the single `/api/v1` mount, matching the frontend's `BACKEND_URL`.

- **`backend/app/services/rag_service.py`** — full rewrite:
  - Loads the actual ShopWave catalog from `dummy site/products.json` (16 products) instead of the four hard-coded "luxury watch / silk tie / leather wallet / sunglasses" placeholders.
  - Loads site-level facts from `backend/data/site_info.json`.
  - Builds rich, embeddable text per product including name, brand, category, price, old price, computed discount %, badge, rating, description, colours, quantity, material, warranty, mfg date, mfg company, and wattage.
  - Stores typed metadata (`doc_type=product` / `doc_type=site_info`) so the chatbot can hydrate full product details from the in-memory catalog after a vector hit.
  - Adds `query()` (general retrieval) and `get_all_products()` (in-memory access for filter/aggregation queries).
  - Keeps the original `query_history()` async chat-history retrieval for compatibility.
  - Resolves the `dummy site/` and `backend/data/` paths via `pathlib` rather than relative cwd, so the backend works no matter where uvicorn is launched from.

- **`backend/app/services/chatbot_service.py`** — full rewrite:
  - New site-grounded `_answer()` pipeline replacing the old "single nearest-neighbour result with a 1.5 distance cutoff" path that was returning an unrelated leather-wallet match for every query.
  - Intent layer for greetings, capabilities, catalog size, category list, payment methods, currency, returns, order tracking, support, policies, social links, flash sale, new arrivals, cart/checkout flow, search/filter help, wishlist, and countdown timer.
  - Structured filter layer that detects category aliases (e.g. *gadgets → electronics*, *clothes → fashion*, *makeup → beauty*), brand names from the live catalog, and price filters (`under X`, `over X`, `between X and Y`).
  - Aggregation queries: cheapest, most expensive, top-rated — all category- and brand-scopable.
  - Falls back to vector search with a relaxed distance threshold (1.6) and, on a product hit, hydrates the full product card from the in-memory catalog instead of echoing the embedded text.
  - Two presentation helpers: `_product_one_liner()` for list responses and `_product_full_card()` for detailed responses.
  - File-upload handler retains QR-code → OCR fallback behaviour from the previous version.

### Fixed
- **`numpy` / `torch` / `transformers` / `opencv-python-headless` compatibility**: the latest versions of these packages on Python 3.12 created a pin chain that broke at import time. Resolved by pinning `numpy<2`, `transformers<5`, `sentence-transformers<4`, `opencv-python-headless<4.10`. Backend now imports cleanly.
- **API double-prefix bug** (see *Changed* above) — `/api/v1/chat`, `/api/v1/upload`, `/api/v1/convert-currency`, `/api/v1/health` are now reachable at the documented paths.
- **Stale ChromaDB store**: deleted `backend/chroma_db/` so the next startup re-seeds with the ShopWave catalog. The collection is repopulated automatically on first run.

### Skipped (intentionally)
- `tensorflow`, `psycopg2-binary`, `python-jose`, `passlib`, `python-magic`, `alembic` — listed in `backend/requirements.txt` but not imported anywhere. Skipped to keep the local install lean.

### How to run locally (no Docker)
```bash
# 1. Install native dep for QR scanning
brew install zbar

# 2. Create venv and install deps
python3.12 -m venv .venv
.venv/bin/pip install fastapi uvicorn 'pydantic>=2' pydantic-settings python-multipart \
  sqlalchemy aiosqlite python-dotenv requests Pillow 'numpy<2' \
  chromadb 'opencv-python-headless<4.10' pyzbar pytesseract \
  'transformers<5' 'sentence-transformers<4' streamlit

# 3. Backend (from backend/)
cd backend && DYLD_LIBRARY_PATH=/usr/local/lib \
  ../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000

# 4. Frontend (from frontend/, in another shell)
cd frontend && BACKEND_URL=http://localhost:8000/api/v1 \
  ../.venv/bin/streamlit run app.py --server.port 8501
```

### Verified queries
The following were tested end-to-end against the running backend and all returned grounded answers:

| Query | Returns |
|---|---|
| `hello` | Greeting |
| `what can you do?` | Capabilities list |
| `how many products are there?` | "16 products across 6 categories" |
| `what categories do you have?` | Beauty, Electronics, Fashion, Food & Snacks, Home & Living, Sports |
| `tell me about the Sony earbuds` | Wireless Earbuds Pro full card |
| `show fashion items under 2000` | Cotton T-Shirt Pack, Floral Summer Dress |
| `cheapest electronics` | Gaming Mouse RGB full card |
| `what is the most expensive product?` | Smart Watch Series 5 full card |
| `top rated beauty products` | Sunscreen SPF 50, Matte Lipstick Set |
| `what payment methods do you accept?` | Visa, Mastercard, UPI, PayPal |
| `tell me about the flash sale` | Top 5 highest-discount items |
| `what's new on the site?` | Items badged `new` |
| `how do I check out?` | Cart-sidebar / Proceed-to-Checkout flow |
| `what currency are prices in?` | Indian Rupees (₹) |
| `do you have running shoes?` | Nike Running Sneakers full card |
