import re
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.ingestion.fetcher import Fetcher

PRODUCT_URL_PATTERNS = [
    re.compile(r"/dp/[A-Z0-9]{10}"),
    re.compile(r"/gp/product/[A-Z0-9]{10}"),
    re.compile(r"/p/[A-Za-z0-9]+"),
    re.compile(r"/products?/[^/?#]+"),
    re.compile(r"/item/[^/?#]+"),
]


def _is_product_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path or ""
    return any(pat.search(path) for pat in PRODUCT_URL_PATTERNS)


def _same_domain(a: str, b: str) -> bool:
    ha = (urlparse(a).hostname or "").lower()
    hb = (urlparse(b).hostname or "").lower()
    if not ha or not hb:
        return False
    return ha == hb or ha.endswith("." + hb) or hb.endswith("." + ha)


# Child sitemaps we want to follow first when a sitemap-index is encountered.
# Shopify/Magento/WooCommerce split their sitemaps by content type; products
# and collections are where ingestible URLs live. Pages/blogs/agentic almost
# never carry product URLs, so we skip them unless nothing else matches.
_SITEMAP_PRIORITY = ("product", "collection")
_SITEMAP_SKIP = ("blog", "page", "article", "agentic")
_MAX_CHILD_SITEMAPS = 10


async def _fetch_sitemap_xml(
    client: httpx.AsyncClient, url: str
) -> BeautifulSoup | None:
    try:
        resp = await client.get(url, timeout=8.0, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    return BeautifulSoup(resp.text, "lxml-xml")


def _rank_child_sitemap(url: str) -> int:
    """Lower rank = fetch sooner. Products first, blogs/pages last (or skipped)."""
    lower = url.lower()
    if any(s in lower for s in _SITEMAP_SKIP):
        return 9
    for i, keyword in enumerate(_SITEMAP_PRIORITY):
        if keyword in lower:
            return i
    return len(_SITEMAP_PRIORITY)


async def discover_via_sitemap(
    client: httpx.AsyncClient, base_url: str, max_urls: int
) -> list[str]:
    parsed = urlparse(base_url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    soup = await _fetch_sitemap_xml(client, sitemap_url)
    if soup is None:
        return []

    # A <sitemapindex> root means this file just points at other sitemaps
    # (Shopify, Magento, large WooCommerce stores). Recurse one level deep.
    if soup.find("sitemapindex"):
        child_urls = [
            (loc.text or "").strip()
            for loc in soup.find_all("loc")
            if (loc.text or "").strip()
        ]
        child_urls = [u for u in child_urls if _rank_child_sitemap(u) < 9]
        child_urls.sort(key=_rank_child_sitemap)
        child_urls = child_urls[:_MAX_CHILD_SITEMAPS]

        collected: list[str] = []
        seen: set[str] = set()
        for child in child_urls:
            child_soup = await _fetch_sitemap_xml(client, child)
            if child_soup is None:
                continue
            for loc in child_soup.find_all("loc"):
                u = (loc.text or "").strip()
                if not u or u in seen:
                    continue
                if _is_product_url(u) and _same_domain(u, base_url):
                    seen.add(u)
                    collected.append(u)
                if len(collected) >= max_urls:
                    return collected
        return collected

    urls: list[str] = []
    for loc in soup.find_all("loc"):
        u = (loc.text or "").strip()
        if u and _is_product_url(u) and _same_domain(u, base_url):
            urls.append(u)
        if len(urls) >= max_urls:
            break
    return urls


def discover_via_html(
    base_url: str, html: str, max_urls: int
) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    urls: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href or href.startswith(("javascript:", "#", "mailto:")):
            continue
        absolute = urljoin(base_url, href)
        absolute, _ = urldefrag(absolute)
        if not _same_domain(absolute, base_url):
            continue
        if not _is_product_url(absolute):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
        if len(urls) >= max_urls:
            break
    return urls


async def discover(
    client: httpx.AsyncClient,
    fetcher: Fetcher,
    base_url: str,
    base_html: str | None,
    max_pages: int,
) -> list[str]:
    found = await discover_via_sitemap(client, base_url, max_pages)
    if found:
        return found[:max_pages]
    if base_html is None:
        try:
            _, base_html = await fetcher.fetch(client, base_url)
        except Exception:
            return []
    return discover_via_html(base_url, base_html, max_pages)
