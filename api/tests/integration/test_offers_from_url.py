import pytest

pytest.importorskip("httpx")

import app.services.offer_service as offer_service
from app.services.url_safety import UnsafeUrlError, safe_fetch


def test_unsafe_url_returns_422(client):
    r = client.post("/api/v1/offers/from-url", json={"url": "http://127.0.0.1/secret"})
    assert r.status_code == 422


def test_happy_path_public(monkeypatch, client):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda h, p: [(None, None, None, None, ("93.184.216.34", 0))])

    # offer_service imported safe_fetch by value, so the patch has to target
    # the name it actually calls.
    monkeypatch.setattr(offer_service, "safe_fetch", lambda url, **kw: b"<html>job</html>")

    r = client.post("/api/v1/offers/from-url", json={"url": "http://example.com/job"})
    assert r.status_code == 202
    body = r.json()
    assert body["existing"] is False
    assert body["job_id"] is not None


def test_idempotence_normalized_url(monkeypatch, client):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda h, p: [(None, None, None, None, ("93.184.216.34", 0))])
    monkeypatch.setattr(offer_service, "safe_fetch", lambda url, **kw: b"<html>job</html>")

    r1 = client.post("/api/v1/offers/from-url", json={"url": "http://example.com/job/"})
    r2 = client.post("/api/v1/offers/from-url", json={"url": "http://example.com/job"})
    assert r1.status_code == 202
    assert r2.status_code == 202
    b1 = r1.json()
    b2 = r2.json()
    assert b1["existing"] is False
    assert b2["existing"] is True
    assert b2["offer_id"] is not None


def test_idempotence_content_hash(monkeypatch, client):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda h, p: [(None, None, None, None, ("93.184.216.34", 0))])

    # First request fetches content A; second fetches different URL but same content.
    contents = iter([b"<html>same content</html>", b"<html>same content</html>"])
    monkeypatch.setattr(offer_service, "safe_fetch", lambda url, **kw: next(contents))

    r1 = client.post("/api/v1/offers/from-url", json={"url": "http://example.com/a"})
    r2 = client.post("/api/v1/offers/from-url", json={"url": "http://example.com/b"})
    assert r1.status_code == 202
    assert r2.status_code == 202
    b2 = r2.json()
    assert b2["existing"] is True
    assert b2["offer_id"] is not None


def test_redirect_to_private_rejected(monkeypatch):
    import socket

    def fake_getaddrinfo(host, port):
        if host == "evil.example":
            return [(None, None, None, None, ("93.184.216.34", 0))]
        if host == "127.0.0.1":
            return [(None, None, None, None, ("127.0.0.1", 0))]
        return [(None, None, None, None, ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    # Simulate a redirect response pointing to a private address by monkeypatching opener.
    import urllib.request

    class _Resp:
        status = 302
        headers = {"Location": "http://127.0.0.1/secret"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, *a):
            return b""

    class _Opener:
        def open(self, req, timeout=None):
            return _Resp()

    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: _Opener())

    with pytest.raises(UnsafeUrlError):
        safe_fetch("http://evil.example/start")
