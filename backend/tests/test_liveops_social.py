"""LiveOps, social, wars, Titan Hunt and store webhook tests (I11-I14)."""
import asyncio
import json

import pytest

from app.core import db
from app.core.config import settings
from tests.conftest import grant, register, shift

pytestmark = pytest.mark.asyncio


async def test_events_dungeons_quests(client):
    u = await register(client)
    h = u["headers"]
    await grant(client, h, highest_cleared=40)
    ev = (await client.get("/events", headers=h)).json()
    assert ev["energy"] == 10 and len(ev["deployments_catalog"]) == 4
    dep = (await client.post("/events/deploy", json={"index": 0}, headers=h)).json()
    assert (await client.post("/events/deploy", json={"index": 0}, headers=h)).status_code == 409
    assert (await client.post("/events/claim", json={"id": dep["id"]}, headers=h)).status_code == 425
    await shift(client, h, 3600)
    c1 = (await client.post("/events/claim", json={"id": dep["id"]}, headers=h)).json()
    c2 = (await client.post("/events/claim", json={"id": dep["id"]}, headers=h)).json()
    assert c1 == c2 and c1["event_tokens"] == round(20 + 40 * 0.35)
    ev2 = (await client.get("/events", headers=h)).json()
    assert ev2["track"]["points"] == c1["event_tokens"] and ev2["energy"] == 9  # deployment[0] costs 1 energy
    prem = await client.post("/events/track/claim", json={"tier": 1, "premium": True}, headers=h)
    assert prem.status_code == 403  # no Event Pass
    # dungeons: tier 2 unlocked at stage 40
    d = (await client.get("/dungeons", headers=h)).json()
    assert d["max_tier"] == 2
    assert (await client.post("/dungeons/start", json={"key": "forge_depths", "tier": 3}, headers=h)).status_code == 403
    run = (await client.post("/dungeons/start", json={"key": "forge_depths", "tier": 2}, headers=h)).json()
    await shift(client, h, 700)
    r1 = (await client.post("/dungeons/claim", json={"id": run["id"]}, headers=h)).json()
    assert r1["granted"]["forge_dust"] == 80 + 25 * 2
    for _ in range(1):
        run2 = (await client.post("/dungeons/start", json={"key": "forge_depths", "tier": 1}, headers=h)).json()
        await shift(client, h, 700)
        await client.post("/dungeons/claim", json={"id": run2["id"]}, headers=h)
    paid = await client.post("/dungeons/start", json={"key": "forge_depths", "tier": 1}, headers=h)
    assert paid.status_code == 200 and paid.json()["paid"] is True  # 3rd entry is a paid extra entry (25 Rubies of the initial 100)
    assert (await client.get("/profile", headers=h)).json()["resources"]["rubies"] == 100 - 25
    await shift(client, h, 700)
    await client.post("/dungeons/claim", json={"id": paid.json()["id"]}, headers=h)
    await db.players.update_one({"_id": u["player_id"]}, {"$set": {"resources.rubies": 0}})
    broke = await client.post("/dungeons/start", json={"key": "forge_depths", "tier": 1}, headers=h)
    assert broke.status_code == 409 and broke.json()["detail"]["code"] == "insufficient_or_changed"  # paid entry without Rubies
    q = (await client.get("/quests", headers=h)).json()
    assert q["daily"]["tasks"]["event_deployment"]["done"] and q["daily"]["tasks"]["run_dungeon"]["done"]
    lg1 = (await client.post("/quests/login/claim", headers=h)).json()
    assert lg1["day"] == 1 and lg1["rubies"] == 3
    assert (await client.post("/quests/login/claim", headers=h)).status_code == 409
    ach = (await client.get("/achievements", headers=h)).json()
    unlocked = [a for a in ach["achievements"] if a["unlocked"]]
    assert unlocked
    c = (await client.post("/achievements/claim", json={"key": unlocked[0]["key"]}, headers=h)).json()
    assert c["rubies"] == unlocked[0]["rubies"]
    assert (await client.post("/achievements/claim", json={"key": unlocked[0]["key"]}, headers=h)).status_code == 409
    cx = (await client.get("/codex", headers=h)).json()
    assert cx["completion_pct"] >= 0


