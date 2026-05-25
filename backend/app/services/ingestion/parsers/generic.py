from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from app.services.ingestion.parsers.base import (
    ParseError,
    Parser,
    clean_text,
    parse_price,
)


class GenericHtmlParser(Parser):
    name = "generic-v1"
    confidence = 0.4

    def parse(self, url: str, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")

        title = None
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            title = clean_text(og_title["content"])
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = clean_text(h1.get_text(" ", strip=True))
        if not title and soup.title:
            title = clean_text(soup.title.get_text(strip=True))
        if not title:
            raise ParseError("Generic: no title found")

        description = None
        og_desc = soup.find("meta", attrs={"property": "og:description"}) or soup.find(
            "meta", attrs={"name": "description"}
        )
        if og_desc and og_desc.get("content"):
            description = clean_text(og_desc["content"])

        price = currency = None
        price_meta = soup.find("meta", attrs={"property": "product:price:amount"})
        currency_meta = soup.find("meta", attrs={"property": "product:price:currency"})
        if price_meta and price_meta.get("content"):
            price, _ = parse_price(price_meta["content"])
        if currency_meta and currency_meta.get("content"):
            currency = currency_meta["content"]

        if price is None:
            price_el = soup.find(attrs={"itemprop": "price"})
            if price_el:
                content = price_el.get("content") or price_el.get_text(" ", strip=True)
                price, sym_curr = parse_price(content)
                currency = currency or sym_curr

        images: list[str] = []
        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image and og_image.get("content"):
            images.append(og_image["content"])

        return {
            "url": url,
            "sku": None,
            "title": title,
            "brand": None,
            "description": description,
            "price": price,
            "list_price": None,
            "currency": currency,
            "availability": "unknown",
            "rating": None,
            "rating_count": None,
            "specs": {},
            "images": images,
            "breadcrumbs": [],
            "fetched_at": Parser.now_iso(),
            "parser_name": self.name,
            "parser_confidence": self.confidence,
        }
