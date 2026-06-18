from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from app.services.ingestion.parsers.base import (
    ParseError,
    Parser,
    clean_text,
    parse_price,
)


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            txt = clean_text(el.get_text(" ", strip=True))
            if txt:
                return txt
    return None


class FlipkartParser(Parser):
    name = "flipkart-v1"

    def parse(self, url: str, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")

        title = _first_text(soup, ["span.B_NuCI", "h1 span", "h1"])
        if not title:
            raise ParseError("Flipkart: missing title")

        sku = None
        q = parse_qs(urlparse(url).query)
        if q.get("pid"):
            sku = q["pid"][0]

        price_text = _first_text(
            soup, ["div._30jeq3._16Jk6d", "div._30jeq3", "div._16Jk6d"]
        )
        price, currency = parse_price(price_text)
        currency = currency or "INR"

        list_price_text = _first_text(
            soup, ["div._3I9_wc._2p6lqe", "div._3I9_wc"]
        )
        list_price, _ = parse_price(list_price_text)

        availability = "in_stock"
        if soup.select_one("div._16FRp0"):
            availability = "out_of_stock"

        rating = None
        rating_text = _first_text(soup, ["div._3LWZlK"])
        if rating_text:
            try:
                rating = float(re.match(r"[\d.]+", rating_text).group(0))
            except (AttributeError, ValueError):
                rating = None

        rating_count = None
        rc_text = _first_text(soup, ["span._2_R_DZ", "span._13vcmD"])
        if rc_text:
            digits = re.sub(r"[^\d]", "", rc_text)
            if digits:
                try:
                    rating_count = int(digits)
                except ValueError:
                    rating_count = None

        brand = None
        breadcrumbs = []
        for a in soup.select("div._3GIHBu a, a._2whKao"):
            t = clean_text(a.get_text(" ", strip=True))
            if t and t.lower() != "home":
                breadcrumbs.append(t)
        if breadcrumbs:
            brand = breadcrumbs[0]

        images: list[str] = []
        primary = soup.select_one("img._396cs4, img._2r_T1I")
        if primary and primary.get("src"):
            images.append(primary["src"].split("?")[0])
        for img in soup.select("ul._6lhXp4 li img, ul.ZqtVYK li img"):
            src = img.get("src")
            if src:
                clean = src.split("?")[0]
                if clean not in images:
                    images.append(clean)

        specs: dict[str, str] = {}
        for section in soup.select("div._14cfVK"):
            section_title_el = section.select_one("div._3k-BhJ")
            section_prefix = (
                clean_text(section_title_el.get_text(" ", strip=True)) + " — "
                if section_title_el
                else ""
            )
            for row in section.select("table tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    k = clean_text(cells[0].get_text(" ", strip=True))
                    v = clean_text(cells[1].get_text(" ", strip=True))
                    if k and v:
                        specs[f"{section_prefix}{k}"] = v

        description = _first_text(soup, ["div._1mXcCf", "div.RmoJUa"])

        confidence = 0.7
        if price is not None and price > 0 and currency:
            confidence = 0.9

        return {
            "url": url,
            "sku": sku,
            "title": title,
            "brand": brand,
            "description": description,
            "price": price,
            "list_price": list_price,
            "currency": currency,
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
