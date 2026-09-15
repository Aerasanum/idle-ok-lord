"""Iteration 15 — Alliance war RESERVES + promotion + reserve withdraw.

The suite builds its own [QAT] -> [ORS] war and fills the attack side to exactly ten,
with qa.bot9 pushed into the reserve queue, then exercises promotion on withdrawal.
[QAT] is seeded with eleven members precisely so the eleventh enlistment overflows.

Does not lock, resolve or cancel the war.
"""
from __future__ import annotations
import pytest
import requests

from live_env import (
    API as BASE,
    declare_fresh_war,
    hdr,
    restore_enemy_border,
    session,
    token,
)
from qa_fixtures import LORD_TESTER, ORS_BOTS, ORS_LEADER, QA_BOTS, QA_LORD


def login(email: str, pw: str) -> str:
    return token(email, pw)


def get_war(tok: str, war_id: str) -> dict:
    r = requests.get(f"{BASE}/wars/{war_id}", headers=hdr(tok), timeout=15)
    assert r.status_code == 200, r.text[:200]
    return r.json()


def enlist(tok: str, war_id: str) -> requests.Response:
    return requests.post(f"{BASE}/wars/{war_id}/enlist", headers=hdr(tok), timeout=15)


def withdraw(tok: str, war_id: str) -> requests.Response:
    return requests.post(f"{BASE}/wars/{war_id}/withdraw", headers=hdr(tok), timeout=15)


@pytest.fixture(scope="module")
def ctx():
    """Declare the war, then enlist qa.bot1..8 and lord.tester to fill the ten slots.

    qa.bot9 enlists last, so it lands in the reserve queue: that is the state the
    promotion assertions below start from.
    """
    qa = session(QA_LORD)
    target = restore_enemy_border(qa, session(ORS_LEADER))
    if target is None:
        pytest.skip("[QAT] and [ORS] share no border; run backend/scripts/seed_qa.py")
    war_id = declare_fresh_war(qa, target)

    sessions = {"qa_lord": qa, "orsi_bot1": session(ORS_BOTS[0])}
    for spec in QA_BOTS[:8]:
        r = enlist(token(spec), war_id)
        assert r.status_code == 200, f"{spec['email']} enlist: {r.status_code} {r.text[:160]}"
    sessions["lord_tester"] = session(LORD_TESTER)
    r = enlist(sessions["lord_tester"]["token"], war_id)
    assert r.status_code == 200, r.text[:200]
    assert r.json()["reserve"] is False, "lord.tester should take the tenth slot, not the reserve"

    sessions["qa_bot9"] = session(QA_BOTS[8])
    r = enlist(sessions["qa_bot9"]["token"], war_id)
    assert r.status_code == 200, r.text[:200]
    assert r.json()["reserve"] is True, "qa.bot9 should overflow into the reserve"

    return {"war_id": war_id,
            "toks": {k: v["token"] for k, v in sessions.items()},
            "pids": {k: v["player_id"] for k, v in sessions.items()}}


class TestInitialState:
    def test_01_war_prep_and_state(self, ctx):
        d = get_war(ctx["toks"]["qa_lord"], ctx["war_id"])
        w = d["war"]
        assert w["status"] == "prep", f"war status={w['status']}"
        assert w["defender_id"], "target should be alliance-held, not an NPC garrison"
        assert len(w["attack_roster"]) == 10, f"attack_roster={w['attack_roster']}"
        assert ctx["pids"]["lord_tester"] in w["attack_roster"], f"lord.tester not in roster: {w['attack_roster']}"
        assert w.get("attack_reserve", []) == [ctx["pids"]["qa_bot9"]], f"attack_reserve={w.get('attack_reserve')}"


