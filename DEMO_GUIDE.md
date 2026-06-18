# LiRiS / Manus Chatbot — Demo Guide

A walkthrough of every feature with copy-paste examples. Use this as a script for live demos or as a self-test checklist.

---

## 0. Setup (30 seconds)

| Step | Action |
|---|---|
| 1 | Backend running on http://localhost:8000 — check http://localhost:8000/docs |
| 2 | Frontend (Streamlit) running on http://localhost:8501 |
| 3 | Open the frontend, click **New Chat** to start a clean session |
| 4 | Note the session ID in the sidebar — it isolates uploads, ingested sites, and chat history |

**Sidebar tour:** Session metrics · New Chat · 🌍 **Language** · 📎 Upload Document · 🌐 Add website · 💱 Currency Converter.

---

## 1. Conversational basics

| Demo | Type into chat | What to highlight |
|---|---|---|
| Greeting | `Hello` | Friendly bounded reply, points at ShopWave catalog |
| Capabilities | `What can you do?` | Lists every supported intent in one message |
| Help | `help` | Same as above — useful as a fallback prompt |

---

## 2. Built-in product catalog (RAG over ShopWave demo data)

The chatbot ships with a seeded ShopWave catalog across 6 categories (Electronics, Fashion, Home & Living, Beauty, Sports, Food & Snacks) priced in ₹.

### 2a. Single-product lookup
- `Tell me about Sony earbuds`
- `Show me the Nike Air Zoom`
- `What's the warranty on the Philips kettle?`

→ Returns a full product card: price, old price, % off, rating, colours, material, warranty, mfg date.

### 2b. Category browsing
- `Show me electronics`
- `What's in the beauty category?`
- `List sports products`

### 2c. Price filters (rupee-aware)
- `Fashion under ₹2000`
- `Electronics between 1000 and 5000`
- `Home items over 3000`

### 2d. Superlatives
- `What's the cheapest electronics product?`
- `Most expensive item in fashion`
- `Top rated products in beauty` *(use "top rated" — hyphenated form breaks the matcher)*

### 2e. Brand filter
- `Show me Sony products`
- `Cheapest Nike item`

### 2f. Catalog metadata
- `How many products do you have?`
- `What categories are available?`
- `What payment methods do you accept?` → Visa, Mastercard, UPI, PayPal
- `What currency are prices in?` → INR (₹)

### 2g. Site behaviour
- `How does the cart work?`
- `How do I search?`
- `How do wishlists work?`
- `When does the flash sale end?`
- `Show me today's deals` → top 5 highest-discount products
- `What's new?` → products tagged `new`

---

## 3. Document upload + RAG (OCR-backed)

**Sidebar → 📎 Upload Document.** Files in `sample_documents/` are ready to use.

| File | What to ask after upload |
|---|---|
| `shopwave_company_brief.pdf` | `According to the document, when was ShopWave founded?` |
| `shopwave_return_policy.txt` | `What does the file say about refunds?` |
| `shopwave_sales_q1.csv` | `From the document, what were Q1 sales numbers?` |
| `shopwave_launch_notes.md` | `Summarise the launch notes` |
| `shopwave_app.log` | `Are there any errors in the uploaded log?` |

**Demo points to call out:**
- The upload card confirms format + chunk count: *"Indexed shopwave_company_brief.pdf (pdf, 7 chunks)."*
- Catalog and document retrieval coexist — the bot picks whichever is closer to the query.
- Phrases like *"according to the document"* or *"from the file"* force document-priority retrieval.

---

## 4. Computer vision — QR code authenticity

**Sidebar → 📎 Upload Document → upload an image (PNG/JPG).**

Test images:
- A QR encoding `AUTH-12345-PRODUCT-XYZ` → ✅ *Product is authentic*
- A QR encoding `https://example.com/random` → ⚠ *Warning: Potential fake product detected!*
- An image with no QR → *No QR code or readable text detected.*

> Quick way to generate one: https://www.qr-code-generator.com/ — encode `AUTH-DEMO-001` and download as PNG.

---

## 5. OCR on documents/images

Upload an invoice scan, warranty card photo, or any image with printed text. The text is extracted, chunked, and indexed alongside other documents.

Then ask:
- `What is the invoice number?`
- `When was this invoice issued?`
- `Extract the total amount`

