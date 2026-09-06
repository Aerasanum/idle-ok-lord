"""API contract + Mongo integration + concurrency/idempotency for the core loop (I01-I10)."""
import asyncio

import pytest

from app.core import db
from tests.conftest import grant, register, shift

pytestmark = pytest.mark.asyncio


async def test_auth_lifecycle(client):
    u = await register(client, verified=False)
    me = (await client.get("/auth/me", headers=u["headers"])).json()
    assert me["account"]["email_verified"] is False
    bad = await client.post("/auth/login", json={"email": u["email"], "password": "wrong-password"})
    assert bad.status_code == 401
    # refresh rotation + reuse detection
    r1 = await client.post("/auth/refresh", json={"refresh_token": u["refresh_token"]})
    assert r1.status_code == 200
    reuse = await client.post("/auth/refresh", json={"refresh_token": u["refresh_token"]})
    assert reuse.status_code == 401
    # the reuse revoked the whole family: the rotated token must also be dead
    r2 = await client.post("/auth/refresh", json={"refresh_token": r1.json()["refresh_token"]})
    assert r2.status_code == 401
    # verified-only gate
    chat = await client.post("/chat/messages", json={"channel": "global:it", "text": "hi"}, headers=u["headers"])
    assert chat.status_code == 403
    code = (await client.get(f"/_test/last-code?email={u['email']}")).json()["code"]
    assert (await client.post("/auth/verify-email", json={"code": "000000" if code != "000000" else "111111"}, headers=u["headers"])).status_code == 400
    assert (await client.post("/auth/verify-email", json={"code": code}, headers=u["headers"])).status_code == 200
    # password reset flow
    await client.post("/auth/forgot-password", json={"email": u["email"]})
    rcode = (await client.get(f"/_test/last-code?email={u['email']}&kind=reset")).json()["code"]
    assert (await client.post("/auth/reset-password", json={"email": u["email"], "code": rcode, "new_password": "AnotherPass!2026"})).status_code == 200
    assert (await client.get("/auth/me", headers=u["headers"])).status_code == 401  # token_version bumped
    login = await client.post("/auth/login", json={"email": u["email"], "password": "AnotherPass!2026"})
    assert login.status_code == 200
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.post("/auth/logout-all", headers=h)).status_code == 200
    assert (await client.get("/auth/me", headers=h)).status_code == 401


async def test_register_validation():
    from httpx import ASGITransport, AsyncClient
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api") as c:
        r = await c.post("/auth/register", json={"email": "x@example.com", "password": "short", "display_name": "Ab", "age_confirmed": True, "consent": True})
        assert r.status_code == 400
        r = await c.post("/auth/register", json={"email": "x2@example.com", "password": "StrongPass!2026", "display_name": "Lord", "age_confirmed": False, "consent": True})
        assert r.status_code == 403


async def test_battle_attempt_claim_idempotent_and_concurrent(client):
    u = await register(client)
    h = u["headers"]
    prof = (await client.get("/profile", headers=h)).json()
    assert prof["combat"]["total_power"] == 100 and prof["resources"]["gold"] == 300
    att = (await client.post("/battle/attempt", json={"stage": 1}, headers=h)).json()["attempt"]
    assert att["win"] is True and att["required_power"] == 75
    early = await client.post("/battle/claim", json={"attempt_id": att["id"]}, headers=h)
    assert early.status_code == 425
    await shift(client, h, 200)
    results = await asyncio.gather(*[client.post("/battle/claim", json={"attempt_id": att["id"]}, headers=h) for _ in range(8)])
    bodies = [r.json() for r in results if r.status_code == 200]
    assert len(bodies) >= 1 and all(b == bodies[0] for b in bodies)
    prof2 = (await client.get("/profile", headers=h)).json()
    assert prof2["resources"]["gold"] == 300 + att["rewards"]["gold"]  # credited exactly once
    assert prof2["campaign"]["highest_cleared"] == 1 and prof2["domain"]["owned"] == 1
    locked = await client.post("/battle/attempt", json={"stage": 5}, headers=h)
    assert locked.status_code == 400
    ledger = await db.ledgers.find_one({"_id": f"battle:{att['id']}"})
    assert ledger["status"] == "applied"


