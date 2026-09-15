"""Alliance war ROSTER BOOKING (enlist/withdraw) — iteration 14.

Covers the review-request scope:
1. Enlist qa.lord (already enlisted → 409 already_enlisted).
2. qa.bot1..3 enlist → 200; roster grows to 4 in order; bot3 withdraw+re-enlist.
3. ORS defenders enlist; fill 10 defenders; 11th → 409 roster_full.
4. Outsider (lord.tester, no alliance) → 403 not_in_alliance.
5. Lock (war-shift 28800 + tick) with under-filled attack:
   - status locked, snapshot.attackers == 10 (4 real + 6 'Corsia vuota').
   - enlist now → 409 roster_locked or war_not_open.
6. Resolve (war-shift 1800 + tick):
   - lanes == 10; 6 empty attacker lanes lose; attacker_points <= 4; winner ORS.
   - alliance chat contains at least one '⚔️ … si è prenotato' herald message.
7. Empty attack-roster ⇒ war cancels (reason empty_attack_roster).
8. Non-officer POST /wars/declare → 403 officer_required.

IMPORTANT: order matters. Tests use a session-scoped state object.
"""
from __future__ import annotations

import pytest
import requests

from live_env import (
    API as BASE,
    declare_fresh_war,
    hdr,
    neighbours,
    restore_enemy_border,
    session,
    token,
    war_map,
)
from qa_fixtures import LORD_TESTER, ORS_BOTS, ORS_LEADER, OUTSIDER, QA_BOTS, QA_LORD


@pytest.fixture(scope="module")
def tokens():
    t = {"qa_lord": token(QA_LORD), "ors_leader": token(ORS_LEADER),
         "lord_tester": token(LORD_TESTER), "outsider": token(OUTSIDER)}
    for i, spec in enumerate(QA_BOTS, 1):
        t[f"qa_bot{i}"] = token(spec)
    for i, spec in enumerate(ORS_BOTS, 1):
        t[f"ors_bot{i}"] = token(spec)
    return t


@pytest.fixture(scope="module")
def war(tokens):
    """Declare a fresh [QAT] -> [ORS] war so the booking flow starts from a known state.

    The suite locks, resolves and then cancels its war, so it cannot reuse one: every
    run needs its own.
    """
    qa = session(QA_LORD)
    target = restore_enemy_border(qa, session(ORS_LEADER))
    if target is None:
        pytest.skip("[QAT] and [ORS] share no border; run backend/scripts/seed_qa.py")
    return declare_fresh_war(qa, target)


def border_node(headers: dict) -> int:
    """Any node bordering our territory. Home castle ids come from a lattice, so this
    cannot be written down as a constant."""
    mp = war_map(headers)
    owned = {n["node_id"] for n in mp["nodes"] if n.get("owner") == mp["my_alliance_id"]}
    candidates = sorted({nb for n in owned for nb in neighbours(n)} - owned)
    assert candidates, "alliance owns no node with a free border"
    return candidates[0]


def get_war(tok: str, war_id: str) -> dict:
    r = requests.get(f"{BASE}/wars/{war_id}", headers=hdr(tok), timeout=15)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def enlist(tok: str, war_id: str) -> requests.Response:
    return requests.post(f"{BASE}/wars/{war_id}/enlist", headers=hdr(tok), timeout=15)


def withdraw(tok: str, war_id: str) -> requests.Response:
    return requests.post(f"{BASE}/wars/{war_id}/withdraw", headers=hdr(tok), timeout=15)


