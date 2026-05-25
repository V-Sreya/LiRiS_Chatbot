"""Covers the two chatbot_service behavioral fixes.

  Fix #3 — Connection gate. The chatbot refuses to answer only when *nothing*
            is connected (no ingested website AND no uploaded document). If
            the user has uploaded a document, answers must come from it even
            without a website ingested — the previous "uploaded docs are only
            supporting context" gate was the bug the user reported.

  Fix #4 — Doc snippet reranking. When a doc is queried with specific keywords
            and no chunk contains them, the assistant should say so instead of
            returning the document's intro paragraph. When a chunk *does*
            contain the keywords, that chunk should win — even if a less-
            relevant chunk is fractionally closer in embedding space.
"""

from __future__ import annotations

import pytest

from app.services import chatbot_service as cs_module
from app.services.chatbot_service import ChatbotService


@pytest.fixture
def svc():
    return ChatbotService()


# ─── Website gate ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gate_no_website_no_docs(svc, monkeypatch):
    """Bare new chat — refuse and tell the user to connect something."""
    monkeypatch.setattr(
        cs_module.ingestion_service, "list_for_session",
        _async_returning([]),
    )
    monkeypatch.setattr(
        cs_module.document_service, "has_documents", lambda _sid: False
    )
    resp = await svc._dispatch("what's in stock under 500?", "sid-1")
    assert "Nothing connected" in resp
    assert "upload" in resp.lower() or "website" in resp.lower()


@pytest.mark.asyncio
async def test_doc_only_question_answers_from_document(svc, monkeypatch):
    """The user uploaded a doc but no website — we must answer from the doc.
    This is the regression we're guarding against: the old gate refused to
    answer doc-only questions and surfaced "No document connected yet" / "Add
    Website" instead of the actual return policy content."""
    monkeypatch.setattr(
        cs_module.ingestion_service, "list_for_session",
        _async_returning([]),
    )
    monkeypatch.setattr(
        cs_module.document_service, "has_documents", lambda _sid: True
    )
    monkeypatch.setattr(
        cs_module.document_service, "query",
        lambda *a, **kw: [
            {
                "content": (
                    "Return Policy: most items are returnable within 7 days "
                    "of delivery. Personalized items are not eligible for "
                    "return under any circumstances."
                ),
                "metadata": {"filename": "policy.pdf"},
                "distance": 0.5,
            }
        ],
    )
    resp = await svc._dispatch("can i return a personalized product?", "sid-2")
    assert resp is not None
    assert "policy.pdf" in resp
    assert "personalized" in resp.lower()
    assert "Add Website" not in resp


@pytest.mark.asyncio
async def test_greeting_still_works_without_anything(svc, monkeypatch):
    """Greetings short-circuit before the gate — UX would feel broken otherwise."""
    monkeypatch.setattr(
        cs_module.ingestion_service, "list_for_session",
        _async_returning([]),
    )
    monkeypatch.setattr(
        cs_module.document_service, "has_documents", lambda _sid: False
    )
    resp = await svc._dispatch("hi", "sid-3")
    assert resp.lower().startswith("hi")


# ─── Doc reranking + intro-only fallback fix ──────────────────────────────────


def test_doc_specific_query_with_no_keyword_match_refuses():
    """Pre-fix this returned the intro paragraph regardless of the question.
    The screenshot showed two different "personalized product" questions both
    receiving the doc's opening lines. Now we refuse explicitly."""
    hits = [
        {
            "content": (
                "ShopWave Return & Refund Policy. Applies to shopwave.in. "
                "Eligibility: most items are returnable within 7 days."
            ),
            "metadata": {"filename": "policy.pdf"},
            "distance": 0.9,
        },
        {
            "content": "How to initiate a return: open the Orders section.",
            "metadata": {"filename": "policy.pdf"},
            "distance": 1.0,
        },
    ]
    out = ChatbotService._format_doc_answer(
        "can i return a personalized product?", hits
    )
    assert out is not None
    # The intro is what used to leak through; it must not anymore.
    assert "ShopWave Return & Refund Policy" not in out
    assert "rephrasing" in out.lower() or "couldn't find" in out.lower()


def test_doc_keyword_hit_picks_correct_chunk_even_if_not_closest():
    """The relevance reranker should beat raw embedding distance: a chunk
    with literal keyword overlap (`personalized`) wins over a slightly closer
    but irrelevant chunk."""
    hits = [
        {
            "content": "General store policies overview.",  # closer, but useless
            "metadata": {"filename": "policy.pdf"},
            "distance": 0.6,
        },
        {
            "content": (
                "Personalized or customized items are NOT eligible for return."
            ),
            "metadata": {"filename": "policy.pdf"},
            "distance": 0.95,
        },
    ]
    out = ChatbotService._format_doc_answer(
        "can i return a personalized product?", hits
    )
    assert out is not None
    assert "Personalized" in out or "personalized" in out
    assert "NOT eligible" in out


def test_doc_broad_summarize_query_still_returns_top_chunk():
    """Regression guard: the no-overlap refusal must NOT fire for queries
    whose only tokens are doc-self-referential (`summarize`, `document`, etc.).
    Those should still return the top chunk."""
    hits = [
        {
            "content": "This document outlines return policies for 2025.",
            "metadata": {"filename": "policy.pdf"},
            "distance": 0.8,
        }
    ]
    out = ChatbotService._format_doc_answer("summarize the document", hits)
    assert out is not None
    assert "policy.pdf" in out
    assert "couldn't find" not in out.lower()


def test_doc_no_hits_returns_none():
    assert ChatbotService._format_doc_answer("anything", []) is None


def test_doc_all_hits_above_distance_threshold_returns_none():
    hits = [
        {"content": "irrelevant", "metadata": {"filename": "x"}, "distance": 99.0}
    ]
    assert ChatbotService._format_doc_answer("anything", hits) is None


# ─── helpers ──────────────────────────────────────────────────────────────────


def _async_returning(value):
    """Build an async-callable stub returning `value` on any invocation."""

    async def _stub(*_a, **_kw):
        return value

    return _stub
