from urllib.parse import urlparse

from app.services.ingestion.parsers.amazon import AmazonParser
from app.services.ingestion.parsers.base import ParseError, Parser
from app.services.ingestion.parsers.flipkart import FlipkartParser
from app.services.ingestion.parsers.generic import GenericHtmlParser
from app.services.ingestion.parsers.json_ld import JsonLdParser

_HOSTNAME_PARSERS: list[tuple[tuple[str, ...], type[Parser]]] = [
    (("amazon.",), AmazonParser),
    (("flipkart.",), FlipkartParser),
]


def select_parsers(url: str) -> list[Parser]:
    """Return ordered parser candidates for a product URL.

    Hostname-specific parsers run first when the URL matches; JSON-LD always
    runs and the generic HTML parser is the final fallback.
    """
    host = (urlparse(url).hostname or "").lower()
    chain: list[Parser] = []
    for tokens, cls in _HOSTNAME_PARSERS:
        if any(t in host for t in tokens):
            chain.append(cls())
    chain.append(JsonLdParser())
    chain.append(GenericHtmlParser())
    return chain


__all__ = [
    "ParseError",
    "Parser",
    "JsonLdParser",
    "AmazonParser",
    "FlipkartParser",
    "GenericHtmlParser",
    "select_parsers",
]
