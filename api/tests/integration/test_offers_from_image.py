import io

import pytest

pytest.importorskip("httpx")

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_valid_image_returns_202(client):
    r = client.post(
        "/api/v1/offers/from-image",
        files={"file": ("shot.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert r.status_code == 202
    assert r.json()["job_id"] is not None


def test_invalid_mime_returns_422(client):
    r = client.post(
        "/api/v1/offers/from-image",
        files={"file": ("shot.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 422


def test_magic_bytes_mismatch_returns_422(client):
    r = client.post(
        "/api/v1/offers/from-image",
        files={"file": ("shot.png", io.BytesIO(b"not-a-png"), "image/png")},
    )
    assert r.status_code == 422


def test_oversized_returns_422(client):
    big = PNG_BYTES + b"\x00" * (6 * 1024 * 1024)
    r = client.post(
        "/api/v1/offers/from-image",
        files={"file": ("big.png", io.BytesIO(big), "image/png")},
    )
    assert r.status_code == 422


def test_empty_returns_422(client):
    r = client.post(
        "/api/v1/offers/from-image",
        files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
    )
    assert r.status_code == 422
