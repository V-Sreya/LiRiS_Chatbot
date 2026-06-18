import hashlib
import re

from app.core.database import AsyncSessionLocal
from app.models.history import ChatMessage, FileUpload
from app.services.cv_service import cv_service
from app.services.document_service import document_service, extract_text
from app.services.ingestion import ingestion_service
from app.services.ingestion.indexer import product_indexer
from app.services.ocr_service import ocr_service

# Distance thresholds for ChromaDB cosine-ish distances. Smaller = more similar.
# Document chunks were too restrictive at 1.1; legitimate matches landed in
# the 1.1–1.4 range and got filtered out. Raise to 1.5.
DOC_DISTANCE_THRESHOLD = 1.5
INGESTED_PRODUCT_THRESHOLD = 1.3

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "will", "with", "what", "which", "who", "when", "where", "why",
    "how", "do", "does", "did", "can", "could", "should", "would", "about", "tell",
    "me", "you", "your", "my", "we", "us", "any", "some", "there", "here",
    "show", "give", "find", "list", "recommend", "suggest", "best", "good",
    "please", "want", "need", "looking", "products", "product", "items", "item",
    "under", "over", "below", "above", "between", "more", "less", "than", "around",
    "rs", "rs.", "inr", "₹", "rupees",
}

DOC_REFERENCE_PHRASES = [
    "according to", "from the document", "from the file", "in the document",
    "in the file", "the pdf", "the doc", "the attachment", "uploaded document",
    "what does it say", "the document say", "the document about", "document about",
    "what is the document", "summarize the document", "summary of the document",
]

# Lightweight category vocabulary — when one of these words appears in the
# query, prefer products whose title/breadcrumbs contain a related word.
CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "shoes": {"shoe", "sneaker", "sneakers", "footwear", "boots", "sandal", "sandals", "heels", "loafer"},
    "shirt": {"shirt", "tshirt", "t-shirt", "top", "polo"},
    "phone": {"phone", "smartphone", "mobile", "iphone", "android"},
    "laptop": {"laptop", "notebook", "macbook", "ultrabook"},
    "watch": {"watch", "smartwatch", "wristwatch"},
    "headphone": {"headphone", "headphones", "earbud", "earbuds", "earphone", "headset"},
    "makeup": {"makeup", "lipstick", "foundation", "mascara", "eyeliner", "kajal", "blush", "concealer", "primer", "cosmetic", "cosmetics", "beauty"},
    "skincare": {"skincare", "moisturizer", "moisturiser", "serum", "cleanser", "toner", "sunscreen"},
    "kitchen": {"kitchen", "cookware", "utensil", "pan", "pot", "blender", "mixer"},
    "furniture": {"furniture", "table", "chair", "desk", "bed", "sofa", "shelf", "rack"},
    "bag": {"bag", "backpack", "handbag", "wallet", "purse", "luggage", "suitcase"},
    "book": {"book", "novel", "textbook", "paperback"},
    "toy": {"toy", "toys", "doll", "puzzle", "game"},
    "food": {"food", "snack", "snacks", "biscuit", "chocolate", "drink", "beverage"},
}

# Category disqualifiers — title words that mean the product is *for* the
# category but isn't actually one. Asking for "shoes" returning a "shoe rack"
# is the canonical bug (see WhatsApp screenshot 2). These let us subtract,
# not just add, signal.
CATEGORY_ANTIWORDS: dict[str, set[str]] = {
    "shoes": {"rack", "racks", "organiser", "organizer", "holder", "stand", "cabinet", "shelf", "polish"},
    "phone": {"case", "cover", "stand", "holder", "charger", "cable", "screen guard", "tempered"},
    "laptop": {"bag", "stand", "skin", "sleeve", "cooling pad", "charger"},
    "watch": {"strap", "band", "charger", "stand", "case"},
    "headphone": {"stand", "case", "cable", "splitter"},
    "book": {"shelf", "rack", "stand", "cover", "light"},
}


def _tokenize(s: str) -> set[str]:
    return {w for w in re.findall(r"\w+", s.lower()) if w not in STOPWORDS and len(w) > 1}


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(])", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_snippet(text: str, query: str, max_sentences: int = 3, max_chars: int = 500) -> str:
    """Pick the sentences from `text` whose word overlap with `query` is highest."""
    sentences = _split_sentences(text)
    if not sentences:
        return text[:max_chars].strip()
    q_tokens = _tokenize(query)
    if not q_tokens:
        return " ".join(sentences[:max_sentences])[:max_chars]

    scored: list[tuple[int, int, str]] = []
    for idx, sent in enumerate(sentences):
        score = len(q_tokens & _tokenize(sent))
        if score > 0:
            scored.append((score, idx, sent))

    if not scored:
        first = sentences[0]
        return first[:max_chars] + ("…" if len(first) > max_chars else "")

    top = sorted(scored, key=lambda x: x[0], reverse=True)[:max_sentences]
    ordered_idx = sorted(idx for _, idx, _ in top)
    out = " ".join(sentences[i] for i in ordered_idx)
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0] + "…"
    return out