async def test_failure_gives_partial_rewards_and_repeat_farm(client):
    u = await register(client)
    h = u["headers"]
    await grant(client, h, highest_cleared=4)
    att = (await client.post("/battle/attempt", json={"stage": 5}, headers=h)).json()["attempt"]  # elite at 122 > 100 power
    assert att["win"] is False and att["rewards"]["soft"] == 0 and att["rewards"]["gold"] > 0
    await shift(client, h, 200)
    c = (await client.post("/battle/claim", json={"attempt_id": att["id"]}, headers=h)).json()
    assert c["win"] is False and c["highest_cleared"] == 4
    rep = (await client.post("/battle/attempt", json={"stage": 2}, headers=h)).json()["attempt"]
    assert rep["first_clear"] is False and rep["rewards"]["xp"] > 0


async def test_kingdom_queue_costs_and_timers(client):
    u = await register(client)
    h = u["headers"]
    k = (await client.get("/kingdom", headers=h)).json()
    farm = next(b for b in k["buildings"] if b["key"] == "farm")
    # canonical buildings.farm level 2 row
    assert farm["level"] == 1 and farm["next"]["cost"] == {"clay": 100, "gold": 10, "grain": 120, "iron": 20, "wood": 180} and farm["next"]["minutes"] == 2
    up = await client.post("/kingdom/upgrade", json={"building": "farm"}, headers=h)
    assert up.status_code == 200
    again = await client.post("/kingdom/upgrade", json={"building": "farm"}, headers=h)
    assert again.status_code == 409  # already queued
    second = await client.post("/kingdom/upgrade", json={"building": "lumberyard"}, headers=h)
    assert second.status_code == 409 and second.json()["detail"]["code"] == "queue_full"
    poor = await client.post("/kingdom/upgrade", json={"building": "castle"}, headers=h)
    assert poor.status_code in (409,)  # queue full or insufficient
    prof = (await client.get("/profile", headers=h)).json()
    assert prof["resources"]["grain"] == 1500 - 120 and prof["resources"]["gold"] == 300 - 10
    await shift(client, h, 60 * 60)
    k2 = (await client.get("/kingdom", headers=h)).json()
    assert next(b for b in k2["buildings"] if b["key"] == "farm")["level"] == 2
    # production accrued into the offline chest for the 1h gap (gap > online window)
    off = (await client.get("/offline", headers=h)).json()
    assert off["hours"] > 0.9 and off["production"]["grain"] > 0
    o1 = await client.post("/offline/claim", headers=h)
    assert o1.status_code == 200
    o2 = await client.post("/offline/claim", headers=h)
    assert o2.status_code == 400  # nothing left; first claim consumed the chest


async def test_concurrent_forge_never_overspends(client):
    u = await register(client)
    h = u["headers"]
    await grant(client, h, highest_cleared=9, hero_level=10)  # hero L10 power 264 > boss 10 required 210
    # first-clear boss stage 10 guarantees one item (battle.gear_drop.boss_guaranteed_items)
    att = (await client.post("/battle/attempt", json={"stage": 10}, headers=h)).json()["attempt"]
    assert att["win"] is True and att["kind"] == "boss" and len(att["drops"]) >= 1
    await shift(client, h, 300)
    await client.post("/battle/claim", json={"attempt_id": att["id"]}, headers=h)
    inv = (await client.get("/gear/inventory", headers=h)).json()
    slot = next((s for s, v in inv["equipped"].items() if v), None)
    assert slot, "boss stage 10 guarantees an item"
    costs = (await client.get("/forge/costs", headers=h)).json()
    one = costs[slot]["next_cost"]
    await db.players.update_one({"_id": u["player_id"]}, {"$set": {"resources.gold": one["gold"], "resources.forge_dust": one["forge_dust"] * 10}})
    rs = await asyncio.gather(*[client.post("/forge/upgrade", json={"slot": slot}, headers=h) for _ in range(6)])
    ok = [r for r in rs if r.status_code == 200]
    assert len(ok) == 1
    prof = (await client.get("/profile", headers=h)).json()
    assert prof["resources"]["gold"] == 0 and prof["forge"][slot] == 1