async def _alliance_with_members(client, n: int, name: str):
    leader = await register(client, name=f"{name}Lead")
    h = leader["headers"]
    await grant(client, h, castle_level=8, resources={"gold": 20000}, highest_cleared=30)
    a = (await client.post("/alliances", json={"name": name, "tag": name[:3].upper(), "join_mode": "open"}, headers=h)).json()
    members = [leader]
    for i in range(n - 1):
        m = await register(client, name=f"{name}{i}")
        await grant(client, m["headers"], castle_level=8, highest_cleared=10 + i)
        j = await client.post("/alliances/join", json={"id": a["id"]}, headers=m["headers"])
        assert j.status_code == 200, j.text
        members.append(m)
    return a, members


async def test_alliance_chat_moderation(client):
    a, members = await _alliance_with_members(client, 3, "Chatters")
    h = members[0]["headers"]
    msg = await client.post("/chat/messages", json={"channel": f"alliance:{a['id']}", "text": "Hello shit lords"}, headers=h)
    assert msg.status_code == 200 and "s***" in msg.json()["text"]
    outsider = await register(client)
    assert (await client.get(f"/chat/messages?channel=alliance:{a['id']}", headers=outsider["headers"])).status_code == 403
    for i in range(5):
        await client.post("/chat/messages", json={"channel": "global:it", "text": f"m{i}"}, headers=h)
    assert (await client.post("/chat/messages", json={"channel": "global:it", "text": "too fast"}, headers=h)).status_code == 429
    # block hides messages for the blocker only
    m2 = members[1]["headers"]
    posted = (await client.post("/chat/messages", json={"channel": f"alliance:{a['id']}", "text": "visible?"}, headers=m2)).json()
    await client.post("/chat/moderate", json={"action": "block", "target_id": members[1]["player_id"]}, headers=h)
    lst = (await client.get(f"/chat/messages?channel=alliance:{a['id']}", headers=h)).json()["messages"]
    assert all(m["id"] != posted["id"] for m in lst)
    # leader can mute and delete
    mute = await client.post("/chat/moderate", json={"action": "mute", "target_id": members[1]["player_id"], "channel": f"alliance:{a['id']}", "minutes": 10}, headers=h)
    assert mute.status_code == 200
    assert (await client.post("/chat/messages", json={"channel": f"alliance:{a['id']}", "text": "muted?"}, headers=m2)).status_code == 403
    assert (await client.post("/chat/moderate", json={"action": "delete", "message_id": posted["id"]}, headers=h)).status_code == 200
    assert (await client.post("/chat/moderate", json={"action": "delete", "message_id": posted["id"]}, headers=members[2]["headers"])).status_code == 403