def _format_ingested_one_liner(meta: dict) -> str:
    title = (meta.get("title") or "").strip()
    brand = (meta.get("brand") or "").strip()
    price = meta.get("price")
    currency = (meta.get("currency") or "").upper()
    rating = meta.get("rating")
    availability = (meta.get("availability") or "").strip()
    url = (meta.get("url") or "").strip()

    head = title
    if brand:
        head = f"{title} — {brand}" if title else brand

    info: list[str] = []
    if price is not None:
        if currency in ("INR", "₹"):
            info.append(f"Price: ₹{price:,.0f}")
        elif currency:
            info.append(f"Price: {price} {currency}")
        else:
            info.append(f"Price: {price}")
    if rating is not None:
        info.append(f"Rating: {rating}")
    if availability and availability.lower() != "unknown":
        info.append(f"Availability: {availability}")

    bits: list[str] = []
    if head:
        bits.append(head)
    if info:
        bits.append(" • ".join(info))
    if url:
        bits.append(f"Source: {url}")
    return "\n".join(bits) if bits else (meta.get("title") or "(unnamed product)")


# ─── Query-intent helpers ──────────────────────────────────────────────────


_PRICE_NUM_RE = r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(?:rs\.?|inr|₹|rupees|/-|/)?"


def _parse_price_filter(ql: str) -> tuple[float | None, float | None]:
    """Return (min_price, max_price) parsed from the query, both optional."""
    m = re.search(rf"between\s+{_PRICE_NUM_RE}\s+(?:and|to|-)\s+{_PRICE_NUM_RE}", ql)
    if m:
        try:
            lo = float(m.group(1).replace(",", ""))
            hi = float(m.group(2).replace(",", ""))
            return (min(lo, hi), max(lo, hi))
        except ValueError:
            pass
    m = re.search(rf"(?:under|below|less than|cheaper than|within|upto|up to)\s+{_PRICE_NUM_RE}", ql)
    if m:
        try:
            return (None, float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    m = re.search(rf"(?:over|above|more than|greater than|atleast|at least)\s+{_PRICE_NUM_RE}", ql)
    if m:
        try:
            return (float(m.group(1).replace(",", "")), None)
        except ValueError:
            pass
    return (None, None)


def _category_tokens(ql: str) -> set[str]:
    """Return the union of category vocabulary words triggered by the query."""
    triggered: set[str] = set()
    for canonical, vocab in CATEGORY_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", ql) for w in vocab | {canonical}):
            triggered |= vocab | {canonical}
    return triggered


def _category_antiwords(ql: str) -> set[str]:
    """Return disqualifying words for whichever categories the query triggered."""
    anti: set[str] = set()
    for canonical, vocab in CATEGORY_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", ql) for w in vocab | {canonical}):
            anti |= CATEGORY_ANTIWORDS.get(canonical, set())
    return anti


def _score_hit(hit: dict, q_tokens: set[str], category_vocab: set[str]) -> float:
    """Combine vector distance, lexical overlap, and category match into one score.

    Lower is better. We add lexical/category boosts as negative offsets so a
    hit with strong keyword overlap moves ahead of a hit that's only embedding-
    close.
    """
    distance = hit.get("distance")
    if distance is None:
        distance = 1.0
    meta = hit.get("metadata") or {}
    haystack_parts = [
        meta.get("title") or "",
        meta.get("brand") or "",
        hit.get("content") or "",
    ]
    haystack = " ".join(haystack_parts).lower()
    hay_tokens = _tokenize(haystack)

    overlap = len(q_tokens & hay_tokens)
    cat_match = bool(category_vocab and (category_vocab & hay_tokens))

    # Each overlap word knocks ~0.15 off the distance; a category match knocks
    # off another 0.4. Tuned so a hit with two overlapping keywords clearly
    # beats a hit with a slightly closer embedding but no overlap.
    boost = 0.15 * overlap + (0.4 if cat_match else 0.0)
    return distance - boost


# ─── Chatbot service ───────────────────────────────────────────────────────


class ChatbotService:
    async def get_response(self, user_query: str, session_id: str):
        async with AsyncSessionLocal() as db:
            db.add(ChatMessage(session_id=session_id, message=user_query, role="user"))
            await db.flush()

            response = await self._dispatch(user_query, session_id)

            db.add(
                ChatMessage(session_id=session_id, message=response, role="assistant")
            )
            await db.commit()
            return response

    @staticmethod
    def _has_word(ql: str, terms) -> bool:
        for t in terms:
            pattern = re.escape(t).replace(r"\ ", r"\s+")
            if re.search(rf"\b{pattern}\b", ql):
                return True
        return False

    async def _dispatch(self, query: str, session_id: str) -> str:
        q = query.strip()
        ql = q.lower()

        if not q:
            return (
                "Hi! Connect a website (paste a URL) or upload a document, "
                "then ask me anything about it."
            )

        # Greetings — word-boundary match so "hi" alone counts but "history" doesn't
        if (
            len(ql.split()) <= 4
            and re.search(r"\b(hi|hello|hey|good morning|good evening)\b", ql)
        ):
            return "Hi! Connect a website URL or upload a document and I'll answer questions about it."

        # Help
        if self._has_word(ql, ["who are you", "what are you", "what can you do"]) or ql in {"help", "help?", "help me"}:
            return (
                "I'm a Q&A assistant. I can:\n"
                "• Answer questions about any website you connect (paste a product URL).\n"
                "• Answer questions about any document you upload (PDF / image / text).\n"
                "Try ingesting a URL via the sources panel or upload a document, then ask away."
            )

        explicit_doc = self._has_word(ql, DOC_REFERENCE_PHRASES)

        ingested_sources = await ingestion_service.list_for_session(session_id)
        has_docs = document_service.has_documents(session_id)

        # Gate only when *nothing* is connected. If the user uploaded a
        # document, answer from it — historically the bot refused with
        # "No document connected yet" / "connect a website first" even after a
        # PDF was uploaded, which is the bug the user reported.
        if not ingested_sources and not has_docs:
            return (
                "Nothing connected yet. Upload a document from the sidebar, "
                "or paste a website URL in **Add Website** and I'll index it. "
                "Then ask me anything about it."
            )

        # Pull more candidates so we have room to filter/rerank.
        ingested_hits: list[dict] = []
        if ingested_sources and not explicit_doc:
            source_ids = [s["source_id"] for s in ingested_sources]
            ingested_hits = product_indexer.query(q, source_ids=source_ids, n_results=12)

        doc_hits: list[dict] = []
        if has_docs:
            doc_hits = document_service.query(session_id, q, n_results=6)

        # Build query metadata once so both layers can use it.
        q_tokens = _tokenize(q)
        category_vocab = _category_tokens(ql)
        antiwords = _category_antiwords(ql)
        min_p, max_p = _parse_price_filter(ql)

        ingested_answer = self._format_ingested_answer(
            ingested_hits,
            ingested_sources,
            q_tokens,
            category_vocab,
            antiwords,
            min_p,
            max_p,
        )
        doc_answer = self._format_doc_answer(q, doc_hits)

        if explicit_doc and doc_answer:
            return doc_answer

        # Prefer the layer that produced *something* — and when both did, pick
        # whichever is closer in distance.
        if ingested_answer and doc_answer:
            ing_dist = (ingested_hits[0].get("distance") or 99.0) if ingested_hits else 99.0
            doc_dist = (doc_hits[0].get("distance") or 99.0) if doc_hits else 99.0
            return doc_answer if doc_dist < ing_dist else ingested_answer
        if ingested_answer:
            return ingested_answer
        if doc_answer:
            return doc_answer

        return self._fallback(bool(ingested_sources), has_docs)

    @staticmethod
    def _format_ingested_answer(
        hits: list[dict],
        sources: list[dict],
        q_tokens: set[str],
        category_vocab: set[str],
        antiwords: set[str],
        min_price: float | None,
        max_price: float | None,
    ) -> str | None:
        if not hits:
            return None

        # 1. Apply hard price filter when the query asked for one.
        filtered: list[dict] = []
        for h in hits:
            meta = h.get("metadata") or {}
            price = meta.get("price")
            if min_price is not None and (price is None or price < min_price):
                continue
            if max_price is not None and (price is None or price > max_price):
                continue
            filtered.append(h)

        if not filtered and (min_price is not None or max_price is not None):
            # Price constraint was specified but nothing matched. Don't fall
            # back to other prices — be explicit so the user can rephrase.
            return ChatbotService._no_price_match(min_price, max_price, sources)

        candidates = filtered or hits

        # 2. Drop products whose TITLE contains a category-anti-word
        #    (e.g. "shoe rack" when the user asked for "shoes"). This kills
        #    the most common category-confusion failure mode visible in the
        #    user's screenshots. If everything gets filtered, return no
        #    answer rather than showing the off-category products anyway.
        if antiwords:
            kept: list[dict] = []
            for h in candidates:
                title = ((h.get("metadata") or {}).get("title") or "").lower()
                title_tokens = _tokenize(title)
                if any(w in title or w in title_tokens for w in antiwords):
                    continue
                kept.append(h)
            candidates = kept
            if not candidates:
                return None

        # 3. Rerank by combined distance + lexical/category boost.
        scored = sorted(
            candidates,
            key=lambda h: _score_hit(h, q_tokens, category_vocab),
        )

        # 4. Drop hits whose effective score is way outside the threshold,
        #    AND that have zero lexical overlap with the query (the bug we're
        #    fixing — vector returning random close-by products). A very low
        #    raw distance (≤ 0.7) is a strong embedding match — accept it even
        #    without literal token overlap so plurals like "t-shirts" vs the
        #    title "T-Shirt" don't silently kill an obviously correct answer.
        relevant: list[dict] = []
        for h in scored:
            score = _score_hit(h, q_tokens, category_vocab)
            meta = h.get("metadata") or {}
            haystack = (
                (meta.get("title") or "") + " " + (h.get("content") or "")
            ).lower()
            hay_tokens = _tokenize(haystack)
            # Stem-light overlap: a query token also matches when one side is
            # a trailing-s plural of the other ("shirts" ↔ "shirt").
            overlap = False
            if q_tokens:
                for qt in q_tokens:
                    if qt in hay_tokens:
                        overlap = True
                        break
                    if qt.endswith("s") and qt[:-1] in hay_tokens:
                        overlap = True
                        break
                    if (qt + "s") in hay_tokens:
                        overlap = True
                        break
            cat_hit = bool(category_vocab and (category_vocab & hay_tokens))
            raw_distance = h.get("distance") if h.get("distance") is not None else 1.0
            strong_vector = raw_distance <= 0.7
            if score <= INGESTED_PRODUCT_THRESHOLD and (
                overlap or cat_hit or strong_vector or not q_tokens
            ):
                relevant.append(h)

        if not relevant:
            return None

        # Dedupe by URL so we don't repeat the same product 3x.
        seen: set[str] = set()
        deduped: list[dict] = []
        for h in relevant:
            url = (h.get("metadata") or {}).get("url") or ""
            if url in seen:
                continue
            seen.add(url)
            deduped.append(h)

        domains = sorted({s["domain"] for s in sources if s.get("domain")})
        header = "From your ingested site"
        if domains:
            header += f" ({', '.join(domains)})"
        header += ":"

        sections: list[str] = [header, ""]
        for h in deduped[:3]:
            sections.append(_format_ingested_one_liner(h["metadata"]))
            sections.append("")
        return "\n".join(sections).rstrip()

    @staticmethod
    def _no_price_match(
        min_price: float | None, max_price: float | None, sources: list[dict]
    ) -> str:
        domains = sorted({s["domain"] for s in sources if s.get("domain")})
        site_part = f" on {', '.join(domains)}" if domains else ""
        if min_price is not None and max_price is not None:
            band = f"between ₹{min_price:,.0f} and ₹{max_price:,.0f}"
        elif max_price is not None:
            band = f"under ₹{max_price:,.0f}"
        else:
            band = f"over ₹{min_price:,.0f}"
        return (
            f"I didn't find any indexed products{site_part} priced {band}. "
            "Try a wider price range, or ingest more pages from the listing."
        )

    @staticmethod
    def _format_doc_answer(query: str, hits: list[dict]) -> str | None:
        """Pick the best chunk from the user's uploaded documents.

        Two-stage selection:

        1. Filter hits that are below the distance threshold (vector-similar).
        2. Rerank survivors by `distance − 0.15 × keyword_overlap` so a chunk
           that *contains* the query keywords beats one that's only embedding-
           close. This kills the failure where every doc question returned the
           document's intro paragraph regardless of what was asked — that
           happened because we always grabbed hits[0] and then `_extract_snippet`
           fell back to the first sentence of the chunk when no sentence
           matched the query.
        3. If the query has keywords but no surviving chunk has *any* overlap,
           we refuse to answer rather than return an intro paragraph; the user
           can rephrase or quote a specific phrase.
        """
        if not hits:
            return None

        candidates = [
            h for h in hits
            if (h.get("distance") if h.get("distance") is not None else 99.0)
               <= DOC_DISTANCE_THRESHOLD
        ]
        if not candidates:
            return None

        q_tokens = _tokenize(query)
        # Words that are *about* the act of reading a doc, not about its
        # content. We strip these before deciding whether the user is asking
        # for specific content — "summarize the document" shouldn't trip the
        # "no keyword found" guard.
        DOC_SELFREF = {
            "document", "doc", "docs", "pdf", "file", "attachment", "upload",
            "uploaded", "summarize", "summarise", "summary", "explain", "content",
        }
        content_tokens = q_tokens - DOC_SELFREF

        def _doc_score(h: dict) -> float:
            distance = h.get("distance")
            if distance is None:
                distance = 1.0
            overlap = len(content_tokens & _tokenize(h.get("content") or ""))
            return distance - 0.15 * overlap

        candidates.sort(key=_doc_score)

        if content_tokens:
            # Require *every* meaningful query word to appear somewhere across
            # the candidate chunks. The earlier weaker check (any overlap)
            # let "can i return a personalized product?" leak through because
            # "return" matched the intro chunk even though "personalized" was
            # absent from the whole document — and the snippet picker then
            # surfaced the intro paragraph. Demanding total coverage stops
            # that silent failure.
            corpus_tokens: set[str] = set()
            for h in candidates:
                corpus_tokens |= _tokenize(h.get("content") or "")
            missing = content_tokens - corpus_tokens
            if missing:
                missing_disp = ", ".join(sorted(missing))
                return (
                    f"I couldn't find anything about **{missing_disp}** in "
                    "your uploaded document. Try rephrasing or quoting a "
                    "phrase from the document so I can locate it."
                )

        # Prefer the highest-ranked chunk that actually contains query terms;
        # only fall back to the top-ranked chunk for self-referential queries
        # like "summarize this document".
        chosen = candidates[0]
        if content_tokens:
            for h in candidates:
                if content_tokens & _tokenize(h.get("content") or ""):
                    chosen = h
                    break

        snippet = _extract_snippet(chosen["content"], query)
        filename = (chosen.get("metadata") or {}).get("filename", "uploaded document")
        return f"From your uploaded document ({filename}):\n\n{snippet}"

    @staticmethod
    def _fallback(has_ingested: bool, has_docs: bool) -> str:
        if has_ingested and has_docs:
            return (
                "I couldn't find a confident answer in the connected site or your "
                "uploaded document. Try rephrasing or asking something more specific."
            )
        if has_ingested:
            return (
                "I couldn't find a confident answer in the connected site. "
                "Try rephrasing or asking about a specific product, price, or detail "
                "from the page."
            )
        if has_docs:
            return (
                "I couldn't find a confident answer in your uploaded document. "
                "Try rephrasing or quoting a specific phrase from the document."
            )
        return (
            "Nothing connected yet. Paste a website URL in the sources panel or "
            "upload a document, then ask me about it."
        )

    async def handle_file_upload(
        self, file_bytes, file_type, filename, file_size, session_id
    ):
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        async with AsyncSessionLocal() as db:
            file_upload = FileUpload(
                session_id=session_id,
                filename=filename,
                file_size=file_size,
                content_type=file_type,
                content_hash=content_hash,
            )
            db.add(file_upload)
            await db.flush()
            file_id = file_upload.id

            qr_payload = None
            if "image" in (file_type or ""):
                qr_result = cv_service.scan_qr_code(file_bytes)
                if qr_result.get("success") and qr_result.get("results"):
                    qr_payload = qr_result["results"][0].get("data")

            text, kind = extract_text(file_bytes, file_type or "", filename or "")
            chunks_indexed = 0
            if text and text.strip():
                chunks_indexed = document_service.index_document(
                    session_id=session_id,
                    file_id=file_id,
                    filename=filename or f"upload_{file_id}",
                    text=text,
                )

            parts = []
            if qr_payload:
                parts.append(f"QR Code detected: {qr_payload}")
            if chunks_indexed > 0:
                parts.append(
                    f"📄 Indexed **{filename}** ({kind}, {chunks_indexed} chunk"
                    f"{'s' if chunks_indexed != 1 else ''}). "
                    "You can now ask me questions about its contents."
                )
            elif kind == "image" and not qr_payload:
                parts.append(
                    "Image uploaded — no QR code or readable text detected."
                )
            elif not parts:
                parts.append(
                    f"Uploaded **{filename}** but couldn't extract any text from it."
                )

            response = "\n\n".join(parts)

            db.add(
                ChatMessage(
                    session_id=session_id,
                    message=f"Uploaded: {filename}",
                    role="user",
                    file_id=file_id,
                )
            )
            await db.commit()
            return response


chatbot_service = ChatbotService()
