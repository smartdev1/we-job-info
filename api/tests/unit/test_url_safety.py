import socket

import pytest

from app.services.url_safety import (
    UnsafeUrlError,
    normalize_url,
    validate_url,
    _is_unsafe_ip,
)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254", "0.0.0.0", "::1", "fe80::1", "fc00::1"])
def test_is_unsafe_ip_blocks_private_and_special(ip):
    assert _is_unsafe_ip(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
def test_is_unsafe_ip_allows_public(ip):
    assert _is_unsafe_ip(ip) is False


def test_validate_url_rejects_bad_scheme():
    with pytest.raises(UnsafeUrlError):
        validate_url("ftp://example.com/x")
    with pytest.raises(UnsafeUrlError):
        validate_url("file:///etc/passwd")


def test_validate_url_rejects_missing_host():
    with pytest.raises(UnsafeUrlError):
        validate_url("http:///path")


def test_validate_url_rejects_private_ip(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda h, p: [(None, None, None, None, ("127.0.0.1", 0))])
    with pytest.raises(UnsafeUrlError):
        validate_url("http://evil.example/x")


def test_validate_url_rejects_metadata_ip(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda h, p: [(None, None, None, None, ("169.254.169.254", 0))])
    with pytest.raises(UnsafeUrlError):
        validate_url("http://metadata.example/x")


def test_validate_url_accepts_public(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda h, p: [(None, None, None, None, ("93.184.216.34", 0))])
    assert validate_url("http://example.com/path/") == "http://example.com/path"


def test_normalize_url_idempotent():
    u = "HTTPS://Example.com/Foo/?q=1"
    n1 = normalize_url(u)
    n2 = normalize_url(n1)
    assert n1 == n2


def test_dns_rebinding_detected(monkeypatch):
    from app.services.url_safety import safe_fetch

    calls = {"n": 0}

    def fake_getaddrinfo(h, p):
        calls["n"] += 1
        ip = "93.184.216.34" if calls["n"] == 1 else "10.0.0.1"
        return [(None, None, None, None, (ip, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    class DummyResp:
        status = 302
        headers = {"Location": "http://example.com/next"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    # Patch opener to return redirect once then stop
    import urllib.request

    class FakeOpener:
        def open(self, req, timeout=None):
            return DummyResp()

    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: FakeOpener())
    with pytest.raises(UnsafeUrlError):
        safe_fetch("http://example.com/start")