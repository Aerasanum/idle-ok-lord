"""Alliance war and item-icon regression tests against the preview backend.

Covers the review request scope:
- GET /wars/map (nodes=361, ORS+QAT alliances, leaderboard, my_home)
- GET /wars, POST /wars/declare validation (non-adjacent 400, own node 400)
- POST /wars/roster validation (>10 ids 400, non-officer 403)
- Snapshot after resolution (10 attackers/10 defenders NPC Garrison, 10 lanes)
- Reward idempotency across a second tick (war_coins granted once)
"""
import os
import time

import pytest
import requests

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://idle1-v11-build.preview.emergentagent.com").rstrip("/") + "/api"

QA_EMAIL = "qa.lord@example.com"
QA_PASS = "QaLordPass!2026"
ORS_EMAIL = "orsi.leader@idle1.app"
ORS_PASS = "QaBot!2026"
BOT_EMAILS = [f"qa.bot{i}@idle1.app" for i in range(1, 10)]
BOT_PASS = "QaBot!2026"


def _login(email: str, pw: str) -> dict:
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    d = r.json()
    d["headers"] = {"Authorization": f"Bearer {d['access_token']}"}
    return d


@pytest.fixture(scope="module")
def qa():
    return _login(QA_EMAIL, QA_PASS)


@pytest.fixture(scope="module")
def ors():
    return _login(ORS_EMAIL, ORS_PASS)


@pytest.fixture(scope="module")
def bot1():
    return _login(BOT_EMAILS[0], BOT_PASS)


# ------------------------ WAR MAP ------------------------