class TestReserveAndPromotion:
    def test_02_bot9_enlist_again_returns_409_already_reserve(self, ctx):
        r = enlist(ctx["toks"]["qa_bot9"], ctx["war_id"])
        assert r.status_code == 409, f"expected 409, got {r.status_code} {r.text[:200]}"
        assert "already_reserve" in r.text, r.text[:200]

    def test_03_orsi_bot1_enlist_defense_side(self, ctx):
        # If already enlisted from previous run, first withdraw so we can verify the enlist path.
        w0 = get_war(ctx["toks"]["qa_lord"], ctx["war_id"])["war"]
        if ctx["pids"]["orsi_bot1"] in w0.get("defense_roster", []):
            wr = withdraw(ctx["toks"]["orsi_bot1"], ctx["war_id"])
            assert wr.status_code == 200, wr.text[:200]
        r = enlist(ctx["toks"]["orsi_bot1"], ctx["war_id"])
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("enlisted") is True, body
        assert body.get("reserve") is False, body
        assert ctx["pids"]["orsi_bot1"] in body.get("defense_roster", []), body
        # attack roster must not change
        w = get_war(ctx["toks"]["qa_lord"], ctx["war_id"])["war"]
        assert len(w["attack_roster"]) == 10
        assert ctx["pids"]["lord_tester"] in w["attack_roster"]

    def test_04_lord_tester_withdraw_promotes_bot9(self, ctx):
        r = withdraw(ctx["toks"]["lord_tester"], ctx["war_id"])
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("promoted") == ctx["pids"]["qa_bot9"], f"promoted={body.get('promoted')} expected {ctx['pids']['qa_bot9']}: {body}"
        assert len(body["attack_roster"]) == 10, body
        assert ctx["pids"]["qa_bot9"] in body["attack_roster"], body
        assert ctx["pids"]["lord_tester"] not in body["attack_roster"], body
        assert body.get("attack_reserve", []) == [], f"attack_reserve should be empty: {body}"

    def test_05_lord_tester_reenlists_goes_to_reserve(self, ctx):
        r = enlist(ctx["toks"]["lord_tester"], ctx["war_id"])
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("reserve") is True, body
        assert body.get("enlisted") is False, body
        assert body.get("reserve_position") == 1, f"reserve_position={body.get('reserve_position')}: {body}"
        w = get_war(ctx["toks"]["qa_lord"], ctx["war_id"])["war"]
        assert ctx["pids"]["lord_tester"] in w.get("attack_reserve", [])
        assert len(w["attack_roster"]) == 10

    def test_06_lord_tester_withdraws_from_reserve(self, ctx):
        r = withdraw(ctx["toks"]["lord_tester"], ctx["war_id"])
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("attack_reserve", []) == [], f"reserve should be empty: {body}"
        # roster unchanged 10, no promotion (no one to promote since reserves empty)
        assert len(body["attack_roster"]) == 10, body
        assert body.get("promoted") in (None,), f"unexpected promotion: {body.get('promoted')}"

    def test_07_war_detail_roster_players_contains_names(self, ctx):
        d = get_war(ctx["toks"]["qa_lord"], ctx["war_id"])
        w = d["war"]
        rp = d.get("roster_players", {})
        # every player in roster + reserve on both sides must have a display_name
        ids = list(w["attack_roster"]) + list(w["defense_roster"]) + list(w.get("attack_reserve", [])) + list(w.get("defense_reserve", []))
        assert ids, "no players in rosters or reserves"
        for pid in ids:
            assert pid in rp, f"pid {pid} missing from roster_players"
            assert rp[pid].get("display_name"), f"missing display_name for {pid}: {rp[pid]}"
            assert isinstance(rp[pid].get("hero_level"), int), f"hero_level not int: {rp[pid]}"


class TestFinalState:
    def test_99_final_state_qa_bot9_in_roster_lord_tester_out(self, ctx):
        """Cleanup verification: the war ends with roster 10 (qa.lord + qa.bot1..9) and lord.tester OUT."""
        w = get_war(ctx["toks"]["qa_lord"], ctx["war_id"])["war"]
        assert w["status"] == "prep", f"war must remain in prep: {w['status']}"
        assert len(w["attack_roster"]) == 10
        assert ctx["pids"]["qa_bot9"] in w["attack_roster"], "qa.bot9 must end up in attack_roster"
        assert ctx["pids"]["lord_tester"] not in w["attack_roster"], "lord.tester must be OUT of attack_roster"
        assert ctx["pids"]["lord_tester"] not in w.get("attack_reserve", []), "lord.tester must be OUT of attack_reserve"
