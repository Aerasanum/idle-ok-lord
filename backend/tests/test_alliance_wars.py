"""Alliance war and item-icon regression tests against the preview backend.

Covers the review request scope:
- GET /wars/map (nodes=361, ORS+QAT alliances, leaderboard, my_home)
- GET /wars, POST /wars/declare validation (non-adjacent 400, own node 400)
- POST /wars/roster validation (>10 ids 400, non-officer 403)
- Snapshot after resolution (10 attackers/10 defenders NPC Garrison, 10 lanes)
- Reward idempotency across a second tick (war_coins granted once)
"""
import pytest
import requests

from live_env import API as BASE, alliance_of, border_nodes, clear_war_cooldown, session, war_map
from qa_fixtures import ORS_ALLIANCE, ORS_LEADER, QA_ALLIANCE, QA_BOTS, QA_LORD


@pytest.fixture(scope="module")
def qa():
    return session(QA_LORD)


@pytest.fixture(scope="module")
def ors():
    return session(ORS_LEADER)


@pytest.fixture(scope="module")
def bot1():
    return session(QA_BOTS[0])


@pytest.fixture(scope="module")
def home(qa):
    """The home castle the server assigned to [QAT]; it is not a fixed node id."""
    return war_map(qa["headers"])["my_home"]


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
        assert QA_ALLIANCE["tag"] in tags, f"{QA_ALLIANCE['tag']} not on map. tags={tags}"
        assert ORS_ALLIANCE["tag"] in tags, f"{ORS_ALLIANCE['tag']} not on map. tags={tags}"
        assert j["my_alliance_id"], "expected my_alliance_id for qa.lord"
        assert j["my_home"] is not None, "expected my_home node for QAT"
        lb = j["leaderboard"]
        assert isinstance(lb, list) and len(lb) >= 2
        ors_row = next((r for r in lb if r["tag"] == ORS_ALLIANCE["tag"]), None)
        assert ors_row is not None
        assert ors_row["season_points"] >= 100, f"ORS should have >=100 season points, got {ors_row['season_points']}"

    def test_home_node_is_an_owned_home_castle(self, qa, home):
        """Home castles are handed out from a lattice in join order, so the id is not fixed."""
        j = war_map(qa["headers"])
        node = next(n for n in j["nodes"] if n["node_id"] == home)
        assert node["type"] == "home_castle", node
        assert node["owner"] == j["my_alliance_id"], node

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
    def test_declare_own_node_400(self, qa, home):
        # 409 when QAT is in cooldown/active war (checked before node validation)
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": home}, headers=qa["headers"], timeout=15)
        assert r.status_code in (400, 409), f"expected 400/409, got {r.status_code} {r.text[:200]}"
        if r.status_code == 400:
            assert "own_node" in r.text or "own" in r.text.lower()

    def test_declare_non_adjacent_400(self, qa, home):
        far = max(range(361), key=lambda n: abs(n % 19 - home % 19) + abs(n // 19 - home // 19))
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": far}, headers=qa["headers"], timeout=15)
        # 400 not_adjacent OR 409 if QAT is already in a war/cooldown/contested
        assert r.status_code in (400, 409), f"expected 400/409, got {r.status_code} {r.text[:200]}"
        if r.status_code == 400:
            assert "not_adjacent" in r.text.lower() or "adjacent" in r.text.lower()

    def test_declare_invalid_node_id_422(self, qa):
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": 999}, headers=qa["headers"], timeout=15)
        assert r.status_code == 422, r.text  # pydantic ge=0, le=360


# ------------------------ ROSTER VALIDATION ------------------------

@pytest.fixture(scope="module")
def prep_war(qa, home):
    """A war in prep declared by [QAT], created here so roster validation never skips."""
    clear_war_cooldown(qa["headers"])
    targets = border_nodes(qa["headers"], alliance_of(qa["headers"])["id"])
    for node_id in [n["node_id"] for n in targets]:
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": node_id}, headers=qa["headers"], timeout=15)
        if r.status_code == 200:
            return r.json()["id"]
    pytest.skip(f"could not declare on any node bordering {home}")


class TestRosterValidation:
    def test_roster_too_many_ids_400(self, qa, prep_war):
        r = requests.post(f"{BASE}/wars/roster", json={"war_id": prep_war, "player_ids": [f"p{i}" for i in range(11)]}, headers=qa["headers"], timeout=15)
        assert r.status_code == 400, f"expected 400 roster_size, got {r.status_code} {r.text[:200]}"
        assert "roster_size" in r.text.lower() or "max" in r.text.lower()

    def test_roster_non_officer_403(self, bot1, prep_war):
        # bot1 is a member but NOT officer/leader of QAT → should get 403 officer_required
        r = requests.post(f"{BASE}/wars/roster", json={"war_id": prep_war, "player_ids": []}, headers=bot1["headers"], timeout=15)
        assert r.status_code == 403, f"expected 403 officer_required, got {r.status_code} {r.text[:200]}"


# ------------------------ FULL WAR E2E ------------------------

class TestWarE2E:
    """End-to-end: declare (if possible) → set roster → war-shift → tick → verify snapshot & rewards idempotent."""

    def test_full_flow(self, qa, bot1, prep_war):
        war_id = prep_war

        # get bot player_ids from alliance mine
        mine = alliance_of(qa["headers"])
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
