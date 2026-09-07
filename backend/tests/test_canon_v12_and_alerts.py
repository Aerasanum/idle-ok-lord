"""Canon v1.2 counters + battle stage formulas + Titan Hunt showcase + war-alerts E2E.

Scoped to iteration_7 review request. All tests hit the live preview backend.
"""
import math
import os
import time

import pytest
import requests

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://idle1-v11-build.preview.emergentagent.com").rstrip("/") + "/api"

QA_EMAIL = "qa.lord@example.com"
QA_PASS = "QaLordPass!2026"
ORS_EMAIL = "orsi.leader@idle1.app"
ORS_PASS = "QaBot!2026"


def _login(email: str, pw: str) -> dict:
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    d = r.json()
    d["headers"] = {"Authorization": f"Bearer {d['access_token']}"}
    return d


@pytest.fixture(scope="module")
def qa():
    return _login(QA_EMAIL, QA_PASS)


@pytest.fixture(scope="module")
def ors():
    return _login(ORS_EMAIL, ORS_PASS)


# ----------------------------------------------------------------------
# Canon v1.2 — GET /army counters + region_counter + Ariete d'Assedio
# ----------------------------------------------------------------------
class TestArmyCounters:
    def test_army_counters_shape(self, qa):
        r = requests.get(f"{BASE}/army", headers=qa["headers"], timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        # counters.table with 13 units
        counters = j.get("counters")
        assert counters is not None, "missing counters block"
        table = counters.get("table")
        # table may be dict {unit_key: {strong_vs, weak_vs}} or list
        if isinstance(table, dict):
            assert len(table) == 13, f"expected 13 units in counters.table, got {len(table)}"
            for key, row in table.items():
                assert "strong_vs" in row and isinstance(row["strong_vs"], list)
                assert "weak_vs" in row and isinstance(row["weak_vs"], list)
        else:
            assert isinstance(table, list) and len(table) == 13, f"expected 13 units, got {len(table) if table else None}"
            for row in table:
                assert "key" in row
                assert "strong_vs" in row and isinstance(row["strong_vs"], list)
                assert "weak_vs" in row and isinstance(row["weak_vs"], list)
        assert counters.get("bonus_pct") == 30, counters.get("bonus_pct")
        assert counters.get("malus_pct") == 20, counters.get("malus_pct")

    def test_region_counter_present(self, qa):
        j = requests.get(f"{BASE}/army", headers=qa["headers"], timeout=15).json()
        rc = j.get("region_counter")
        assert rc is not None, "missing region_counter"
        upct = rc.get("unit_pct")
        assert isinstance(upct, dict) and len(upct) >= 1, f"unit_pct missing/empty: {upct}"
        # values are numeric percentages (int or float)
        for k, v in upct.items():
            assert isinstance(v, (int, float)), f"unit_pct[{k}] not numeric: {v}"

    def test_conquest_wagon_renamed(self, qa):
        j = requests.get(f"{BASE}/army", headers=qa["headers"], timeout=15).json()
        units = j.get("units") or []
        wagon = next((u for u in units if u.get("key") == "conquest_wagon"), None)
        assert wagon is not None, "conquest_wagon unit missing"
        assert wagon.get("name") == "Ariete d'Assedio", f"expected 'Ariete d\\'Assedio', got {wagon.get('name')}"


# ----------------------------------------------------------------------
# Battle stage formulas: stage 60 (boss) + stage 100 (boss)
# ----------------------------------------------------------------------
class TestBattleFormulas:
    def _fetch(self, qa, stage):
        r = requests.get(f"{BASE}/battle/stage/{stage}", headers=qa["headers"], timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    def test_stage_60_shape(self, qa):
        j = self._fetch(qa, 60)
        assert "enemy_mix" in j and isinstance(j["enemy_mix"], (list, dict))
        assert "army_counter_net_pct" in j
        assert isinstance(j["army_counter_net_pct"], (int, float))
        # stage 60 is a boss stage
        kind = j.get("kind") or (j.get("stage") or {}).get("kind")
        assert kind == "boss", f"stage 60 kind expected boss, got {kind}"

    def test_stage_60_required_power(self, qa):
        j = self._fetch(qa, 60)
        rp = j.get("required_power")
        assert isinstance(rp, (int, float))
        # 75 * 1.047^59 * (1 + 0.004*10) * 1.85 (boss)
        expected = round(round(75 * (1.047 ** 59) * (1 + 0.004 * 10)) * 1.85)
        # allow small variance
        assert abs(rp - expected) <= max(2, expected * 0.005), f"stage60 rp={rp} expected≈{expected}"

    def test_stage_100_required_power(self, qa):
        j = self._fetch(qa, 100)
        rp = j.get("required_power")
        assert isinstance(rp, (int, float))
        # stage 100: 75*1.047^99*1.2 (elite? no — boss on stage%10==0) → boss 1.85
        expected = round(round(75 * (1.047 ** 99) * 1.2) * 1.85)
        assert abs(rp - expected) <= max(2, expected * 0.005), f"stage100 rp={rp} expected≈{expected}"


# ----------------------------------------------------------------------
# GET /alliance-boss (Titan Hunt showcase) — titan_family, tier_families 1..10, leaderboard
# ----------------------------------------------------------------------
class TestTitanShowcase:
    def test_boss_titan_metadata(self, qa):
        r = requests.get(f"{BASE}/alliance-boss", headers=qa["headers"], timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert isinstance(j.get("titan_family"), str) and j["titan_family"], "titan_family missing"
        tf = j.get("tier_families")
        assert isinstance(tf, (list, dict)), f"tier_families missing/typed: {type(tf)}"
        # tiers 1..10 present
        if isinstance(tf, dict):
            keys = {str(k) for k in tf.keys()}
            expected_keys = {str(i) for i in range(1, 11)}
            assert expected_keys.issubset(keys), f"missing tiers: {expected_keys - keys}"
        else:
            assert len(tf) >= 10, f"tier_families length={len(tf)}"
        lb = j.get("leaderboard")
        assert isinstance(lb, list)
        # If a run exists we should see rows with rank/damage
        if j.get("run") and j["run"].get("status") == "active":
            for row in lb:
                assert "rank" in row and "display_name" in row and "damage" in row
                assert "attacks" in row and "share_pct" in row
        assert "my_player_id" in j


# ----------------------------------------------------------------------
# WAR ALERTS E2E — ORS declares → chat gets system:war messages
# ----------------------------------------------------------------------
class TestWarAlertsE2E:
    def test_full_flow(self, ors):
        # 1) clear cooldowns / resolve any old wars for ORS
        s = requests.post(f"{BASE}/_test/war-shift", json={"seconds": 90000, "include_resolved": True}, headers=ors["headers"], timeout=20)
        assert s.status_code == 200, s.text
        # nudge tick to finalize any pending
        requests.post(f"{BASE}/_test/tick", headers=ors["headers"], timeout=30)

        # 2) get ORS alliance id + members
        mine = requests.get(f"{BASE}/alliances/mine", headers=ors["headers"], timeout=15).json()["alliance"]
        alliance_id = mine.get("id")
        assert alliance_id, "no ORS alliance id"
        members = mine.get("members", [])
        assert len(members) >= 10, f"expected ORS to have 10 members, got {len(members)}"
        pids = [m.get("player_id") or m.get("id") for m in members[:10]]
        pids = [p for p in pids if p]
        assert len(pids) == 10

        # 3) find a neutral node adjacent (manhattan 1) to any ORS-owned node
        mp = requests.get(f"{BASE}/wars/map", headers=ors["headers"], timeout=15).json()
        nodes = mp["nodes"]
        my_al = mp.get("my_alliance_id")
        assert my_al == alliance_id, f"my_alliance mismatch: {my_al} vs {alliance_id}"
        by_id = {n["node_id"]: n for n in nodes}
        owned = [n for n in nodes if n.get("owner") == alliance_id]
        assert owned, "ORS owns nothing?"

        def neighbors(nid):
            n = by_id[nid]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = next((m for m in nodes if m["x"] == n["x"] + dx and m["y"] == n["y"] + dy), None)
                if nb:
                    yield nb

        target = None
        for o in owned:
            for nb in neighbors(o["node_id"]):
                if not nb.get("owner") and nb.get("type") not in ("home_castle", "castle"):
                    target = nb["node_id"]
                    break
            if target is not None:
                break
        assert target is not None, "no neutral adjacent node to ORS"

        # 4) declare
        dec = requests.post(f"{BASE}/wars/declare", json={"node_id": target}, headers=ors["headers"], timeout=15)
        assert dec.status_code == 200, f"declare failed: {dec.status_code} {dec.text[:300]}"
        war = dec.json()
        war_id = war["id"]

        # 5) chat should contain a system 'war' message on channel alliance:<id>
        time.sleep(1.0)
        ch = f"alliance:{alliance_id}"
        cm = requests.get(f"{BASE}/chat/messages", params={"channel": ch}, headers=ors["headers"], timeout=15)
        assert cm.status_code == 200, cm.text
        msgs = cm.json().get("messages", [])
        assert msgs, f"chat empty on {ch}"
        # newest first or last — inspect both ends
        recent = msgs[:5] + msgs[-5:]
        declare_msg = next((m for m in recent if m.get("system") and m.get("kind") == "war" and "dichiarato" in (m.get("text") or "").lower()), None)
        assert declare_msg is not None, f"no declare war alert in chat. recent={[{'k': m.get('kind'), 't': (m.get('text') or '')[:80]} for m in recent]}"
        assert (declare_msg.get("display_name") or "").lower().startswith("araldo"), f"unexpected sender: {declare_msg.get('display_name')}"

        # 6) roster save
        rr = requests.post(f"{BASE}/wars/roster", json={"war_id": war_id, "player_ids": pids}, headers=ors["headers"], timeout=15)
        assert rr.status_code == 200, f"roster failed: {rr.status_code} {rr.text[:200]}"
        time.sleep(1.0)
        msgs2 = requests.get(f"{BASE}/chat/messages", params={"channel": ch}, headers=ors["headers"], timeout=15).json().get("messages", [])
        roster_msg = next((m for m in (msgs2[:5] + msgs2[-5:]) if m.get("system") and m.get("kind") == "war" and "roster" in (m.get("text") or "").lower()), None)
        assert roster_msg is not None, "no roster save alert in chat"
        assert "10/10" in (roster_msg.get("text") or "") or "10" in (roster_msg.get("text") or "")

        # 7) shift + tick → resolved
        s2 = requests.post(f"{BASE}/_test/war-shift", json={"seconds": 28860}, headers=ors["headers"], timeout=20)
        assert s2.status_code == 200, s2.text
        t = requests.post(f"{BASE}/_test/tick", headers=ors["headers"], timeout=30)
        assert t.status_code == 200, t.text

        # 8) inspect war
        d = requests.get(f"{BASE}/wars/{war_id}", headers=ors["headers"], timeout=15).json()
        w = d["war"]
        assert w["status"] == "resolved", f"expected resolved, got {w['status']}"
        lanes = w.get("result", {}).get("lanes")
        assert isinstance(lanes, list) and len(lanes) == 10
        lane0 = lanes[0]
        assert "attacker_counter_pct" in lane0
        assert "defender_counter_pct" in lane0
        # neutral node → defender_counter_pct should be 0
        if not w.get("defender_id"):
            assert lane0.get("defender_counter_pct") == 0
            assert lane0.get("defender_npc") is True or lane0.get("defender_npc") == 1
        # attacker_level present
        assert "attacker_level" in lane0
        # attacker_npc field present
        assert "attacker_npc" in lane0

        # 9) chat contains 'Roster bloccato' + VITTORIA/SCONFITTA
        time.sleep(1.0)
        msgs3 = requests.get(f"{BASE}/chat/messages", params={"channel": ch}, headers=ors["headers"], timeout=15).json().get("messages", [])
        recent3 = msgs3[:10] + msgs3[-10:]
        texts = [(m.get("text") or "") for m in recent3 if m.get("system") and m.get("kind") == "war"]
        has_lock = any("bloccato" in t.lower() or "lock" in t.lower() for t in texts)
        has_result = any(("vittoria" in t.lower()) or ("sconfitta" in t.lower()) for t in texts)
        assert has_lock, f"no 'Roster bloccato' alert. texts={texts}"
        assert has_result, f"no VITTORIA/SCONFITTA alert. texts={texts}"

        # 10) second tick idempotency — no new war chat entry, no reward duplication
        count_before = len([m for m in msgs3 if m.get("system") and m.get("kind") == "war"])
        prof1 = requests.get(f"{BASE}/profile", headers=ors["headers"], timeout=15).json()
        coins1 = prof1["resources"].get("war_coins", 0)
        t2 = requests.post(f"{BASE}/_test/tick", headers=ors["headers"], timeout=30)
        assert t2.status_code == 200
        msgs4 = requests.get(f"{BASE}/chat/messages", params={"channel": ch}, headers=ors["headers"], timeout=15).json().get("messages", [])
        count_after = len([m for m in msgs4 if m.get("system") and m.get("kind") == "war"])
        assert count_after == count_before, f"war chat entries duplicated: {count_before}→{count_after}"
        prof2 = requests.get(f"{BASE}/profile", headers=ors["headers"], timeout=15).json()
        coins2 = prof2["resources"].get("war_coins", 0)
        assert coins2 == coins1, f"war_coins doubled on second tick: {coins1}→{coins2}"
