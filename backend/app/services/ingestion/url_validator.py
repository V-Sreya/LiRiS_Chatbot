import ipaddress
import socket
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = (
    "ManusChatbot-Ingestor/1.0 "
    "(+https://github.com/Manus-chatbot; contact: aarcbala@gmail.com)"
)
ALLOWED_SCHEMES = {"http", "https"}
ROBOTS_CACHE_TTL = 24 * 3600


class ValidationError(Exception):
    pass


class URLValidator:
    def __init__(self) -> None:
        self._robots_cache: dict[str, tuple[float, RobotFileParser]] = {}

    @staticmethod
    def _is_private_host(host: str) -> bool:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            raise ValidationError(f"Could not resolve host: {host}")
        for info in infos:
            ip = info[4][0]
            try:
                addr = ipaddress.ip_address(ip)
            except ValueError:
                continue
            if (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_reserved
                or addr.is_multicast
            ):
                return True
        return False

    def validate(self, url: str) -> str:
        if not url or not isinstance(url, str):
            raise ValidationError("URL is required")
        parsed = urlparse(url.strip())
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise ValidationError(
                f"Unsupported scheme '{parsed.scheme}'. Only http/https allowed."
            )
        if not parsed.netloc:
            raise ValidationError("URL is missing a host")
        if self._is_private_host(parsed.hostname or ""):
            raise ValidationError("Refusing to fetch private/loopback host")
        return parsed.geturl()

    def _robots(self, scheme: str, host: str) -> RobotFileParser:
        key = f"{scheme}://{host}"
        now = time.time()
        cached = self._robots_cache.get(key)
        if cached and now - cached[0] < ROBOTS_CACHE_TTL:
            return cached[1]
        rp = RobotFileParser()
        rp.set_url(f"{key}/robots.txt")
        try:
            with httpx.Client(
                timeout=5.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
            ) as client:
                resp = client.get(f"{key}/robots.txt")
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    rp.parse([])
        except Exception:
            rp.parse([])
        self._robots_cache[key] = (now, rp)
        return rp

    def is_allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        rp = self._robots(parsed.scheme, parsed.netloc)
        return rp.can_fetch(USER_AGENT, url)
