import asyncio
import random
from collections import defaultdict
from urllib.parse import urlparse

import httpx

ANTI_BOT_SIGNATURES = (
    "Just a moment...",
    "cf-browser-verification",
    "Attention Required! | Cloudflare",
    "captcha-delivery.com",
    "px-captcha",
    "/_Incapsula_Resource",
    "Access Denied",
    "Pardon Our Interruption",
    # AWS WAF challenge — Amazon serves this for "suspicious" homepage hits.
    # Returns HTTP 202 with a tiny HTML stub that runs a JS token exchange.
    # The previous regex only looked for "/dp/" links and silently produced
    # 0 products; now we recognise the challenge upfront.
    "AwsWafIntegration",
    "awsWafCookieDomainList",
    "challenge.js",
    "token.awswaf.com",
    # Akamai bot-manager challenge
    "_abck",
    "ak_bmsc",
    # Generic captcha indicators
    "verify that you're not a robot",
    "/captcha",
)

# Pool of realistic, modern desktop browser User-Agents. Many ecommerce sites
# (Flipkart, Meesho, etc.) immediately reject our previous "ManusChatbot-
# Ingestor/1.0" UA with a 403, so we present as a normal browser instead.
BROWSER_USER_AGENTS = (
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.2849.46",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
)


def _pick_user_agent() -> str:
    return random.choice(BROWSER_USER_AGENTS)


def _browser_headers(referer: str | None = None) -> dict[str, str]:
    # NOTE: do *not* advertise brotli (`br`). httpx ships with gzip+deflate
    # decoders but no brotli; sites that pick brotli (Vercel/Next.js, many
    # Shopify shops) hand back compressed bytes that we then "parse" as
    # garbage HTML — symptom is "no products discovered" on pages that
    # clearly have `/product/...` links. The previous header set advertised
    # `br` and silently dropped every brotli-served site.
    headers = {
        "User-Agent": _pick_user_agent(),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9,en-IN;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none" if not referer else "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    }
    if referer:
        headers["Referer"] = referer
        headers["Sec-Fetch-Site"] = "same-origin"
    return headers


class AntiBotChallenge(Exception):
    pass


class Fetcher:
    """Async fetcher with per-host concurrency and base delay."""

    def __init__(
        self,
        per_host_concurrency: int = 4,
        base_delay: float = 1.5,
        timeout: float = 20.0,
    ) -> None:
        self.per_host_concurrency = per_host_concurrency
        self.base_delay = base_delay
        self.timeout = timeout
        self._host_semaphores: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(per_host_concurrency)
        )
        self._last_fetched: dict[str, float] = {}

    def _semaphore(self, host: str) -> asyncio.Semaphore:
        return self._host_semaphores[host]

    @staticmethod
    def _detect_anti_bot(text: str) -> bool:
        head = text[:8192]
        return any(sig in head for sig in ANTI_BOT_SIGNATURES)

    async def fetch(
        self, client: httpx.AsyncClient, url: str, attempt: int = 0
    ) -> tuple[int, str]:
        host = urlparse(url).hostname or ""
        sem = self._semaphore(host)
        async with sem:
            jitter = random.uniform(0, 0.6)
            await asyncio.sleep(self.base_delay + jitter)
            # Per-request browser headers — fresh UA each retry helps slip
            # past UA-based blocks.
            headers = _browser_headers()
            try:
                resp = await client.get(
                    url,
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=headers,
                )
            except httpx.HTTPError as e:
                if attempt < 2:
                    backoff = (2**attempt) + random.uniform(0, 0.5)
                    await asyncio.sleep(backoff)
                    return await self.fetch(client, url, attempt + 1)
                raise
            if resp.status_code in (429, 503) and attempt < 3:
                backoff = (2**attempt) + random.uniform(0, 1.0)
                await asyncio.sleep(backoff)
                return await self.fetch(client, url, attempt + 1)
            text = resp.text or ""
            # Detect anti-bot/WAF challenges regardless of HTTP status —
            # AWS WAF returns 202, Cloudflare returns 200/403, Akamai
            # returns 200 with _abck cookies, etc. The status code alone
            # isn't enough.
            challenged = self._detect_anti_bot(text) or resp.status_code in (403, 503)
            if challenged and attempt < 2:
                # Back off and retry with a different UA — sometimes that's
                # enough to slip past UA-keyed throttles.
                backoff = 2.0 + random.uniform(0, 1.0)
                await asyncio.sleep(backoff)
                return await self.fetch(client, url, attempt + 1)
            if challenged:
                raise AntiBotChallenge(
                    f"Anti-bot challenge at {url} (HTTP {resp.status_code})"
                )
            if resp.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}", request=resp.request, response=resp
                )
            return resp.status_code, text


def make_client() -> httpx.AsyncClient:
    """Build an httpx client that looks like a real browser session.

    The default-headers here are starting values; per-request `_browser_headers`
    overrides UA so we can rotate between attempts.
    """
    return httpx.AsyncClient(
        headers=_browser_headers(),
        timeout=20.0,
        http2=False,
    )
