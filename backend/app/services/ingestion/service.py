from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.history import IngestedSource
from app.models.product import Product
from app.services.ingestion.discoverer import discover
from app.services.ingestion.fetcher import AntiBotChallenge, Fetcher, make_client
from app.services.ingestion.indexer import product_indexer
from app.services.ingestion.page_classifier import classify
from app.services.ingestion.parsers import ParseError, select_parsers
from app.services.ingestion.url_validator import URLValidator, ValidationError

log = logging.getLogger("ingestion")


class IngestionEvent:
    def __init__(self, type: str, **payload: Any) -> None:
        self.type = type
        self.payload = payload

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, **self.payload}


class IngestionService:
    def __init__(self) -> None:
        self.validator = URLValidator()
        self.fetcher = Fetcher()
        self._queues: dict[str, asyncio.Queue[IngestionEvent | None]] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    @staticmethod
    def _new_source_id() -> str:
        return f"src_{uuid.uuid4().hex[:20]}"

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Strip tracking/affiliate junk that often triggers Amazon's WAF.

        Keeps `k`, `q`, `s`, `pid`, `dp`, search-meaningful params; drops
        `tag`, `ref`, `linkCode`, `pf_rd_*`, `psc`, `crid`, `qid`, etc.
        """
        from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if "amazon." not in host:
            return url
        keep = {"k", "q", "s", "pid", "dp", "node", "i"}
        kept = [(k, v) for k, v in parse_qsl(parsed.query) if k in keep]
        return urlunparse(parsed._replace(query=urlencode(kept)))

    def _ensure_queue(self, source_id: str) -> asyncio.Queue:
        if source_id not in self._queues:
            self._queues[source_id] = asyncio.Queue()
        return self._queues[source_id]

    async def _emit(self, source_id: str, event: IngestionEvent) -> None:
        queue = self._ensure_queue(source_id)
        await queue.put(event)

    def get_queue(self, source_id: str) -> asyncio.Queue | None:
        return self._queues.get(source_id)

    async def start(
        self,
        url: str,
        session_id: str,
        max_pages: int = 100,
        max_depth: int = 2,
    ) -> str:
        canonical = self._normalize_url(self.validator.validate(url))
        domain = urlparse(canonical).hostname or ""
        source_id = self._new_source_id()

        async with AsyncSessionLocal() as db:
            db.add(
                IngestedSource(
                    id=source_id,
                    session_id=session_id,
                    url=canonical,
                    domain=domain,
                    status="queued",
                    pages_seen=0,
                    products_indexed=0,
                    errors=[],
                )
            )
            await db.commit()

        self._ensure_queue(source_id)
        task = asyncio.create_task(
            self._run(source_id, canonical, max_pages=max_pages, max_depth=max_depth)
        )
        self._tasks[source_id] = task
        return source_id

    async def _set_status(
        self,
        source_id: str,
        *,
        status: str | None = None,
        pages_seen: int | None = None,
        products_indexed: int | None = None,
        errors: list[dict] | None = None,
        completed: bool = False,
    ) -> None:
        async with AsyncSessionLocal() as db:
            stmt = select(IngestedSource).where(IngestedSource.id == source_id)
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                return
            if status is not None:
                row.status = status
            if pages_seen is not None:
                row.pages_seen = pages_seen
            if products_indexed is not None:
                row.products_indexed = products_indexed
            if errors is not None:
                row.errors = errors
            if completed:
                row.completed_at = datetime.now(timezone.utc)
            await db.commit()

    async def _run(
        self,
        source_id: str,
        url: str,
        max_pages: int,
        max_depth: int,
    ) -> None:
        errors: list[dict] = []
        products_indexed = 0
        pages_seen = 0

        try:
            await self._emit(source_id, IngestionEvent("queued"))

            if not self.validator.is_allowed_by_robots(url):
                await self._set_status(
                    source_id,
                    status="failed",
                    errors=[{"url": url, "reason": "robots.txt disallow"}],
                    completed=True,
                )
                await self._emit(
                    source_id,
                    IngestionEvent(
                        "error",
                        url=url,
                        reason="robots.txt disallows automated indexing",
                    ),
                )
                await self._emit(source_id, IngestionEvent("complete", products_indexed=0))
                return

            await self._set_status(source_id, status="fetching")
            await self._emit(source_id, IngestionEvent("fetching", url=url))

            async with make_client() as client:
                try:
                    status_code, html = await self.fetcher.fetch(client, url)
                except AntiBotChallenge:
                    reason = self._anti_bot_reason(url)
                    await self._set_status(
                        source_id,
                        status="failed",
                        errors=[{"url": url, "reason": reason}],
                        completed=True,
                    )
                    await self._emit(
                        source_id,
                        IngestionEvent("error", url=url, reason=reason),
                    )
                    await self._emit(
                        source_id, IngestionEvent("complete", products_indexed=0)
                    )
                    return
                except httpx.HTTPError as e:
                    await self._set_status(
                        source_id,
                        status="failed",
                        errors=[{"url": url, "reason": f"fetch failed: {e}"}],
                        completed=True,
                    )
                    await self._emit(
                        source_id,
                        IngestionEvent("error", url=url, reason=f"fetch failed: {e}"),
                    )
                    await self._emit(
                        source_id, IngestionEvent("complete", products_indexed=0)
                    )
                    return

                pages_seen += 1
                page_type = classify(url, html)

                if page_type == "product":
                    target_urls = [url]
                    base_html_for_target = html
                else:
                    target_urls = await discover(
                        client, self.fetcher, url, html, max_pages
                    )
                    base_html_for_target = None

                if not target_urls:
                    await self._set_status(
                        source_id,
                        status="failed",
                        pages_seen=pages_seen,
                        errors=[{"url": url, "reason": "no products discovered"}],
                        completed=True,
                    )
                    await self._emit(
                        source_id,
                        IngestionEvent(
                            "error",
                            url=url,
                            reason="No product pages discovered from this URL",
                        ),
                    )
                    await self._emit(
                        source_id, IngestionEvent("complete", products_indexed=0)
                    )
                    return

                target_urls = target_urls[:max_pages]
                products: list[dict[str, Any]] = []

                for target in target_urls:
                    if not self.validator.is_allowed_by_robots(target):
                        errors.append(
                            {"url": target, "reason": "robots.txt disallow"}
                        )
                        continue
                    await self._emit(
                        source_id, IngestionEvent("fetching", url=target)
                    )
                    try:
                        if target == url and base_html_for_target is not None:
                            page_html = base_html_for_target
                        else:
                            _, page_html = await self.fetcher.fetch(client, target)
                            pages_seen += 1
                    except AntiBotChallenge:
                        errors.append(
                            {"url": target, "reason": "anti-bot challenge"}
                        )
                        await self._emit(
                            source_id,
                            IngestionEvent(
                                "error", url=target, reason="anti-bot challenge"
                            ),
                        )
                        continue
                    except Exception as e:
                        errors.append({"url": target, "reason": f"fetch error: {e}"})
                        await self._emit(
                            source_id,
                            IngestionEvent(
                                "error", url=target, reason=f"fetch error: {e}"
                            ),
                        )
                        continue

                    parsed = self._try_parsers(target, page_html)
                    if not parsed:
                        errors.append(
                            {"url": target, "reason": "no parser succeeded"}
                        )
                        await self._emit(
                            source_id,
                            IngestionEvent(
                                "error", url=target, reason="no parser succeeded"
                            ),
                        )
                        continue

                    parsed["source_id"] = source_id
                    try:
                        validated = Product(**parsed)
                    except PydanticValidationError as e:
                        errors.append({"url": target, "reason": f"schema: {e}"})
                        continue
                    record = validated.model_dump(mode="python")
                    record["url"] = str(record["url"])
                    record["images"] = [str(u) for u in record["images"]]
                    products.append(record)
                    await self._emit(
                        source_id,
                        IngestionEvent("parsed", url=target, product_count=len(products)),
                    )

                if products:
                    products_indexed = product_indexer.upsert(source_id, products)
                    await self._emit(
                        source_id,
                        IngestionEvent("indexed", products_indexed=products_indexed),
                    )

                final_status = (
                    "complete"
                    if products_indexed and not errors
                    else ("partial" if products_indexed else "failed")
                )
                await self._set_status(
                    source_id,
                    status=final_status,
                    pages_seen=pages_seen,
                    products_indexed=products_indexed,
                    errors=errors,
                    completed=True,
                )
                await self._emit(
                    source_id,
                    IngestionEvent("complete", products_indexed=products_indexed),
                )
        except Exception as exc:
            log.exception("Ingestion failed for %s", source_id)
            await self._set_status(
                source_id,
                status="failed",
                errors=errors + [{"url": url, "reason": f"unexpected: {exc}"}],
                completed=True,
            )
            await self._emit(
                source_id,
                IngestionEvent("error", url=url, reason=f"unexpected: {exc}"),
            )
            await self._emit(
                source_id, IngestionEvent("complete", products_indexed=products_indexed)
            )
        finally:
            queue = self._queues.get(source_id)
            if queue is not None:
                await queue.put(None)

    @staticmethod
    def _anti_bot_reason(url: str) -> str:
        host = (urlparse(url).hostname or "").lower()
        # Sites we know are heavily JS-rendered or behind aggressive anti-bot
        # protection — give the user actionable advice instead of a cryptic
        # "anti-bot challenge".
        hostile = {
            "amazon.": (
                "Amazon presented an AWS WAF JavaScript challenge instead of "
                "the page. The homepage is most likely to trigger this — try "
                "a search URL (https://www.amazon.in/s?k=earbuds) or a direct "
                "product URL (https://www.amazon.in/dp/<ASIN>). Removing "
                "tracking/affiliate query parameters often helps too."
            ),
            "flipkart.com": "Flipkart blocks server-side scrapers. Try a single product URL (e.g. https://www.flipkart.com/.../p/itm...) instead of the homepage.",
            "meesho.com": "Meesho blocks server-side scrapers and renders products with JavaScript. Direct product URLs may work better than the homepage.",
            "myntra.com": "Myntra renders content with JavaScript and blocks server-side scrapers; we can't ingest it without a full browser.",
            "ajio.com": "Ajio blocks server-side scrapers; try a direct product URL.",
            "snapdeal.com": "Snapdeal blocked our request — try a direct product URL.",
        }
        for needle, msg in hostile.items():
            if needle in host:
                return msg
        return (
            "The site returned an anti-bot challenge. Try a direct product URL "
            "(e.g. ending in /dp/<ASIN> for Amazon, /p/<id> for others)."
        )

    @staticmethod
    def _try_parsers(url: str, html: str) -> dict[str, Any] | None:
        last_error: ParseError | None = None
        best: dict[str, Any] | None = None
        for parser in select_parsers(url):
            try:
                result = parser.parse(url, html)
            except ParseError as e:
                last_error = e
                continue
            except Exception as e:  # pragma: no cover
                last_error = ParseError(str(e))
                continue
            if best is None or result.get("parser_confidence", 0) > best.get(
                "parser_confidence", 0
            ):
                best = result
            if best.get("parser_confidence", 0) >= 0.9:
                break
        return best

    async def get_status(self, source_id: str) -> dict[str, Any] | None:
        async with AsyncSessionLocal() as db:
            stmt = select(IngestedSource).where(IngestedSource.id == source_id)
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                return None
            return {
                "source_id": row.id,
                "url": row.url,
                "status": row.status,
                "pages_seen": row.pages_seen,
                "products_indexed": row.products_indexed,
                "errors": row.errors or [],
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": (
                    row.completed_at.isoformat() if row.completed_at else None
                ),
            }

    async def list_for_session(self, session_id: str) -> list[dict[str, Any]]:
        async with AsyncSessionLocal() as db:
            stmt = select(IngestedSource).where(
                IngestedSource.session_id == session_id
            )
            rows = (await db.execute(stmt)).scalars().all()
            return [
                {
                    "source_id": r.id,
                    "url": r.url,
                    "domain": r.domain,
                    "status": r.status,
                    "products_indexed": r.products_indexed,
                }
                for r in rows
            ]

    async def detach(self, source_id: str) -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            stmt = select(IngestedSource).where(IngestedSource.id == source_id)
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                return {"detached": False, "reason": "not_found"}
            removed = product_indexer.purge_source(source_id)
            await db.delete(row)
            await db.commit()
            self._queues.pop(source_id, None)
            return {"detached": True, "removed": removed}


ingestion_service = IngestionService()
