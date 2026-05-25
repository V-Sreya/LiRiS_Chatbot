"""Verifies the sitemap-index recursion that unblocks Shopify/Magento stores.

The bug: `sitemap.xml` for SUGAR Cosmetics (and any Shopify/Magento store) is
a sitemap *index* — its top-level <loc> entries point at *other* sitemap files
like `sitemap_products_1.xml`, not at product URLs. The pre-fix discoverer
checked those top-level locs against the product-URL regex and got zero hits.
This test reproduces that exact structure and asserts we now recurse one level
deep and end up with the actual product URLs.
"""

from __future__ import annotations

import pytest

from app.services.ingestion import discoverer


INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://shop.example.com/sitemap_products_1.xml</loc></sitemap>
  <sitemap><loc>https://shop.example.com/sitemap_collections_1.xml</loc></sitemap>
  <sitemap><loc>https://shop.example.com/sitemap_blogs_1.xml</loc></sitemap>
  <sitemap><loc>https://shop.example.com/sitemap_pages_1.xml</loc></sitemap>
</sitemapindex>
"""

PRODUCTS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://shop.example.com/products/red-lipstick</loc></url>
  <url><loc>https://shop.example.com/products/blue-mascara</loc></url>
  <url><loc>https://shop.example.com/about-us</loc></url>
</urlset>
"""

COLLECTIONS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://shop.example.com/products/green-eyeshadow</loc></url>
  <url><loc>https://shop.example.com/collections/summer</loc></url>
</urlset>
"""

BLOG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://shop.example.com/blogs/how-to-apply</loc></url>
</urlset>
"""


class _StubResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class _StubClient:
    """httpx.AsyncClient stand-in that serves a fixed URL→XML map."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    async def get(self, url, **_kwargs):
        self.calls.append(url)
        text = self.mapping.get(url)
        if text is None:
            return _StubResponse(404, "")
        return _StubResponse(200, text)


@pytest.mark.asyncio
async def test_sitemap_index_recurses_into_product_sitemap():
    mapping = {
        "https://shop.example.com/sitemap.xml": INDEX_XML,
        "https://shop.example.com/sitemap_products_1.xml": PRODUCTS_XML,
        "https://shop.example.com/sitemap_collections_1.xml": COLLECTIONS_XML,
        "https://shop.example.com/sitemap_blogs_1.xml": BLOG_XML,
    }
    client = _StubClient(mapping)
    found = await discoverer.discover_via_sitemap(
        client, "https://shop.example.com/", max_urls=10
    )
    # Three product URLs across products + collections sitemaps; non-product
    # URLs (about-us, /collections/summer) and the blog sitemap entries are
    # excluded by _is_product_url + the blog skip rule.
    assert sorted(found) == sorted(
        [
            "https://shop.example.com/products/red-lipstick",
            "https://shop.example.com/products/blue-mascara",
            "https://shop.example.com/products/green-eyeshadow",
        ]
    )
    # Confirms we actually skipped the blog sitemap — the regression we're
    # guarding against would have shown the blog URL in `calls`.
    assert "https://shop.example.com/sitemap_blogs_1.xml" not in client.calls


@pytest.mark.asyncio
async def test_sitemap_index_respects_max_urls():
    mapping = {
        "https://shop.example.com/sitemap.xml": INDEX_XML,
        "https://shop.example.com/sitemap_products_1.xml": PRODUCTS_XML,
        "https://shop.example.com/sitemap_collections_1.xml": COLLECTIONS_XML,
    }
    client = _StubClient(mapping)
    found = await discoverer.discover_via_sitemap(
        client, "https://shop.example.com/", max_urls=2
    )
    assert len(found) == 2


@pytest.mark.asyncio
async def test_flat_sitemap_still_works():
    """The original (non-index) code path must not regress for sites that ship
    a flat sitemap.xml."""
    mapping = {"https://shop.example.com/sitemap.xml": PRODUCTS_XML}
    client = _StubClient(mapping)
    found = await discoverer.discover_via_sitemap(
        client, "https://shop.example.com/", max_urls=10
    )
    assert set(found) == {
        "https://shop.example.com/products/red-lipstick",
        "https://shop.example.com/products/blue-mascara",
    }
    # Only the root sitemap should have been fetched — no recursion.
    assert client.calls == ["https://shop.example.com/sitemap.xml"]


@pytest.mark.asyncio
async def test_missing_sitemap_returns_empty():
    client = _StubClient({})
    found = await discoverer.discover_via_sitemap(
        client, "https://shop.example.com/", max_urls=10
    )
    assert found == []