async def test_war_full_cycle_deterministic_and_idempotent(client):
    a1, m1 = await _alliance_with_members(client, 10, "Wolves")
    a2, m2 = await _alliance_with_members(client, 10, "Bears")
    h1, h2 = m1[0]["headers"], m2[0]["headers"]
    mp = (await client.get("/wars/map", headers=h1)).json()
    assert len(mp["nodes"]) == 361 and sum(1 for n in mp["nodes"] if n["type"] == "home_castle") == 64
    home = mp["my_home"]
    x, y = home % 19, home // 19
    target = next(n for n in mp["nodes"] if abs(n["x"] - x) + abs(n["y"] - y) == 1 and n["owner"] is None)
    too_small = await register(client)
    assert (await client.post("/wars/declare", json={"node_id": target["node_id"]}, headers=too_small["headers"])).status_code == 403
    far = next(n for n in mp["nodes"] if abs(n["x"] - x) + abs(n["y"] - y) > 3 and n["owner"] is None)
    assert (await client.post("/wars/declare", json={"node_id": far["node_id"]}, headers=h1)).status_code == 400
    war = (await client.post("/wars/declare", json={"node_id": target["node_id"]}, headers=h1)).json()
    assert war["status"] == "prep"
    assert (await client.post("/wars/declare", json={"node_id": target["node_id"]}, headers=h1)).status_code == 409  # cooldown/active
    roster = await client.post("/wars/roster", json={"war_id": war["id"], "player_ids": [m["player_id"] for m in m1]}, headers=h1)
    assert roster.status_code == 200
    assert (await client.post("/wars/roster", json={"war_id": war["id"], "player_ids": [m1[0]["player_id"]]}, headers=m1[3]["headers"])).status_code == 403
    await client.post("/_test/war-shift", json={"seconds": 8 * 3600 + 60}, headers=h1)
    t1, t2 = await asyncio.gather(client.post("/_test/tick", headers=h1), client.post("/_test/tick", headers=h1))
    assert t1.status_code == 200 and t2.status_code == 200
    detail = (await client.get(f"/wars/{war['id']}", headers=h1)).json()
    assert detail["war"]["status"] == "resolved" and detail["snapshot"] is not None
    res = detail["war"]["result"]
    assert len(res["lanes"]) == 10 and res["attacker_points"] + res["defender_points"] == 10
    assert len(detail["snapshot"]["defenders"]) == 10 and all(d.get("npc") for d in detail["snapshot"]["defenders"])
    assert res["attacker_won"] is True and res["captured"] is True  # players beat 70%-median garrison
    # snapshot immutable & single: re-tick must not change anything or double-credit
    await client.post("/_test/tick", headers=h1)
    snaps = await db.war_snapshots.count_documents({"war_id": war["id"]})
    assert snaps == 1
    coins = (await client.get("/profile", headers=h1)).json()["resources"]["war_coins"]
    assert coins == 100 + 150
    node = await db.alliance_map_nodes.find_one({"shard_id": war["shard_id"], "node_id": target["node_id"]})
    assert node["owner_alliance_id"] == a1["id"]
    # deterministic lane replay
    from app.domain.wars import resolve_lanes
    snap = await db.war_snapshots.find_one({"war_id": war["id"]})
    assert resolve_lanes(snap)["lanes"] == res["lanes"]
    # season leaderboard updated
    mp2 = (await client.get("/wars/map", headers=h2)).json()
    assert any(l["alliance_id"] == a1["id"] and l["season_points"] == 100 for l in mp2["leaderboard"])
    # v1.2: live war alerts in the alliance chat (declare, roster, lock, result) + lane counter fields for the animated replay
    chat = (await client.get(f"/chat/messages?channel=alliance:{a1['id']}", headers=h1)).json()["messages"]
    alerts = [m for m in chat if m.get("system") and m.get("kind") == "war"]
    texts = " | ".join(m["text"] for m in alerts)
    assert "ha dichiarato guerra" in texts and "ha salvato il roster" in texts and "Roster bloccato" in texts and "VITTORIA" in texts
    assert all({"attacker_counter_pct", "defender_counter_pct", "attacker_npc", "defender_npc", "attacker_level"} <= set(l) for l in res["lanes"])
    assert all(l["defender_counter_pct"] == 0 and l["attacker_counter_pct"] == 0 for l in res["lanes"])  # NPC garrison is neutral
    assert "army_class_mix" in detail["snapshot"]["attackers"][0] and "army_per_unit" in detail["snapshot"]["attackers"][0]


async def test_titan_hunt(client):
    a, members = await _alliance_with_members(client, 3, "Hunters")
    h = members[0]["headers"]
    assert (await client.post("/alliance-boss/start", json={"tier": 1}, headers=members[1]["headers"])).status_code == 403
    run = (await client.post("/alliance-boss/start", json={"tier": 1}, headers=h)).json()
    assert run["hp"] == 500000
    before = (await client.get("/profile", headers=h)).json()["resources"]
    r = (await client.post("/alliance-boss/attack", headers=h)).json()
    prof = (await client.get("/profile", headers=h)).json()
    assert prof["resources"]["forge_dust"] == before["forge_dust"] + 25 and prof["resources"]["war_coins"] == before["war_coins"] + 20
    assert r["damage"] == prof["combat"]["total_power"] * 4
    await client.post("/alliance-boss/attack", headers=h)
    await client.post("/alliance-boss/attack", headers=h)
    fourth = (await client.post("/alliance-boss/attack", headers=h)).json()
    assert fourth["paid"] is True  # 3 free used -> paid extra attack (50 Rubies of the initial 100)
    assert (await client.get("/profile", headers=h)).json()["resources"]["rubies"] == 100 - 50
    await db.players.update_one({"_id": members[0]["player_id"]}, {"$set": {"resources.rubies": 0}})
    broke = await client.post("/alliance-boss/attack", headers=h)
    assert broke.status_code == 409  # paid attack without Rubies
    # kill with massive power
    await db.players.update_one({"_id": members[1]["player_id"]}, {"$set": {"hero.level": 100, "army.units.dragon": 5000, "army.formation.dragon": 5000, "kingdom.castle_level": 20}})
    kill = (await client.post("/alliance-boss/attack", headers=members[1]["headers"])).json()
    assert kill["killed"] is True
    p1 = (await client.get("/profile", headers=h)).json()["resources"]
    assert p1["forge_dust"] == before["forge_dust"] + 25 * 4 + 150 and p1["reforge_stone"] == before["reforge_stone"] + 2


