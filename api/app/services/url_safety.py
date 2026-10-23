"""SSRF guard helpers for user-supplied URLs."""

from __future__ import annotations

import ipaddress
import socket
import urllib.request
from typing import Iterable
import urllib.parse
from urllib.parse import urlparse, urlunparse


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

_BLOCKED_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


class UnsafeUrlError(ValueError):
    """Raised when a URL fails SSRF safety checks."""


def _is_unsafe_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast:
        return True
    for net in _BLOCKED_NETWORKS:
        if addr in net:
            return True
    if str(addr) == "169.254.169.254":
        return True
    return False


def normalize_url(url: str) -> str:
    """Normalize a URL for idempotent comparison: trim, lowercase host, strip trailing slash."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    # Rebuild netloc preserving port
    netloc = host
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    path = parsed.path.rstrip("/") if parsed.path not in ("", "/") else ""
    return urlunparse((parsed.scheme.lower(), netloc, path, parsed.params, parsed.query, ""))


def _resolve_and_check(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"could not resolve hostname: {exc}") from exc
    if not infos:
        raise UnsafeUrlError("could not resolve hostname")
    ips = [str(info[4][0]) for info in infos]
    for ip in ips:
        if _is_unsafe_ip(ip):
            raise UnsafeUrlError("resolved address is not publicly routable")
    return ips


def validate_url(url: str) -> str:
    """Validate a user-supplied URL against SSRF rules. Returns normalized URL or raises UnsafeUrlError."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("only http and https schemes are allowed")
    if not parsed.hostname:
        raise UnsafeUrlError("missing hostname")
    _resolve_and_check(parsed.hostname)
    return normalize_url(url)


def safe_fetch(url: str, *, max_redirects: int = 5, timeout: float = 10.0, max_bytes: int = 5 * 1024 * 1024) -> bytes:
    """Fetch a URL following redirects manually, re-validating every hop and guarding against DNS rebinding."""
    current = url
    pinned_ips: dict[str, list[str]] = {}
    for _ in range(max_redirects + 1):
        parsed = urlparse(current)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise UnsafeUrlError("invalid url")
        hostname = parsed.hostname
        # Resolve once per hostname; block if IP changes (DNS rebinding).
        if hostname not in pinned_ips:
            pinned_ips[hostname] = _resolve_and_check(hostname)
        else:
            fresh = _resolve_and_check(hostname)
            if fresh != pinned_ips[hostname]:
                raise UnsafeUrlError("dns rebinding detected: resolved ip changed")
        # Perform a single non-redirecting request using an opener that does not auto-redirect.
        req = urllib.request.Request(current, method="GET")
        opener = urllib.request.build_opener(_NoRedirectHandler())
        try:
            with opener.open(req, timeout=timeout) as resp:
                # Check for redirect
                if resp.status in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        raise UnsafeUrlError("redirect without location")
                    current = urllib.parse.urljoin(current, location)
                    continue
                # Read in bounded chunks to avoid memory blowup on unbounded streams.
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise UnsafeUrlError("response too large")
                    chunks.append(chunk)
                return b"".join(chunks)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location")
                if not location:
                    raise UnsafeUrlError("redirect without location")
                current = urllib.parse.urljoin(current, location)
                continue
            raise
    raise UnsafeUrlError("too many redirects")
