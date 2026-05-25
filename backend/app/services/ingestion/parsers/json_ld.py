from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup

from app.services.ingestion.parsers.base import (
    ParseError,
    Parser,
    clean_text,
    parse_price,
)


def _walk_ld(blob: Any):
    if isinstance(blob, list):
        for item in blob:
            yield from _walk_ld(item)
    elif isinstance(blob, dict):
        if "@graph" in blob and isinstance(blob["@graph"], list):
            for item in blob["@graph"]:
                yield from _walk_ld(item)
        else:
            yield blob


def _find_product(soup: BeautifulSoup) -> dict | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _walk_ld(data):
            t = node.get("@type")
            if isinstance(t, list):
                if "Product" in t:
                    return node
            elif t == "Product":
                return node
    return None


def _decimal(val: Any) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


class JsonLdParser(Parser):
    name = "json-ld"
    confidence = 0.85

    def parse(self, url: str, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        product = _find_product(soup)
        if not product:
            raise ParseError("No JSON-LD Product node found")

        title = clean_text(product.get("name"))
        if not title:
            raise ParseError("JSON-LD Product missing name")

        brand = product.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        description = clean_text(product.get("description"))

        offers = product.get("offers")
        price = currency = availability = None
        list_price = None
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict):
            price = _decimal(offers.get("price"))
            currency = offers.get("priceCurrency")
            avail_url = (offers.get("availability") or "").lower()
            if "instock" in avail_url:
                availability = "in_stock"
            elif "outofstock" in avail_url or "soldout" in avail_url:
                availability = "out_of_stock"
            elif "preorder" in avail_url:
                availability = "preorder"
            list_price = _decimal(offers.get("priceSpecification", {}).get("listPrice")) if isinstance(offers.get("priceSpecification"), dict) else None

        if price is None:
            text_price, sym_currency = parse_price(product.get("price"))
            price = text_price
            currency = currency or sym_currency

        rating = rating_count = None
        agg = product.get("aggregateRating")
        if isinstance(agg, dict):
            try:
                rating = float(agg.get("ratingValue")) if agg.get("ratingValue") else None
            except (TypeError, ValueError):
                rating = None
            try:
                rc_raw = agg.get("reviewCount") or agg.get("ratingCount")
                rating_count = int(rc_raw) if rc_raw is not None else None
            except (TypeError, ValueError):
                rating_count = None

        images_raw = product.get("image") or []
        if isinstance(images_raw, str):
            images_raw = [images_raw]
        images = [u for u in images_raw if isinstance(u, str) and u.startswith("http")]

        sku = product.get("sku") or product.get("mpn") or product.get("productID")

        return {
            "url": url,
            "sku": str(sku) if sku else None,
            "title": title,
            "brand": clean_text(brand) if brand else None,
            "description": description or None,
            "price": price,
            "list_price": list_price,
            "currency": currency,
            "availability": availability or "unknown",
            "rating": rating,
            "rating_count": rating_count,
            "specs": {},
            "images": images,
            "breadcrumbs": [],
            "fetched_at": Parser.now_iso(),
            "parser_name": self.name,
            "parser_confidence": self.confidence,
        }
