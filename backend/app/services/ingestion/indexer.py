import hashlib
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import settings

INGESTED_COLLECTION = "ingested_products"


def _format_chunk(p: dict[str, Any]) -> str:
    lines: list[str] = [str(p["title"])]
    if p.get("brand"):
        lines.append(f"Brand: {p['brand']}")
    if p.get("price") is not None:
        price_line = f"Price: {p['price']}"
        if p.get("currency"):
            price_line += f" {p['currency']}"
        if p.get("list_price") is not None:
            price_line += f" (was {p['list_price']})"
        lines.append(price_line)
    if p.get("rating") is not None:
        rc = p.get("rating_count")
        rc_part = f" from {rc} ratings" if rc else ""
        lines.append(f"Rating: {p['rating']}{rc_part}")
    if p.get("availability"):
        lines.append(f"Availability: {p['availability']}")
    if p.get("breadcrumbs"):
        lines.append("Category: " + " > ".join(p["breadcrumbs"]))
    if p.get("specs"):
        lines.append("Specifications:")
        for k, v in p["specs"].items():
            lines.append(f"- {k}: {v}")
    if p.get("description"):
        lines.append("")
        lines.append("Description:")
        lines.append(p["description"])
    lines.append("")
    lines.append(f"Source: {p['url']}")
    return "\n".join(lines)


class ProductIndexer:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=INGESTED_COLLECTION, embedding_function=self.embedding_fn
        )

    @staticmethod
    def _id(source_id: str, sku: str | None, url: str) -> str:
        key = (sku or url).encode("utf-8")
        digest = hashlib.sha256(source_id.encode("utf-8") + key).hexdigest()[:24]
        return f"prod_{digest}"

    def upsert(self, source_id: str, products: list[dict[str, Any]]) -> int:
        if not products:
            return 0
        # Dedupe by computed ID — the same product may surface twice in a
        # listing (sponsored slot + organic slot), and Chroma errors out on
        # duplicate IDs in a single upsert.
        seen_ids: dict[str, dict[str, Any]] = {}
        for p in products:
            pid = self._id(source_id, p.get("sku"), str(p["url"]))
            if pid in seen_ids:
                continue
            seen_ids[pid] = p

        ids: list[str] = []
        docs: list[str] = []
        metas: list[dict[str, Any]] = []
        for pid, p in seen_ids.items():
            ids.append(pid)
            docs.append(_format_chunk(p))
            meta: dict[str, Any] = {
                "source_id": source_id,
                "url": str(p["url"]),
                "sku": p.get("sku") or "",
                "title": p["title"],
                "brand": p.get("brand") or "",
                "currency": p.get("currency") or "",
                "availability": p.get("availability") or "unknown",
                "parser_name": p.get("parser_name", ""),
                "parser_confidence": float(p.get("parser_confidence", 0.0)),
            }
            if p.get("price") is not None:
                try:
                    meta["price"] = float(p["price"])
                except (TypeError, ValueError):
                    pass
            if p.get("rating") is not None:
                meta["rating"] = float(p["rating"])
            metas.append(meta)
        self.collection.upsert(documents=docs, metadatas=metas, ids=ids)
        return len(ids)

    def query(
        self,
        query_text: str,
        source_ids: list[str] | None = None,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        try:
            count = self.collection.count()
        except Exception:
            count = 0
        if count == 0:
            return []
        where: dict[str, Any] | None = None
        if source_ids:
            where = (
                {"source_id": source_ids[0]}
                if len(source_ids) == 1
                else {"source_id": {"$in": source_ids}}
            )
        n = min(n_results, count)
        results = self.collection.query(
            query_texts=[query_text], n_results=n, where=where
        )
        out = []
        docs = results.get("documents") or [[]]
        metas = results.get("metadatas") or [[]]
        dists = results.get("distances") or [[]]
        for i in range(len(docs[0])):
            out.append(
                {
                    "content": docs[0][i],
                    "metadata": metas[0][i],
                    "distance": dists[0][i] if dists and dists[0] else None,
                }
            )
        return out

    def purge_source(self, source_id: str) -> int:
        try:
            existing = self.collection.get(where={"source_id": source_id})
        except Exception:
            return 0
        ids = (existing or {}).get("ids") or []
        if not ids:
            return 0
        self.collection.delete(ids=ids)
        return len(ids)


product_indexer = ProductIndexer()
