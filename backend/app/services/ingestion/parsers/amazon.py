from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from app.services.ingestion.parsers.base import (
    ParseError,
    Parser,
    clean_text,
    parse_price,
)
from app.services.ingestion.parsers.json_ld import JsonLdParser

ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")


def _first_text(soup: BeautifulSoup, selector: str) -> str | None:
    el = soup.select_one(selector)
    if not el:
        return None
    return clean_text(el.get_text(" ", strip=True))


class AmazonParser(Parser):
    name = "amazon-v1"

    def parse(self, url: str, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")

        title = _first_text(soup, "#productTitle") or _first_text(soup, "h1#title")
        if not title:
            raise ParseError("Amazon: missing #productTitle")

        m = ASIN_RE.search(url)
        sku = m.group(1) if m else None

        brand = _first_text(soup, "#bylineInfo")
        if brand:
            brand = re.sub(
                r"^(?:Visit the\s+|Brand:\s*)", "", brand, flags=re.I
            ).strip()
            brand = re.sub(r"\s+Store$", "", brand, flags=re.I)

        price_text = _first_text(
            soup, "span.a-price > span.a-offscreen"
        )
        price, currency = parse_price(price_text)

        list_price_text = _first_text(
            soup, "span.a-price.a-text-price > span.a-offscreen"
        )
        list_price, _ = parse_price(list_price_text)

        rating = None
        rating_el = soup.select_one("span#acrPopover")
        if rating_el and rating_el.get("title"):
            mr = re.match(r"([\d.]+)", rating_el["title"].strip())
            if mr:
                try:
                    rating = float(mr.group(1))
                except ValueError:
                    rating = None

        rating_count = None
        rc_text = _first_text(soup, "#acrCustomerReviewText")
        if rc_text:
            digits = re.sub(r"[^\d]", "", rc_text)
            if digits:
                try:
                    rating_count = int(digits)
                except ValueError:
                    rating_count = None

        availability = "unknown"
        avail_text = _first_text(soup, "#availability span")
        if avail_text:
            low = avail_text.lower()
            if "in stock" in low:
                availability = "in_stock"
            elif "unavailable" in low or "out of stock" in low:
                availability = "out_of_stock"
            elif "pre-order" in low or "preorder" in low:
                availability = "preorder"

        images: list[str] = []
        landing = soup.select_one("#landingImage")
        if landing and landing.get("src"):
            images.append(landing["src"])
        for img in soup.select("#altImages img"):
            src = img.get("src")
            if src and src not in images:
                images.append(src)

        specs: dict[str, str] = {}
        for row in soup.select(
            "#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr"
        ):
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                k = clean_text(cells[0].get_text(" ", strip=True))
                v = clean_text(cells[1].get_text(" ", strip=True))
                if k and v:
                    specs[k] = v
        for li in soup.select("#detailBullets_feature_div li"):
            spans = li.find_all("span")
            if len(spans) >= 2:
                k = clean_text(spans[0].get_text(" ", strip=True)).rstrip(":").strip()
                v = clean_text(spans[1].get_text(" ", strip=True))
                if k and v:
                    specs[k] = v

        breadcrumbs = []
        for li in soup.select("#wayfinding-breadcrumbs_feature_div ul li"):
            t = clean_text(li.get_text(" ", strip=True))
            if t and t not in {"›", "/"}:
                breadcrumbs.append(t)

        description_lines = []
        for li in soup.select("#feature-bullets ul li"):
            t = clean_text(li.get_text(" ", strip=True))
            if t:
                description_lines.append(t)
        description = "\n".join(description_lines) if description_lines else None

        confidence = 0.75
        try:
            ld = JsonLdParser().parse(url, html)
            if ld.get("title") and clean_text(ld["title"]) == clean_text(title):
                confidence = 0.95
            if ld.get("price") and price is None:
                price = ld["price"]
            if ld.get("currency") and not currency:
                currency = ld["currency"]
            if ld.get("description") and not description:
                description = ld["description"]
        except ParseError:
            pass

        return {
            "url": url,
            "sku": sku,
            "title": title,
            "brand": brand,
            "description": description,
            "price": price,
            "list_price": list_price,
            "currency": currency or ("INR" if "amazon.in" in url else None),
            "availability": availability,
            "rating": rating,
            "rating_count": rating_count,
            "specs": specs,
            "images": images,
            "breadcrumbs": breadcrumbs,
            "fetched_at": Parser.now_iso(),
            "parser_name": self.name,
            "parser_confidence": confidence,
        }