---

## 6. URL ingestion (the headline feature)

**Sidebar → 🌐 Add website → paste URL → set max pages → Ingest site.**

A websocket streams live progress: discovered → fetched → parsed → indexed.

### Recommended demo URLs — 19 verified live (2026-05-15)

Each URL below was ingested end-to-end and reached `status=complete`.
Together they indexed 76 products and cover every product category
present in `sample_documents/`.

**Amazon product pages** (single product, ~5 s each)

| # | URL | Result |
|---|---|---|
| 1 | `https://www.amazon.in/dp/B0FMDLD86P` | ✅ 1 product (OnePlus Nord Buds 3r) |
| 2 | `https://www.amazon.in/dp/B0BW8TXJJ2` | ✅ 1 product (boAt Nirvana Ion) |

**Amazon search/listing pages** (multi-product, 30–60 s each)

| # | URL | Pairs with sample doc | Result |
|---|---|---|---|
|  3 | `https://www.amazon.in/s?k=earbuds` | amazon_boat, amazon_oneplus | ✅ 4 products |
|  4 | `https://www.amazon.in/s?k=power+bank` | flipkart_powerbank, MagClick manual | ✅ 5 products |
|  5 | `https://www.amazon.in/s?k=running+shoes` | shopsy_shoe | ✅ 4 products |
|  6 | `https://www.amazon.in/s?k=hair+straightener` | flipkart_straightner, Philips manual | ✅ 5 products |
|  7 | `https://www.amazon.in/s?k=induction+cooktop` | Prestige manual | ✅ 4 products |
|  8 | `https://www.amazon.in/s?k=oven+toaster+grill` | Havells manual | ✅ 5 products |
|  9 | `https://www.amazon.in/s?k=cotton+kurta` | myntra_kurti | ✅ 4 products |
| 10 | `https://www.amazon.in/s?k=sunscreen+spf+50` | shopsy_sunscreen | ✅ 5 products |
| 11 | `https://www.amazon.in/s?k=ceiling+lamp` | myntra_lamp | ✅ 4 products |
| 12 | `https://www.amazon.in/s?k=wireless+earphones` | amazon_boat, amazon_oneplus | ✅ 4 products |
| 13 | `https://www.amazon.in/s?k=bluetooth+headphones` | Boats headset manual | ✅ 3 products |
| 14 | `https://www.amazon.in/s?k=smart+watch` | (general electronics) | ✅ 5 products |
| 15 | `https://www.amazon.in/s?k=trimmer` | (personal care) | ✅ 5 products |
| 16 | `https://www.amazon.in/s?k=mens+running+shoes` | shopsy_shoe | ✅ 4 products |
| 17 | `https://www.amazon.in/s?k=womens+sneakers` | shopsy_shoe | ✅ 4 products |
| 18 | `https://www.amazon.in/s?k=chopper+vegetable` | meesho_chopper | ✅ 4 products |
| 19 | `https://www.amazon.in/s?k=iron+box+750w` | meesho_ironbox | ✅ 5 products |

**Intentionally-failing URLs** (good to show — the error message is itself a feature)

| URL pattern | What the bot returns |
|---|---|
| `https://www.flipkart.com/` | *"Flipkart blocks server-side scrapers. Try a single product URL (.../p/itm...) instead of the homepage."* |
| `https://www.meesho.com/` | *"Meesho blocks server-side scrapers and renders products with JavaScript. Direct product URLs may work better than the homepage."* |
| `https://www.myntra.com/` | *"Myntra renders content with JavaScript and blocks server-side scrapers; we can't ingest it without a full browser."* |
| `https://www.ajio.com/` | *"Ajio blocks server-side scrapers; try a direct product URL."* |
| `https://www.snapdeal.com/` | *"Snapdeal blocked our request — try a direct product URL."* |

> A generic schema.org product page (any URL with `<script type="application/ld+json">`) also works — the chatbot falls back to the JSON-LD parser when no host-specific parser matches.

### Demo-able answer-quality fixes (call these out)

After ingesting an Amazon catalog, these queries used to mis-fire and now don't:

| Query | Demo point |
|---|---|
| `show me earbuds under 5000` | Returns the actual earbuds card with source URL — embeddings + lexical overlap + price filter all agreed. |
| `recommend makeup products under 200` (against an earbud catalog) | *"I didn't find any indexed products on www.amazon.in priced under ₹200. Try a wider price range, or ingest more pages from the listing."* The price filter is hard, so the bot doesn't surface a wrong-category match. |
| `show me best shoes under 2000` (no shoes in catalog) | *"I couldn't find a confident answer in the connected site."* The category vocabulary plus anti-words (rack/organiser/holder/stand/cabinet/shelf/polish) suppresses the *Shoe Rack* false-positive that the previous version returned. |
| `Compare the top 3 results` | Returns up to 3 deduped product cards. URLs are deduped so sponsored-slot duplicates from Amazon listings don't repeat. |

The reply is prefixed *"From your ingested site (amazon.in):"* and includes the source URL for citation.

**Detach demo:** in the sidebar's *Active sites in this chat* list, click ✕ next to a site to drop it from this session.

---

## 7. Currency conversion

Use the **sidebar 💱 Currency Converter**:
- Enter amount → pick *From* / *To* → click **Convert**.
- Supported codes: USD, EUR, GBP, INR, AED.
- Powered by `POST /api/v1/convert-currency` (live FX rates).

> **Note:** Natural-language conversion in the chat (e.g. *"Convert 100 USD to INR"*) is **not** wired up — the bot recognises currency keywords but only returns a generic pricing message. Always use the sidebar tool for actual conversions.

---

## 8. Multi-language chat (real, end-to-end)

The chatbot accepts queries in 18 languages and replies in the same one. Internally each query is translated to English (so embeddings + intent heuristics still match), then the English response is translated back. Powered by `deep-translator` (Google Translate, no API key) + `langdetect`.

**Sidebar → 🌍 Language → pick one.** Picking *Auto-detect* uses langdetect to read the language off whatever you typed.

Supported codes today: `en, hi, ta, te, kn, ml, mr, bn, gu, pa, ur, fr, es, de, ar, zh-CN, ja` plus `auto`.

| Language | Type into chat | Expected reply |
|---|---|---|
| Hindi | `नमस्ते` | *"नमस्ते! एक वेबसाइट यूआरएल कनेक्ट करें या एक दस्तावेज़ अपलोड करें और मैं इसके बारे में सवालों के जवाब दूंगा।"* |
| Hindi (with ingested catalog) | `मुझे ईयरबड्स दिखाओ` | Returns the same OnePlus Nord Buds product card, fully localised into Hindi (price, rating, availability labels included). |
| Tamil | `நீங்கள் என்ன செய்ய முடியும்?` | Capabilities reply in Tamil. |
| Spanish | `¿Qué puedes hacer?` | Capabilities reply in Spanish. |
| Auto-detect | any non-English text | Detected language code is used for the reply. |

**API:** `POST /api/v1/chat` accepts an optional `language` field (`"en"`, `"hi"`, …, or `"auto"`). The response includes `language` and `translated` flags. `GET /api/v1/languages` lists everything the picker shows.

**Network requirement:** translation hits Google Translate's free endpoint — needs internet at chat time. If the network is unavailable the call falls back to passing text through unchanged (better degraded behaviour than failing the request).

---

## 9. Session + history

- Every message and upload is persisted to `chat_history.db` (SQLite) keyed by session ID.
- **Sidebar metrics** show file count and message count live.
- **New Chat** rotates the session ID — uploads and ingested sites from the previous session don't leak in.
- The session ID is sent as `X-Session-ID` on every API call.

Demo: send 3 messages, click **New Chat**, send another → sidebar resets to 1 message, previous uploads aren't referenced.

---

## 10. Embedding on a website

Drop into any site:

```html
<iframe
  src="http://your-deployment-url:8501/?embed=true"
  style="height: 600px; width: 100%; border: none;">
</iframe>
```

The Streamlit `?embed=true` param hides chrome so it looks like a native widget.

---

## 11. API surface (for integrators)

Open http://localhost:8000/docs for the Swagger UI.

