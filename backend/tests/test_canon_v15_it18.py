"""Iteration 18 — Canon v1.5 live E2E tests: unlocks, rarity bands, domain tiles, quest texts,
alternatives, war casualties (main), PvE unchanged, PDF."""
import io
import json
import time
import pytest
import requests

from live_env import API as BASE, restore_enemy_border, spec, token
from qa_fixtures import ORS_ALLIANCE, ORS_LEADER as ORS_LEADER_SPEC, QA_BOTS, QA_LORD

QA = (QA_LORD["email"], QA_LORD["password"])
ORS_LEADER = (ORS_LEADER_SPEC["email"], ORS_LEADER_SPEC["password"])
BOT4 = (QA_BOTS[3]["email"], QA_BOTS[3]["password"])


def _login(email, pw):
    return {"Authorization": f"Bearer {token(email, pw)}"}


@pytest.fixture(scope="module")
def qa_h():
    return _login(*QA)


@pytest.fixture(scope="module")
def ors_h():
    return _login(*ORS_LEADER)


@pytest.fixture(scope="module")
def bot4_h():
    return _login(*BOT4)


# -------- (1) Canon validation --------
def test_canon_validation_v15():
    r = requests.get(f"{BASE}/canon/validation", timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["VERSION"] >= "1.5"


# -------- (2) /api/army effective unlock --------
def test_army_effective_unlock_fields(qa_h):
    r = requests.get(f"{BASE}/army", headers=qa_h, timeout=15)
    assert r.status_code == 200
    units = {u["key"]: u for u in r.json()["units"]}
    # infantry always unlocked at 1
    assert units["infantry"]["unlock_castle_level"] == 1
    assert units["infantry"]["effective_unlock_castle_level"] == 1
    # nominal->effective bumps
    expected = {"archer": (3, 4), "cavalry": (5, 7), "conquest_wagon": (9, 10), "war_elephant": (12, 13)}
    for key, (nom, eff) in expected.items():
        u = units[key]
        assert u["unlock_castle_level"] == nom, (key, u)
        assert u["effective_unlock_castle_level"] == eff, (key, u)
        # required_research_name must be present because eff > nom
        assert u.get("required_research_name"), (key, u)


def test_recruit_locked_unit_returns_403(qa_h):
    # QA lord is castle 8, dragon requires much higher castle => should be locked
    r = requests.post(f"{BASE}/army/recruit", json={"unit": "dragon", "quantity": 1}, headers=qa_h, timeout=15)
    assert r.status_code == 403, r.text
    body = r.json()
    assert "unit_locked" in json.dumps(body).lower()


# -------- (3) Rarity drop bands (read canon directly since /canon/static does not expose stage_drop_weights) --------
def test_gear_stage_drop_weights_bands():
    from app.core.canon import canon
    gear = canon()["gear"]
    bands = gear["stage_drop_weights"]
    assert len(bands) == 7, len(bands)
    unlock = gear["rarity_unlock_stage"]
    for band in bands:
        weights = band["weights_pct"]
        total = sum(weights.values())
        assert total == 100, (band, total)
        start = int(band["stages"].split("-")[0])
        for rarity, w in weights.items():
            if w > 0:
                us = unlock.get(rarity, 1)
                assert us <= start, f"band {band['stages']} has rarity {rarity} (unlock {us}) with weight {w}"
    # explicit: band 1-24 (i.e. first two bands) should NOT have rare > 0
    for band in bands:
        s = band["stages"]
        if s in ("1-9", "10-24"):
            assert band["weights_pct"].get("rare", 0) == 0, (s, band)


# -------- (4) Domain tiles at various stages --------
def test_domain_tiles_formula(bot4_h):
    prof0 = requests.get(f"{BASE}/profile", headers=bot4_h, timeout=15).json()
    # Try to record starting highest_cleared for restore
    prev_hc = prof0.get("campaign", {}).get("highest_cleared", 10)
    try:
        cases = [(3, 1), (4, 2), (199, 99), (200, 100)]
        for hc, expected in cases:
            g = requests.post(f"{BASE}/_test/grant", json={"highest_cleared": hc}, headers=bot4_h, timeout=15)
            assert g.status_code == 200, g.text
            prof = requests.get(f"{BASE}/profile", headers=bot4_h, timeout=15).json()
            owned = prof["domain"]["owned"]
            assert owned == expected, f"stage {hc} expected {expected} got {owned}"
    finally:
        # restore to 10 as requested
        requests.post(f"{BASE}/_test/grant", json={"highest_cleared": max(10, prev_hc)}, headers=bot4_h, timeout=15)


# -------- (5) Quest templates have Italian text --------
def test_quests_italian_text_and_alt_active(qa_h):
    r = requests.get(f"{BASE}/quests", headers=qa_h, timeout=15)
    assert r.status_code == 200
    j = r.json()
    for period in ("daily", "weekly"):
        block = j[period]
        assert "templates" in block, block
        assert len(block["templates"]) > 0
        for t in block["templates"]:
            assert t.get("text"), (period, t)
            assert isinstance(t["alt_active"], bool)
        # tasks[key].text present + alt_active false for QA (forge not maxed)
        for key, task in block["tasks"].items():
            assert task.get("text"), (period, key, task)
            assert task["alt_active"] is False, (period, key, task["alt_active"])


# -------- (6) Quest alternative when forge maxed --------
def test_quest_alternative_when_forge_maxed(qa_h):
    """With every slot at the forge cap, the forge quest must offer its alternative."""
    forge = spec()["gear"]["forge"]
    slots = spec()["gear"]["slots"]
    before = requests.get(f"{BASE}/gear/inventory", headers=qa_h, timeout=15).json()["forge"]
    r = requests.post(f"{BASE}/_test/grant",
                      json={"forge": {s: forge["max_level_per_slot"] for s in slots}}, headers=qa_h, timeout=15)
    assert r.status_code == 200, r.text[:200]
    try:
        templates = {t["key"]: t for t in requests.get(f"{BASE}/quests", headers=qa_h, timeout=15).json()["daily"]["templates"]}
        assert templates["forge_upgrade"]["alt_active"] is True, templates["forge_upgrade"]
    finally:
        requests.post(f"{BASE}/_test/grant", json={"forge": before}, headers=qa_h, timeout=15)


# -------- (7) War casualties full flow (MAIN) --------
@pytest.fixture(scope="module")
def war_result(qa_h, ors_h):
    # Move any resolved/cancelled war outside the 24h cooldown
    requests.post(f"{BASE}/_test/war-shift", json={"seconds": 100000, "include_resolved": True}, headers=qa_h, timeout=15)
    requests.post(f"{BASE}/_test/tick", headers=qa_h, timeout=60)

    # The target must belong to [ORS] specifically: other alliances share the shard and
    # a neutral or third-party node would be defended by the NPC garrison, leaving no
    # contested lane and therefore no PvP casualties to assert on.
    target = restore_enemy_border({"headers": qa_h}, {"headers": ors_h})
    if target is None:
        pytest.skip(f"[QAT] and [{ORS_ALLIANCE['tag']}] share no border; run backend/scripts/seed_qa.py")
    r = requests.post(f"{BASE}/wars/declare", json={"node_id": target}, headers=qa_h, timeout=15)
    assert r.status_code in (200, 201), f"declare on {target}: {r.status_code} {r.text[:200]}"
    body = r.json()
    war_id = body.get("id") or body.get("war", {}).get("id")
    assert war_id, "could not declare"
    m = requests.get(f"{BASE}/wars/map", headers=qa_h, timeout=15).json()

    # Record BEFORE
    army_before = requests.get(f"{BASE}/army", headers=qa_h, timeout=15).json()
    units_before = {u["key"]: u["owned"] for u in army_before["units"]}
    prof_before = requests.get(f"{BASE}/profile", headers=qa_h, timeout=15).json()
    form_before = dict(prof_before["army"]["formation"])

    mine = requests.get(f"{BASE}/alliances/mine", headers=qa_h, timeout=15).json()["alliance"]
    my_alliance_id = m["my_alliance_id"]
    pids_att = [x["player_id"] for x in mine["members"]][:10]
    r = requests.post(f"{BASE}/wars/roster", json={"war_id": war_id, "player_ids": pids_att}, headers=qa_h, timeout=15)
    assert r.status_code in (200, 201), r.text

    # ORS as defender: set their roster too
    d0 = requests.get(f"{BASE}/wars/{war_id}", headers=ors_h, timeout=15).json()
    if d0.get("my_side") == "defense":
        mo = requests.get(f"{BASE}/alliances/mine", headers=ors_h, timeout=15).json()["alliance"]
        pids_def = [x["player_id"] for x in mo["members"]][:10]
        requests.post(f"{BASE}/wars/roster", json={"war_id": war_id, "player_ids": pids_def}, headers=ors_h, timeout=15)

    # advance to lock, then to resolve
    requests.post(f"{BASE}/_test/war-shift", json={"seconds": 8 * 3600}, headers=qa_h, timeout=15)
    requests.post(f"{BASE}/_test/tick", headers=qa_h, timeout=60)
    requests.post(f"{BASE}/_test/war-shift", json={"seconds": 1800}, headers=qa_h, timeout=15)
    requests.post(f"{BASE}/_test/tick", headers=qa_h, timeout=60)

    d = requests.get(f"{BASE}/wars/{war_id}", headers=qa_h, timeout=15).json()
    assert d["war"]["status"] == "resolved", d["war"]["status"]
    snap_before = json.dumps(d["snapshot"], sort_keys=True, default=str)

    # AFTER
    army_after = requests.get(f"{BASE}/army", headers=qa_h, timeout=15).json()
    units_after = {u["key"]: u["owned"] for u in army_after["units"]}
    prof_after = requests.get(f"{BASE}/profile", headers=qa_h, timeout=15).json()

    # idempotent second tick
    requests.post(f"{BASE}/_test/tick", headers=qa_h, timeout=60)
    army_after2 = requests.get(f"{BASE}/army", headers=qa_h, timeout=15).json()
    units_after2 = {u["key"]: u["owned"] for u in army_after2["units"]}
    d2 = requests.get(f"{BASE}/wars/{war_id}", headers=qa_h, timeout=15).json()
    snap_after = json.dumps(d2["snapshot"], sort_keys=True, default=str)

    return {
        "war_id": war_id,
        "war": d["war"],
        "detail": d,
        "units_before": units_before,
        "units_after": units_after,
        "units_after2": units_after2,
        "form_before": form_before,
        "prof_after": prof_after,
        "snap_before": snap_before,
        "snap_after": snap_after,
        "my_alliance_id": my_alliance_id,
    }


def test_war_casualties_shape(war_result):
    war = war_result["war"]
    cas = war["result"]["casualties"]
    assert isinstance(cas, dict) and len(cas) > 0
    for pid, c in cas.items():
        for k in ("side", "lane", "won", "ratio", "rate_pct", "units", "deployed_total", "lost_total"):
            assert k in c, (pid, k, c)
        assert c["lost_total"] <= c["deployed_total"], (pid, c)
        for unit_key, u in c["units"].items():
            for k in ("deployed", "lost", "survived", "rate_pct"):
                assert k in u, (pid, unit_key, u)
            assert u["lost"] <= u["deployed"]
            if u["deployed"] > 0:
                assert u["survived"] >= 1, (pid, unit_key, u)


def test_war_lane_rates_loser_gt_winner(war_result):
    cas = war_result["war"]["result"]["casualties"]
    # group by lane
    by_lane = {}
    for pid, c in cas.items():
        by_lane.setdefault(c["lane"], []).append(c)
    checked = 0
    for lane, entries in by_lane.items():
        winners = [e for e in entries if e["won"]]
        losers = [e for e in entries if not e["won"]]
        if winners and losers:
            # loser rate_pct > winner rate_pct
            assert max(l["rate_pct"] for l in losers) > min(w["rate_pct"] for w in winners), (lane, winners, losers)
            checked += 1
    assert checked > 0, "no contested lanes found (all NPC/empty?)"


def test_war_units_deducted_and_formation_clamped(war_result):
    d = war_result["detail"]
    my = d.get("my_casualties")
    assert my is not None
    ub, ua = war_result["units_before"], war_result["units_after"]
    for k, v in my["units"].items():
        assert ua[k] == ub[k] - v["lost"], (k, ub[k], ua[k], v)
    form = war_result["prof_after"]["army"]["formation"]
    for k, q in form.items():
        assert q <= ua.get(k, 0), (k, q, ua.get(k))


def test_war_idempotent_and_snapshot_unchanged(war_result):
    assert war_result["units_after"] == war_result["units_after2"], "losses applied twice on second tick!"
    assert war_result["snap_before"] == war_result["snap_after"], "snapshot changed after second tick!"


def test_war_detail_extras(war_result):
    d = war_result["detail"]
    assert "my_casualties" in d and "team_casualties" in d and "roster_players" in d
    tc = d["team_casualties"]
    if tc:
        for k in ("deployed", "lost", "players"):
            assert k in tc, tc


def test_war_result_chat_alert(qa_h, war_result):
    chan = f"alliance:{war_result['my_alliance_id']}"
    chat = requests.get(f"{BASE}/chat/messages", params={"channel": chan}, headers=qa_h, timeout=15).json()
    msgs = chat.get("messages", chat) if isinstance(chat, dict) else chat
    perdite = [x for x in msgs if "Perdite" in x.get("text", "")]
    assert len(perdite) >= 1, "no ⚰ Perdite alert in alliance chat"
    assert "⚰" in perdite[-1]["text"] or "Perdite" in perdite[-1]["text"]


# -------- (8) PvE unchanged: campaign attempt/claim should not deduct units --------
def test_pve_units_unchanged(qa_h):
    # The time-shift below also completes any pending recruitment, so the rule under
    # test is that PvE never *reduces* a unit count, not that counts stay identical.
    army0 = requests.get(f"{BASE}/army", headers=qa_h, timeout=15).json()
    u0 = {u["key"]: u["owned"] for u in army0["units"]}
    prof = requests.get(f"{BASE}/profile", headers=qa_h, timeout=15).json()
    stage = prof["campaign"].get("current_stage") or 1
    # attempt
    a = requests.post(f"{BASE}/battle/attempt", json={"stage": stage}, headers=qa_h, timeout=15)
    if a.status_code not in (200, 201):
        pytest.skip(f"battle/attempt not accepted: {a.status_code} {a.text[:150]}")
    aj = a.json()
    attempt_id = aj.get("attempt_id") or aj.get("id") or (aj.get("attempt") or {}).get("id")
    if not attempt_id:
        pytest.skip(f"no attempt_id in response: {aj}")
    # fast-forward via time-shift
    requests.post(f"{BASE}/_test/time-shift", json={"seconds": 3600}, headers=qa_h, timeout=15)
    c = requests.post(f"{BASE}/battle/claim", json={"attempt_id": attempt_id}, headers=qa_h, timeout=15)
    assert c.status_code in (200, 201), c.text
    army1 = requests.get(f"{BASE}/army", headers=qa_h, timeout=15).json()
    u1 = {u["key"]: u["owned"] for u in army1["units"]}
    lost = {k: (u0[k], u1[k]) for k in u0 if u1.get(k, 0) < u0[k]}
    assert not lost, ("PvE deducted units", lost)


# -------- (9) Rulebook PDF --------
def test_rulebook_pdf():
    r = requests.get(f"{BASE}/docs/regolamento.pdf", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    try:
        from pypdf import PdfReader
    except Exception:
        pytest.skip("pypdf not available")
    reader = PdfReader(io.BytesIO(r.content))
    if reader.is_encrypted:
        reader.decrypt("")
    assert len(reader.pages) == 43, f"expected 43 pages got {len(reader.pages)}"
    text = ""
    for p in reader.pages:
        try:
            text += p.extract_text() or ""
        except Exception:
            pass
    # The rulebook is generated from the canonical spec, so it must carry the
    # version currently pinned in canon rather than the one live when this was written.
    for needle in (f"spec v{spec()['document']['version']}", "Perdite permanenti", "Disponibile dal", "floor("):
        assert needle in text, f"missing '{needle}'"