async def test_store_webhook_idempotent_and_refund(client):
    u = await register(client)
    h = u["headers"]
    pid = u["player_id"]
    cat = (await client.get("/store/catalog", headers=h)).json()
    assert cat["paid_random_gear_or_gacha"] is False and len(cat["store_products"]) == 8
    ev = {"event": {"id": f"evt_{pid}", "type": "INITIAL_PURCHASE", "app_user_id": pid, "product_id": "idle1.rubies.700", "store": "APP_STORE", "transaction_id": f"tx_{pid}"}}
    bad = await client.post("/purchases/revenuecat/webhook", content=json.dumps(ev), headers={"Authorization": "Bearer nope", "Content-Type": "application/json"})
    assert bad.status_code == 401
    ok_h = {"Authorization": f"Bearer {settings.RC_WEBHOOK_TOKEN}", "Content-Type": "application/json"}
    r1 = await client.post("/purchases/revenuecat/webhook", content=json.dumps(ev), headers=ok_h)
    r2 = await client.post("/purchases/revenuecat/webhook", content=json.dumps(ev), headers=ok_h)
    assert r1.status_code == 200 and r2.json().get("duplicate") is True
    # same transaction under a new event id must not double credit
    ev2 = {"event": {**ev["event"], "id": f"evt2_{pid}", "type": "RENEWAL"}}
    await client.post("/purchases/revenuecat/webhook", content=json.dumps(ev2), headers=ok_h)
    prof = (await client.get("/profile", headers=h)).json()
    assert prof["resources"]["rubies"] == 100 + 700
    pass_ev = {"event": {"id": f"evp_{pid}", "type": "NON_RENEWING_PURCHASE", "app_user_id": pid, "product_id": "idle1.event_pass.weekly", "store": "PLAY_STORE", "transaction_id": f"txp_{pid}"}}
    await client.post("/purchases/revenuecat/webhook", content=json.dumps(pass_ev), headers=ok_h)
    ents = (await client.get("/store/catalog", headers=h)).json()["entitlements"]
    assert ents["event_pass"]["active"] is True
    refund = {"event": {"id": f"evr_{pid}", "type": "CANCELLATION", "cancel_reason": "CUSTOMER_SUPPORT", "app_user_id": pid, "product_id": "idle1.rubies.700", "store": "APP_STORE", "transaction_id": f"tx_{pid}"}}
    await client.post("/purchases/revenuecat/webhook", content=json.dumps(refund), headers=ok_h)
    prof = (await client.get("/profile", headers=h)).json()
    assert prof["resources"]["rubies"] == 100
    hist = (await client.get("/account/purchases", headers=h)).json()
    assert any(p["status"] == "refunded" for p in hist["purchases"])
    # client can never self-credit: verify without RC secret is a hard 503, no state change
    v = await client.post("/purchases/verify", json={"product_id": "idle1.rubies.700"}, headers=h)
    assert v.status_code == 503
    await grant(client, h, resources={"rubies": 100})  # 200 Rubies: the canonical small crate costs 150
    crate = await client.post("/store/crate", json={"key": "small"}, headers=h)
    assert crate.status_code == 200 and crate.json()["rubies_spent"] == 150
    assert (await client.get("/profile", headers=h)).json()["resources"]["rubies"] == 200 - 150