| Endpoint | Use |
|---|---|
| `POST /api/v1/chat` | Send a message, get a response. Accepts `{message, language?}` where `language` is `en`/`hi`/…/`auto`. |
| `GET /api/v1/languages` | List languages the frontend picker should show. |
| `POST /api/v1/upload` | Upload a file (multipart) — runs QR + OCR + indexing |
| `POST /api/v1/convert-currency` | `{amount, from_currency, to_currency}` |
| `POST /api/v1/sources/url` | Submit a URL for ingestion → returns `source_id` + `ws_url` |
| `GET /api/v1/sources/{id}` | Status of a single ingestion |
| `GET /api/v1/sources` | List active sites for this session |
| `DELETE /api/v1/sources/{id}` | Detach a site |
| `WS /ws/sources/{id}` | Live ingestion progress events |
| `GET /api/v1/health` | Health check (returns session ID) |

### One-liner curl probes

```bash
# Chat (English)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: demo-session" \
  -d '{"message": "show me cheapest electronics", "language": "en"}'

# Chat (Hindi reply)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: demo-session" \
  -d '{"message": "नमस्ते", "language": "hi"}'

# List supported languages
curl http://localhost:8000/api/v1/languages

# Currency
curl -X POST http://localhost:8000/api/v1/convert-currency \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "from_currency": "USD", "to_currency": "INR"}'

# Ingest a site
curl -X POST http://localhost:8000/api/v1/sources/url \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: demo-session" \
  -d '{"url": "https://www.amazon.in/dp/B0DGJ3T3SK", "max_pages": 5}'
```

---

## 12. Suggested 5-minute live demo flow

1. **(0:00)** Open http://localhost:8501 → click a suggested prompt to show the empty state.
2. **(0:30)** Type `What can you do?` → walk through the capabilities list.
3. **(1:00)** Catalog: `Show fashion under 2000` → then drill in: `Tell me more about <first item>`.
4. **(1:45)** Upload `shopwave_return_policy.txt` → ask `What does the document say about refunds?`.
5. **(2:30)** Sidebar 🌐 Add website → ingest an Amazon product URL with max pages = 5 → watch progress.
6. **(3:30)** After ingestion: `Show me what's on the site I just added` → highlight citation.
7. **(4:15)** Sidebar 💱 → convert 1000 USD → INR. Then in chat: `Convert ₹4999 to USD`.
8. **(4:45)** Show document RAG depth: `What does the document say about COD refunds?` (uses the return-policy doc uploaded earlier).
9. **(5:00)** Click **New Chat** → show session reset.

---

## 13. Troubleshooting cheat-sheet

| Symptom | Fix |
|---|---|
| Frontend can't reach backend | Check both ports (`lsof -i :8000 -i :8501`). Confirm `BACKEND_URL` env var in frontend. |
| Ingestion stuck in *Queued* | Site likely blocked by `robots.txt` — try a different URL. |
| Ingestion fails with *"…blocks server-side scrapers"* | The site (Meesho/Myntra/Ajio) needs a JavaScript-capable browser. Try a direct product URL or a different site. |
| Frontend says *"Ingestion still running"* but Active sites shows the product | Streamlit's polling loop times out at ~120 s; the backend keeps going. Refresh or wait — the product is indexed. |
| No QR detected | Image too small/blurry — re-upload a higher-res version. |
| OCR returns empty | File is a scanned image without a text layer — Tesseract may need clearer scans. |
| "I couldn't find a confident answer" | Query didn't match catalog or doc — rephrase, or upload a relevant document. |
| "I didn't find any indexed products … priced under ₹X" | Price filter excluded everything in the catalog. Widen the price band or ingest more pages. |
| Multilingual reply comes back in English | The translation service couldn't reach Google Translate (offline?). Falls back to English by design. |

---

## 14. Verification matrix (all prompts tested against running backend)

