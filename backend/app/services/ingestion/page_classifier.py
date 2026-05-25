import re
from typing import Literal
from urllib.parse import urlparse

from bs4 import BeautifulSoup

PageType = Literal["product", "listing", "category", "home"]

AMAZON_PRODUCT_RE = re.compile(r"/(?:dp|gp/product)/[A-Z0-9]{10}")
FLIPKART_PRODUCT_RE = re.compile(r"/p/[A-Za-z0-9]+(?:\?|$)")


def classify(url: str, html: str | None = None) -> PageType:
    parsed = urlparse(url)
    path = parsed.path or "/"
    host = (parsed.hostname or "").lower()

    if "amazon." in host:
        if AMAZON_PRODUCT_RE.search(path):
            return "product"
        if path.startswith("/s") or "k=" in (parsed.query or ""):
            return "listing"
    if "flipkart." in host:
        if FLIPKART_PRODUCT_RE.search(parsed.path + ("?" if parsed.query else "")):
            return "product"
        if path.startswith("/search") or path.startswith("/s/"):
            return "listing"

    if html:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all("script", type="application/ld+json"):
            txt = tag.string or ""
            if '"@type"' in txt and "Product" in txt:
                return "product"
        if soup.find(attrs={"itemtype": re.compile("schema.org/Product")}):
            return "product"

    if path in ("", "/"):
        return "home"
    return "category"
