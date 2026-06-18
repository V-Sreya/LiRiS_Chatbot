"""Regression tests for the two ingestion/chat fixes added 2026-05-15:

  Fix #5 — Fetcher must not advertise brotli (`br`) in Accept-Encoding when
            httpx has no brotli decoder installed. Vercel/Next-served sites
            silently returned compressed-bytes-as-text and the discoverer
            then saw zero product hrefs ("no products discovered").

  Fix #6 — Chatbot reranker accepts strong vector hits (distance ≤ 0.7) and
            stem-light plural overlap (`shirts` ↔ `shirt`) so a clearly
            relevant T-shirt result isn't filtered out by the literal-match
            gate.
"""

from __future__ import annotations

from app.services.chatbot_service import ChatbotService, _tokenize
from app.services.ingestion.fetcher import _browser_headers


# ─── Fetcher / Accept-Encoding ───────────────────────────────────────────────


def test_browser_headers_do_not_advertise_brotli():
    """httpx ships gzip+deflate but no brotli; advertising `br` breaks decoding."""
    h = _browser_headers()
    ae = h.get("Accept-Encoding", "")
    assert "br" not in ae.lower(), (
        "Accept-Encoding must not include `br` — httpx has no brotli decoder "
        f"and would return garbage HTML. Got: {ae!r}"
    )
    # Sanity: still advertise the encodings we *do* support so we don't get
    # uncompressed HTML on every request.
    assert "gzip" in ae
    assert "deflate" in ae


def test_browser_headers_carry_referer_when_provided():
    """Referer propagation must keep working — anti-bot checks look at it."""
    h = _browser_headers(referer="https://example.com/page")
    assert h.get("Referer") == "https://example.com/page"
    assert h.get("Sec-Fetch-Site") == "same-origin"


def test_browser_headers_no_referer_defaults_to_navigate():
    h = _browser_headers()
    assert "Referer" not in h
    assert h.get("Sec-Fetch-Site") == "none"


# ─── Chatbot reranker: stem-light overlap + strong-vector escape ─────────────


def test_rerank_strong_vector_passes_without_literal_overlap():
    """`do you have any t-shirts?` → tokens={'shirts'} which doesn't lexically
    overlap a title 'Acme Circles T-Shirt' (tokens={'t','shirt','acme','circles'}).
    Pre-fix the candidate was filtered out and the assistant fell back to
    'couldn't find a confident answer'. Strong vector (≤ 0.7) now passes."""
    hits = [
        {
            "content": "Acme Circles T-Shirt — 60% cotton/40% polyester jersey tee.",
            "metadata": {
                "title": "Acme Circles T-Shirt",
                "url": "https://demo.vercel.store/product/acme-circles-t-shirt",
            },
            "distance": 0.42,
        }
    ]
    sources = [{"source_id": "src_1", "domain": "demo.vercel.store"}]
    out = ChatbotService._format_ingested_answer(
        hits, sources,
        q_tokens=_tokenize("do you have any t-shirts?"),
        category_vocab=set(),  # neither "shirt" nor "tshirt" word-boundary-matches
        antiwords=set(),
        min_price=None, max_price=None,
    )
    assert out is not None
    assert "Acme Circles T-Shirt" in out
    assert "demo.vercel.store" in out


def test_rerank_plural_singular_overlap():
    """`shirts` ↔ `shirt` should count as overlap (stem-light)."""
    hits = [
        {
            "content": "blue cotton shirt with button-down collar",
            "metadata": {
                "title": "Classic Cotton Shirt",
                "url": "https://shop.example/product/classic-shirt",
            },
            "distance": 0.85,  # not "strong vector" — must pass via overlap
        }
    ]
    out = ChatbotService._format_ingested_answer(
        hits, [{"source_id": "x", "domain": "shop.example"}],
        q_tokens=_tokenize("any shirts in stock?"),
        category_vocab=set(),  # query doesn't trip category vocab via re.search
        antiwords=set(),
        min_price=None, max_price=None,
    )
    assert out is not None
    assert "Classic Cotton Shirt" in out


def test_rerank_weak_vector_no_overlap_still_filtered():
    """Guardrail: a weak-vector hit with no overlap/category/strong-vector
    signal must still be dropped — otherwise the bot regresses to surfacing
    random close-by products."""
    hits = [
        {
            "content": "completely unrelated kitchen utensil description",
            "metadata": {
                "title": "Stainless Steel Spatula",
                "url": "https://shop.example/product/spatula",
            },
            "distance": 1.1,  # weak vector
        }
    ]
    out = ChatbotService._format_ingested_answer(
        hits, [{"source_id": "x", "domain": "shop.example"}],
        q_tokens=_tokenize("any shirts in stock?"),
        category_vocab=set(),
        antiwords=set(),
        min_price=None, max_price=None,
    )
    assert out is None
