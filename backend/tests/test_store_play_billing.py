"""Google Play one-time products through RevenueCat: webhook + client verify must credit a purchase exactly once."""
import json

import pytest

from app.core.config import settings
from app.domain import store as S
from tests.conftest import register

pytestmark = pytest.mark.asyncio


class _FakeResp:
    def __init__(self, payload: dict):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


def _fake_rc(subscriber: dict):
    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, headers=None):
            return _FakeResp({"subscriber": subscriber})

    return _Client


async def test_webhook_then_verify_credits_once(client, monkeypatch):
    u = await register(client)
    h, pid = u["headers"], u["player_id"]
    order_id = f"GPA.{pid[-8:]}-0001"
    ok_h = {"Authorization": f"Bearer {settings.RC_WEBHOOK_TOKEN}", "Content-Type": "application/json"}
    ev = {"event": {"id": f"evg_{pid}", "type": "NON_RENEWING_PURCHASE", "app_user_id": pid, "product_id": "idle1.rubies.120", "store": "PLAY_STORE", "transaction_id": order_id}}
    assert (await client.post("/purchases/revenuecat/webhook", content=json.dumps(ev), headers=ok_h)).status_code == 200
    before = (await client.get("/profile", headers=h)).json()["resources"]["rubies"]

    # REST v1 subscriber payload: `id` is RevenueCat's own id, `store_transaction_id` is the Google order id
    monkeypatch.setattr(settings, "RC_SECRET", "sk_test_dummy")
    monkeypatch.setattr(S.httpx, "AsyncClient", _fake_rc({"non_subscriptions": {"idle1.rubies.120": [{"id": "o1_rcInternalId", "store": "play_store", "store_transaction_id": order_id}]}, "subscriptions": {}}))
    v = await client.post("/purchases/verify", json={"product_id": "idle1.rubies.120", "store": "play_store"}, headers=h)
    assert v.status_code == 200, v.text
    assert v.json()["restored"][0]["duplicate"] is True
    assert (await client.get("/profile", headers=h)).json()["resources"]["rubies"] == before


async def test_verify_first_then_webhook_credits_once(client, monkeypatch):
    u = await register(client)
    h, pid = u["headers"], u["player_id"]
    order_id = f"GPA.{pid[-8:]}-0002"
    start = (await client.get("/profile", headers=h)).json()["resources"]["rubies"]
    monkeypatch.setattr(settings, "RC_SECRET", "sk_test_dummy")
    monkeypatch.setattr(S.httpx, "AsyncClient", _fake_rc({"non_subscriptions": {"idle1.rubies.700": [{"id": "o1_rcOther", "store": "play_store", "store_transaction_id": order_id}]}, "subscriptions": {}}))
    v = await client.post("/purchases/verify", json={}, headers=h)
    assert v.status_code == 200 and v.json()["restored"][0]["duplicate"] is False
    assert (await client.get("/profile", headers=h)).json()["resources"]["rubies"] == start + 700

    ok_h = {"Authorization": f"Bearer {settings.RC_WEBHOOK_TOKEN}", "Content-Type": "application/json"}
    ev = {"event": {"id": f"evg2_{pid}", "type": "NON_RENEWING_PURCHASE", "app_user_id": pid, "product_id": "idle1.rubies.700", "store": "PLAY_STORE", "transaction_id": order_id}}
    assert (await client.post("/purchases/revenuecat/webhook", content=json.dumps(ev), headers=ok_h)).status_code == 200
    assert (await client.get("/profile", headers=h)).json()["resources"]["rubies"] == start + 700
