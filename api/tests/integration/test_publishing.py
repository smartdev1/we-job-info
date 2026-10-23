import asyncio
import uuid

import pytest

pytest.importorskip("httpx")

from app.models import GeneratedAsset, Offer
from tests.integration.conftest import session_factory

# The state machine only allows nouvelle -> selectionnee -> publiee, so an
# offer must be selected before it can be published.
SELECTED = "selectionnee"


async def _seed_offer(status: str = SELECTED):
    async with session_factory() as session:
        offer = Offer(title="Test", company="ACME", status=status)
        session.add(offer)
        await session.commit()
        await session.refresh(offer)
        return offer.id


async def _seed_offer_with_asset():
    async with session_factory() as session:
        offer = Offer(title="Test", company="ACME", status=SELECTED)
        session.add(offer)
        await session.flush()
        asset = GeneratedAsset(offer_id=offer.id, image_path="/internal/path.png", variant=1)
        session.add(asset)
        await session.commit()
        return offer.id


def test_publish_flow_and_transition(client):
    offer_id = asyncio.run(_seed_offer())
    r = client.post(f"/api/v1/offers/{offer_id}/publish", json={"channel": "export_manuel"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["channel"] == "export_manuel"
    assert body["status"] == "published"


def test_invalid_channel_returns_422(client):
    offer_id = asyncio.run(_seed_offer())
    r = client.post(f"/api/v1/offers/{offer_id}/publish", json={"channel": "whatsapp"})
    assert r.status_code == 422


def test_orphan_asset_id_returns_404(client):
    offer_id = asyncio.run(_seed_offer())
    r = client.post(
        f"/api/v1/offers/{offer_id}/publish",
        json={"asset_id": str(uuid.uuid4()), "channel": "export_manuel"},
    )
    assert r.status_code == 404


def test_publish_refused_from_a_status_that_cannot_be_published(client):
    """A 'nouvelle' offer cannot jump straight to 'publiee'."""
    offer_id = asyncio.run(_seed_offer(status="nouvelle"))
    r = client.post(f"/api/v1/offers/{offer_id}/publish", json={"channel": "export_manuel"})
    assert r.status_code == 409


def test_assets_list(client):
    offer_id = asyncio.run(_seed_offer_with_asset())
    r = client.get(f"/api/v1/offers/{offer_id}/assets")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["image_path"] == "/internal/path.png"