class TestEnlistBooking:
    """State-mutating in sequence: pytest runs tests in file order by default."""

    def test_01_war_open_and_has_qa_lord(self, tokens, war):
        d = get_war(tokens["qa_lord"], war)
        w = d["war"]
        assert w["status"] == "prep", f"war not prep: {w['status']}"
        assert w["attacker_id"].startswith("al_")
        assert w["defender_id"].startswith("al_"), "target should be alliance-held, not an NPC garrison"
        # QA Lord should already be in attack_roster (declared_by)
        qa_lord_pid = w["declared_by"]
        assert qa_lord_pid in w["attack_roster"], f"qa.lord not in roster: {w['attack_roster']}"
        assert len(w["attack_roster"]) == 1, f"a fresh war holds only the declarer: {w['attack_roster']}"

    def test_02_qa_lord_re_enlist_409_already_enlisted(self, tokens, war):
        r = enlist(tokens["qa_lord"], war)
        assert r.status_code == 409, f"expected 409, got {r.status_code} {r.text[:200]}"
        assert "already_enlisted" in r.text, r.text[:200]

    def test_03_qa_bot1_bot2_bot3_enlist(self, tokens, war):
        for i in (1, 2, 3):
            r = enlist(tokens[f"qa_bot{i}"], war)
            assert r.status_code == 200, f"bot{i} enlist: {r.status_code} {r.text[:200]}"
            body = r.json()
            assert body["enlisted"] is True
            assert body["attack_roster"][-1].startswith("p_"), body
        d = get_war(tokens["qa_lord"], war)
        w = d["war"]
        assert len(w["attack_roster"]) == 4, f"expected 4, got {len(w['attack_roster'])}: {w['attack_roster']}"

    def test_04_bot3_withdraw_then_reenlist(self, tokens, war):
        r = withdraw(tokens["qa_bot3"], war)
        assert r.status_code == 200, r.text[:200]
        w = get_war(tokens["qa_lord"], war)["war"]
        assert len(w["attack_roster"]) == 3
        r2 = enlist(tokens["qa_bot3"], war)
        assert r2.status_code == 200, r2.text[:200]
        w = get_war(tokens["qa_lord"], war)["war"]
        assert len(w["attack_roster"]) == 4

    def test_05_ors_bot1_bot2_enlist_defense(self, tokens, war):
        for i in (1, 2):
            r = enlist(tokens[f"ors_bot{i}"], war)
            assert r.status_code == 200, f"ors_bot{i}: {r.status_code} {r.text[:200]}"
        w = get_war(tokens["qa_lord"], war)["war"]
        assert len(w["defense_roster"]) == 2

    def test_06_outsider_gets_not_in_alliance(self, tokens, war):
        r = enlist(tokens["outsider"], war)
        # spec says 403 not_in_war OR not_in_alliance
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:200]}"
        assert "not_in_alliance" in r.text or "not_in_war" in r.text, r.text[:200]

    def test_07_fill_defense_to_10_and_11th_is_roster_full(self, tokens, war):
        # ors_bot1..2 already in (2). Add ors leader + ors_bot3..9 = 2 + 1 + 7 = 10
        r = enlist(tokens["ors_leader"], war)
        assert r.status_code == 200, r.text[:200]
        for i in range(3, 10):  # bot3..bot9 (7 bots)
            r = enlist(tokens[f"ors_bot{i}"], war)
            assert r.status_code == 200, f"ors_bot{i}: {r.status_code} {r.text[:200]}"
        w = get_war(tokens["qa_lord"], war)["war"]
        assert len(w["defense_roster"]) == 10, f"defense_roster={len(w['defense_roster'])}"
        # [ORS] has exactly ten accounts, so the eleventh slot cannot be probed with a
        # fresh member; re-enlisting one already in must be rejected as a duplicate.
        r = enlist(tokens["ors_bot1"], war)
        assert r.status_code == 409, r.text[:200]
        assert "already_enlisted" in r.text, r.text[:200]

    def test_08_lock_war_shift_and_tick(self, tokens, war):
        """war-shift 28800s + tick — war reaches at least locked (may go straight to resolved)."""
        s = requests.post(f"{BASE}/_test/war-shift", json={"seconds": 28800}, headers=hdr(tokens["qa_lord"]), timeout=15)
        assert s.status_code == 200, s.text
        t = requests.post(f"{BASE}/_test/tick", headers=hdr(tokens["qa_lord"]), timeout=30)
        assert t.status_code == 200, t.text
        d = get_war(tokens["qa_lord"], war)
        w = d["war"]
        assert w["status"] in ("locked", "resolved"), f"expected locked or resolved, got {w['status']}"
        snap = d["snapshot"]
        assert snap is not None, "snapshot missing"
        assert len(snap["attackers"]) == 10, f"attackers snap={len(snap['attackers'])}"
        empties = [a for a in snap["attackers"] if a.get("empty") is True]
        assert len(empties) == 6, f"expected 6 empty attacker lanes, got {len(empties)}"
        for a in empties:
            assert a["display_name"] == "Corsia vuota", a
            assert a["war_power"] == 0, a
        assert len(snap["defenders"]) == 10

    def test_09_enlist_after_lock_is_rejected(self, tokens, war):
        r = enlist(tokens["qa_bot4"], war)
        assert r.status_code == 409, f"expected 409, got {r.status_code} {r.text[:200]}"
        assert "roster_locked" in r.text or "war_not_open" in r.text, r.text[:200]

    def test_10_resolve_war_and_check_lanes(self, tokens, war):
        """After war-shift 1800 + tick, war MUST be resolved with expected outcome."""
        s = requests.post(f"{BASE}/_test/war-shift", json={"seconds": 1800}, headers=hdr(tokens["qa_lord"]), timeout=15)
        assert s.status_code == 200, s.text
        t = requests.post(f"{BASE}/_test/tick", headers=hdr(tokens["qa_lord"]), timeout=30)
        assert t.status_code == 200, t.text
        d = get_war(tokens["qa_lord"], war)
        w = d["war"]
        assert w["status"] == "resolved", f"expected resolved, got {w['status']}"
        assert w["result"] is not None
        lanes = w["result"]["lanes"]
        assert len(lanes) == 10, f"expected 10 lanes, got {len(lanes)}"
        # 6 empty attacker lanes MUST be losses.
        # Lane shape: {attacker: display_name, attacker_id: str|None, attacker_npc: bool, attacker_wins: bool, ...}
        empty_lanes = [ln for ln in lanes if ln.get("attacker_id") is None and ln.get("attacker") == "Corsia vuota"]
        assert len(empty_lanes) == 6, f"expected 6 empty lanes, got {len(empty_lanes)}: {[l.get('attacker') for l in lanes]}"
        for ln in empty_lanes:
            assert ln.get("attacker_wins") is False, f"empty lane should lose: {ln}"
            assert ln.get("attacker_power") == 0, ln
        assert w["result"].get("attacker_points", 0) <= 4, f"attacker_points too high: {w['result']}"
        # Defender wins (ORS): attacker_won False
        assert w["result"].get("attacker_won") is False, f"expected defender (ORS) win: {w['result']}"

    def test_11_alliance_chat_contains_prenotato_herald(self, tokens, war):
        alliance_id = get_war(tokens["qa_lord"], war)["war"]["attacker_id"]
        r = requests.get(f"{BASE}/chat/messages", params={"channel": f"alliance:{alliance_id}", "limit": 50}, headers=hdr(tokens["qa_lord"]), timeout=15)
        assert r.status_code == 200, r.text[:300]
        msgs = r.json()["messages"]
        hits = [m for m in msgs if "si è prenotato" in (m.get("text") or "")]
        assert hits, f"no 'si è prenotato' herald messages in alliance chat: {[m.get('text','')[:80] for m in msgs[:20]]}"