class TestWarMap:
    def test_wars_map_shape(self, qa):
        r = requests.get(f"{BASE}/wars/map", headers=qa["headers"], timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert len(j["nodes"]) == 361
        # Both QAT (leader = qa.lord) and ORS should have alliances entries with home nodes
        als = j["alliances"]
        tags = {v["tag"] for v in als.values()}
        assert "QAT" in tags, f"QAT not on map. tags={tags}"
        assert "ORS" in tags, f"ORS not on map. tags={tags}"
        assert j["my_alliance_id"], "expected my_alliance_id for qa.lord"
        assert j["my_home"] is not None, "expected my_home node for QAT"
        lb = j["leaderboard"]
        assert isinstance(lb, list) and len(lb) >= 2
        ors_row = next((r for r in lb if r["tag"] == "ORS"), None)
        assert ors_row is not None
        assert ors_row["season_points"] >= 100, f"ORS should have >=100 season points, got {ors_row['season_points']}"

    def test_home_node_20_for_qat(self, qa):
        j = requests.get(f"{BASE}/wars/map", headers=qa["headers"], timeout=15).json()
        assert j["my_home"] == 20, f"QAT home expected 20, got {j['my_home']}"

    def test_leaderboard_has_scores(self, qa):
        j = requests.get(f"{BASE}/wars/map", headers=qa["headers"], timeout=15).json()
        assert all("season_points" in row for row in j["leaderboard"])


# ------------------------ WARS LIST ------------------------

class TestWarsList:
    def test_list_wars_ok(self, qa):
        r = requests.get(f"{BASE}/wars", headers=qa["headers"], timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "wars" in j
        assert j.get("alliance_id"), "expected QAT alliance id"


# ------------------------ DECLARE VALIDATION ------------------------

class TestDeclareValidation:
    def test_declare_own_node_400(self, qa):
        # node 20 is QAT home; 409 when QAT is in cooldown/active war (checked before node validation)
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": 20}, headers=qa["headers"], timeout=15)
        assert r.status_code in (400, 409), f"expected 400/409, got {r.status_code} {r.text[:200]}"
        if r.status_code == 400:
            assert "own_node" in r.text or "own" in r.text.lower()

    def test_declare_non_adjacent_400(self, qa):
        # node 360 (bottom-right corner) is very far from home node 20 → not adjacent
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": 360}, headers=qa["headers"], timeout=15)
        # 400 not_adjacent OR 409 if QAT is already in a war/cooldown/contested
        assert r.status_code in (400, 409), f"expected 400/409, got {r.status_code} {r.text[:200]}"
        if r.status_code == 400:
            assert "not_adjacent" in r.text.lower() or "adjacent" in r.text.lower()

    def test_declare_invalid_node_id_422(self, qa):
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": 999}, headers=qa["headers"], timeout=15)
        assert r.status_code == 422, r.text  # pydantic ge=0, le=360


# ------------------------ ROSTER VALIDATION ------------------------

class TestRosterValidation:
    def test_roster_too_many_ids_400(self, qa):
        # find any war involving QAT if present, otherwise skip
        wars = requests.get(f"{BASE}/wars", headers=qa["headers"], timeout=15).json()["wars"]
        war = next((w for w in wars if w.get("status") == "prep"), None)
        if not war:
            pytest.skip("no prep war to test roster on")
        r = requests.post(f"{BASE}/wars/roster", json={"war_id": war["id"], "player_ids": [f"p{i}" for i in range(11)]}, headers=qa["headers"], timeout=15)
        assert r.status_code == 400, f"expected 400 roster_size, got {r.status_code} {r.text[:200]}"
        assert "roster_size" in r.text.lower() or "max" in r.text.lower()

    def test_roster_non_officer_403(self, bot1):
        # bot1 is a member but NOT officer/leader of QAT → should get 403 officer_required
        wars = requests.get(f"{BASE}/wars", headers=bot1["headers"], timeout=15).json()["wars"]
        war = next((w for w in wars if w.get("status") == "prep"), None)
        if not war:
            pytest.skip("no prep war to test non-officer on")
        r = requests.post(f"{BASE}/wars/roster", json={"war_id": war["id"], "player_ids": []}, headers=bot1["headers"], timeout=15)
        assert r.status_code == 403, f"expected 403 officer_required, got {r.status_code} {r.text[:200]}"


# ------------------------ FULL WAR E2E ------------------------

class TestWarE2E:
    """End-to-end: declare (if possible) → set roster → war-shift → tick → verify snapshot & rewards idempotent."""

    def test_full_flow(self, qa, bot1):
        wars = requests.get(f"{BASE}/wars", headers=qa["headers"], timeout=15).json()["wars"]
        active = next((w for w in wars if w.get("status") in ("prep", "locked")), None)
        war_id = None
        if active:
            war_id = active["id"]
        else:
            # attempt to declare on node 21 (adjacent to home 20)
            r = requests.post(f"{BASE}/wars/declare", json={"node_id": 21}, headers=qa["headers"], timeout=15)
            if r.status_code == 200:
                war_id = r.json()["id"]
            elif r.status_code == 409 or (r.status_code == 400 and "own_node" in r.text):
                # cooldown / node_contested / attack_cooldown / node already conquered in a previous run → live state, not a bug
                pytest.skip(f"declare 21 blocked: {r.text[:200]}")
            else:
                pytest.fail(f"declare failed: {r.status_code} {r.text[:200]}")
        assert war_id, "no war id"

        # get bot player_ids from alliance mine
        mine = requests.get(f"{BASE}/alliances/mine", headers=qa["headers"], timeout=15).json()["alliance"]
        members = mine.get("members", [])
        assert len(members) >= 10, f"expected >=10 QAT members, got {len(members)}"
        pids = [m.get("player_id") or m.get("id") for m in members[:10]]
        pids = [p for p in pids if p]
        assert len(pids) == 10

        # set roster
        rr = requests.post(f"{BASE}/wars/roster", json={"war_id": war_id, "player_ids": pids}, headers=qa["headers"], timeout=15)
        assert rr.status_code == 200, f"roster failed: {rr.status_code} {rr.text[:200]}"

        # shift wars 28860s + tick
        s = requests.post(f"{BASE}/_test/war-shift", json={"seconds": 28860}, headers=qa["headers"], timeout=15)
        assert s.status_code == 200, s.text
        t = requests.post(f"{BASE}/_test/tick", headers=qa["headers"], timeout=30)
        assert t.status_code == 200, t.text

        # war detail
        d = requests.get(f"{BASE}/wars/{war_id}", headers=qa["headers"], timeout=15).json()
        w = d["war"]
        assert w["status"] == "resolved", f"expected resolved, got {w['status']}"
        assert w["result"] is not None
        assert isinstance(w["result"].get("lanes"), list)
        assert len(w["result"]["lanes"]) == 10, f"expected 10 lanes, got {len(w['result']['lanes'])}"

        # snapshot has 10 attackers + 10 defenders (NPC Garrison since neutral node had no defender)
        snap = d["snapshot"]
        assert snap and len(snap["attackers"]) == 10 and len(snap["defenders"]) == 10
        # defenders are NPC Garrison for neutral node
        if not w.get("defender_id"):
            assert all(s.get("npc") for s in snap["defenders"])
            assert all(s.get("display_name") == "Garrison" for s in snap["defenders"])

        # capture attacker war_coins now, do a second tick and confirm idempotency
        prof1 = requests.get(f"{BASE}/profile", headers=qa["headers"], timeout=15).json()
        coins1 = prof1["resources"].get("war_coins", 0)
        t2 = requests.post(f"{BASE}/_test/tick", headers=qa["headers"], timeout=30)
        assert t2.status_code == 200
        prof2 = requests.get(f"{BASE}/profile", headers=qa["headers"], timeout=15).json()
        coins2 = prof2["resources"].get("war_coins", 0)
        assert coins2 == coins1, f"war_coins doubled on second tick: {coins1} -> {coins2}"


# ------------------------ TITAN HUNT (boss) ------------------------

class TestBoss:
    def test_boss_view_ok(self, qa):
        r = requests.get(f"{BASE}/alliance-boss", headers=qa["headers"], timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("alliance_id")
        assert "rules" in j
        assert j["rules"]["free_attacks_per_day"] == 3

    def test_boss_start_and_attack(self, qa):
        cur = requests.get(f"{BASE}/alliance-boss", headers=qa["headers"], timeout=15).json()
        if cur.get("run") and cur["run"].get("status") == "active":
            pass  # reuse
        else:
            s = requests.post(f"{BASE}/alliance-boss/start", json={"tier": 1}, headers=qa["headers"], timeout=15)
            assert s.status_code == 200, s.text
        a = requests.post(f"{BASE}/alliance-boss/attack", headers=qa["headers"], timeout=15)
        # 200 with damage OR 409 if user already used up daily attacks
        assert a.status_code in (200, 409), a.text
        if a.status_code == 200:
            j = a.json()
            assert j["damage"] > 0
            assert j["boss_hp"] < j["boss_hp_max"]