async def test_research_army_formation_rules(client):
    u = await register(client)
    h = u["headers"]
    await grant(client, h, resources={"gold": 100000, "grain": 100000, "wood": 100000, "clay": 100000, "iron": 100000}, castle_level=3, highest_cleared=10)
    r = await client.post("/research/start", json={"node": "military.infantry_drill"}, headers=h)
    assert r.status_code == 200
    assert (await client.post("/research/start", json={"node": "economy.crop_yield"}, headers=h)).status_code == 409  # single research queue
    gated = await client.post("/research/start", json={"node": "mythic.draconic_lore"}, headers=h)  # castle 4 gate
    assert gated.status_code == 403
    rec = await client.post("/army/recruit", json={"unit": "infantry", "quantity": 30}, headers=h)
    assert rec.status_code == 200 and rec.json()["cost"] == {"clay": 300, "gold": 30, "grain": 450, "iron": 150, "wood": 300}
    assert (await client.post("/army/recruit", json={"unit": "dragon", "quantity": 1}, headers=h)).status_code == 403
    bad = await client.put("/army/formation", json={"formation": {"infantry": 30}}, headers=h)
    assert bad.status_code == 400  # not recruited yet
    await shift(client, h, 3600)  # recruit (30 min) and infantry_drill L1 (10 min) both complete
    a = (await client.get("/army", headers=h)).json()
    assert next(x for x in a["units"] if x["key"] == "infantry")["owned"] == 30
    ok = await client.put("/army/formation", json={"formation": {"infantry": 30}}, headers=h)
    assert ok.status_code == 200 and ok.json()["command_used"] == 30
    prof = (await client.get("/profile", headers=h)).json()
    assert prof["research"]["military.infantry_drill"] == 1
    assert prof["combat"]["army_power"] == round(30 * 37 * 1.03) and prof["combat"]["total_power"] == prof["combat"]["hero"]["power"] + round(30 * 37 * 1.03)
    assert prof["army_visual_tier"]["tier"] >= 1


async def test_talents_and_skills(client):
    u = await register(client)
    h = u["headers"]
    await grant(client, h, hero_level=10)
    t = await client.post("/hero/talents", json={"branch": "warrior"}, headers=h)
    assert t.status_code == 200 and t.json()["points_total"] == 2
    await client.post("/hero/talents", json={"branch": "warrior"}, headers=h)
    assert (await client.post("/hero/talents", json={"branch": "warrior"}, headers=h)).status_code == 403
    s = await client.put("/hero/skills", json={"slots": ["power_strike", None, None]}, headers=h)  # slot 1 unlocks at L10
    assert s.status_code == 200
    assert (await client.put("/hero/skills", json={"slots": ["power_strike", "war_cry", None]}, headers=h)).status_code == 403  # slot 2 unlocks at L30
    assert (await client.put("/hero/skills", json={"slots": ["shield_wall", None, None]}, headers=h)).status_code == 400  # skill unlocks at L30
    prof = (await client.get("/profile", headers=h)).json()
    assert prof["combat"]["hero"]["attack"] == round((20 + 9 * 5) * 1.04)  # 2 warrior ranks = +4% attack


async def test_account_export_and_delete(client):
    u = await register(client)
    h = u["headers"]
    ex = await client.get("/account/export", headers=h)
    assert ex.status_code == 200 and "player" in ex.json() and "gear_items" in ex.json()
    d = await client.post("/account/delete", json={"password": "StrongPass!2026", "confirm": "DELETE"}, headers=h)
    assert d.status_code == 200
    assert (await client.get("/profile", headers=h)).status_code == 401
    acc = await db.accounts.find_one({"_id": u["account"]["id"]})
    assert acc["deleted_at"] is not None and acc["email"].endswith("@deleted.invalid")