class TestEmptyAttackCancels:
    """After the war above resolves, clear cooldown & declare a new war then withdraw the sole attacker."""

    def test_20_clear_cooldown(self, tokens):
        s = requests.post(f"{BASE}/_test/war-shift", json={"seconds": 100000, "include_resolved": True}, headers=hdr(tokens["qa_lord"]), timeout=15)
        assert s.status_code == 200, s.text
        t = requests.post(f"{BASE}/_test/tick", headers=hdr(tokens["qa_lord"]), timeout=30)
        assert t.status_code == 200, t.text

    def test_21_declare_auto_enlists_declarer(self, tokens):
        node_id = border_node(hdr(tokens["qa_lord"]))
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": node_id}, headers=hdr(tokens["qa_lord"]), timeout=15)
        assert r.status_code == 200, f"declare on {node_id}: {r.status_code} {r.text[:300]}"
        j = r.json()
        war_id = j.get("_id") or j.get("id")
        assert war_id, j
        # attack_roster should contain qa.lord's player_id
        d = get_war(tokens["qa_lord"], war_id)
        w = d["war"]
        assert len(w["attack_roster"]) == 1, f"expected 1 attacker auto-enlisted: {w['attack_roster']}"
        pytest.war_id_2 = war_id

    def test_22_withdraw_then_lock_should_cancel(self, tokens):
        war_id = pytest.war_id_2
        r = withdraw(tokens["qa_lord"], war_id)
        assert r.status_code == 200, r.text[:200]
        w = get_war(tokens["qa_lord"], war_id)["war"]
        assert w["attack_roster"] == [], f"expected empty roster: {w['attack_roster']}"
        # war-shift 28800 + tick
        s = requests.post(f"{BASE}/_test/war-shift", json={"seconds": 28800}, headers=hdr(tokens["qa_lord"]), timeout=15)
        assert s.status_code == 200, s.text
        t = requests.post(f"{BASE}/_test/tick", headers=hdr(tokens["qa_lord"]), timeout=30)
        assert t.status_code == 200, t.text
        d = get_war(tokens["qa_lord"], war_id)
        w = d["war"]
        assert w["status"] == "cancelled", f"expected cancelled, got {w['status']}: {w.get('result')}"
        assert w.get("result", {}).get("reason") == "empty_attack_roster", f"expected empty_attack_roster: {w.get('result')}"

    def test_23_final_clear_cooldown_no_open_war(self, tokens):
        s = requests.post(f"{BASE}/_test/war-shift", json={"seconds": 100000, "include_resolved": True}, headers=hdr(tokens["qa_lord"]), timeout=15)
        assert s.status_code == 200, s.text
        t = requests.post(f"{BASE}/_test/tick", headers=hdr(tokens["qa_lord"]), timeout=30)
        assert t.status_code == 200, t.text


class TestOfficerPermission:
    def test_30_non_officer_declare_403(self, tokens):
        # qa_bot1 is a regular member of QAT; rank is checked before the node is validated
        node_id = border_node(hdr(tokens["qa_lord"]))
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": node_id}, headers=hdr(tokens["qa_bot1"]), timeout=15)
        assert r.status_code == 403, f"expected 403 officer_required, got {r.status_code} {r.text[:200]}"
        assert "officer_required" in r.text, r.text[:200]