| # | Section | Prompt / Action | Status | Sample response |
|---|---|---|---|---|
| 1 | Basics | `Hello` | ✅ | "Hi! Welcome to ShopWave. I can help with products, categories…" |
| 2 | Basics | `What can you do?` | ✅ | Lists capabilities |
| 3 | Basics | `help` | ✅ | Same capabilities list |
| 4 | Catalog | `Tell me about Sony earbuds` | ✅ | Sony Wireless Earbuds Pro — ₹2,999 |
| 5 | Catalog | `Show me electronics` | ✅ | 4 products listed |
| 6 | Catalog | `Fashion under 2000` | ✅ | 2 products: Cotton T-Shirt Pack, Floral Summer Dress |
| 7 | Catalog | `Electronics between 1000 and 5000` | ✅ | 3 products |
| 8 | Catalog | `What's the cheapest electronics product?` | ✅ | Razer Gaming Mouse RGB |
| 9 | Catalog | `Most expensive item in fashion` | ✅ | Nike Running Sneakers |
| 10 | Catalog | `Top rated products in beauty` | ⚠ | Returns category list (top-rated branch needs better routing) |
| 11 | Catalog | `Show me Sony products` | ✅ | Sony Wireless Earbuds Pro |
| 12 | Metadata | `How many products do you have?` | ✅ | "16 products across 6 categories" |
| 13 | Metadata | `What categories are available?` | ✅ | Lists 6 categories |
| 14 | Metadata | `What payment methods do you accept?` | ✅ | Visa, Mastercard, UPI, PayPal |
| 15 | Metadata | `What currency are prices in?` | ✅ | INR (₹) |
| 16 | Site | `How does the cart work?` | ✅ | Detailed cart instructions |
| 17 | Site | `Show me today's deals` | ✅ | Top 5 discounted picks |
| 18 | Site | `What's new?` | ✅ | New arrivals list |
| 19 | Site | `How do wishlists work?` | ✅ | Heart icon on product cards |
| 20 | Site | `How do I return an item?` | ✅ | Returns link in footer |
| 21 | Document | Upload `shopwave_return_policy.txt` | ✅ | Indexed (text, 4 chunks) |
| 22 | Document | `What does the document say about refunds?` | ✅ | Quotes return policy |
| 23 | Currency | Sidebar: 100 USD → INR | ✅ | 9504 INR (rate 95.04) |
| 24 | Currency | Chat: `Convert 4999 to USD` | ❌ | Generic pricing reply (NL conversion not implemented) |
| 25 | Multi-lang | `नमस्ते` (Hindi picker) | ✅ | Hindi greeting reply (verified end-to-end in browser) |
| 26 | Multi-lang | `मुझे ईयरबड्स दिखाओ` against ingested catalog | ✅ | OnePlus earbud card translated to Hindi |
| 27 | Multi-lang | `GET /api/v1/languages` | ✅ | 18 languages + `auto`, `available: true` |
| 28 | Ingestion | Amazon `/dp/B0FMDLD86P` | ✅ | 1 product indexed in ~5s |
| 29 | Ingestion | Amazon `/s?k=earbuds`, max_pages=20 | ✅ | 15 products indexed, status `partial` (sponsored-slot dedupe in indexer) |
| 30 | Ingestion | Meesho homepage | ✅ | Clear failure: *"Meesho blocks server-side scrapers… direct product URLs may work better"* |
| 31 | Relevance | `show me earbuds under 5000` | ✅ | Returns the actual earbud, source URL included |
| 32 | Relevance | `recommend makeup products under 200` (no makeup in catalog) | ✅ | *"I didn't find any indexed products on www.amazon.in priced under ₹200"* (no false positive) |
| 33 | Relevance | `show me best shoes under 2000` (no shoes) | ✅ | *"I couldn't find a confident answer in the connected site"* (no shoe-rack false positive) |
| 34 | Doc Q&A | `what is the warranty hotline number` | ✅ | Returns CONTACT block with `+91-22-5555-0199` |
| 35 | Doc Q&A | `what is the document about` (broad) | ✅ | Returns intro WARRANTY POLICY chunk (was *"couldn't find an answer"* in previous version) |
| 36 | Ingestion | `POST /api/v1/sources/url` | ✅ | Returns `source_id` + `ws_url` |
| 37 | Ingestion | `GET /api/v1/sources` | ✅ | Lists active sources for session |
| 38 | API | `GET /api/v1/health` | ✅ | `{"status":"healthy", "session_id":"…"}` |

**Legend:** ✅ works as documented · ⚠ partial / depends on phrasing · ❌ documented behaviour does not work

**Untested in this run** (require physical artefacts but feature exists in code):
- QR code authenticity — needs a QR image file. Code path: `cv_service.scan_qr_code()` triggered by image upload; `AUTH-` prefix marks authentic.
- OCR on scanned invoice — needs an image with printed text. Pipeline: `ocr_service` → `document_service.index_document()`.
- Live Amazon/Flipkart ingestion — works against the API; full crawl depends on network and `robots.txt`.
