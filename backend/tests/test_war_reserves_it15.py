"""Iteration 15 — Alliance war RESERVES + promotion + reserve withdraw.

War: war_0b2db37c91bb4cd8b4ca6e933ca8509d (QAT → ORS, node 22, prep).
Initial expected state: attack_roster 10 (qa.lord + qa.bot1..8 + lord.tester at slot 10),
                       attack_reserve [qa.bot9].
Do NOT lock/resolve/cancel this war.
"""
from __future__ import annotations
import os
import pytest
import requests

BASE = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"
WAR_ID = "war_0b2db37c91bb4cd8b4ca6e933ca8509d"


def hdr(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def login(email: str, pw: str) -> str:
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


def get_me(tok: str) -> dict:
    r = requests.get(f"{BASE}/profile", headers=hdr(tok), timeout=15)
    assert r.status_code == 200, r.text[:200]
    return r.json()


def get_war(tok: str) -> dict:
    r = requests.get(f"{BASE}/wars/{WAR_ID}", headers=hdr(tok), timeout=15)
    assert r.status_code == 200, r.text[:200]
    return r.json()


def enlist(tok: str) -> requests.Response:
    return requests.post(f"{BASE}/wars/{WAR_ID}/enlist", headers=hdr(tok), timeout=15)


def withdraw(tok: str) -> requests.Response:
    return requests.post(f"{BASE}/wars/{WAR_ID}/withdraw", headers=hdr(tok), timeout=15)


@pytest.fixture(scope="module")
def ctx():
    toks = {
        "qa_lord": login("qa.lord@example.com", "QaLordPass!2026"),
        "qa_bot9": login("qa.bot9@idle1.app", "QaBot!2026"),
        "orsi_bot1": login("orsi.bot1@idle1.app", "QaBot!2026"),
        "lord_tester": login("lord.tester@idle1.app", "Idle1Lord!2026"),
    }
    pids = {
        "qa_lord": get_me(toks["qa_lord"])["id"],
        "qa_bot9": get_me(toks["qa_bot9"])["id"],
        "orsi_bot1": get_me(toks["orsi_bot1"])["id"],
        "lord_tester": get_me(toks["lord_tester"])["id"],
    }
    return {"toks": toks, "pids": pids}


class TestInitialState:
    def test_01_war_prep_and_state(self, ctx):
        d = get_war(ctx["toks"]["qa_lord"])
        w = d["war"]
        assert w["status"] == "prep", f"war status={w['status']}"
        assert w["node_id"] == 22
        assert len(w["attack_roster"]) == 10, f"attack_roster={w['attack_roster']}"
        assert ctx["pids"]["lord_tester"] in w["attack_roster"], f"lord.tester not in roster: {w['attack_roster']}"
        assert w.get("attack_reserve", []) == [ctx["pids"]["qa_bot9"]], f"attack_reserve={w.get('attack_reserve')}"


class TestReserveAndPromotion:
    def test_02_bot9_enlist_again_returns_409_already_reserve(self, ctx):
        r = enlist(ctx["toks"]["qa_bot9"])
        assert r.status_code == 409, f"expected 409, got {r.status_code} {r.text[:200]}"
        assert "already_reserve" in r.text, r.text[:200]

    def test_03_orsi_bot1_enlist_defense_side(self, ctx):
        # If already enlisted from previous run, first withdraw so we can verify the enlist path.
        w0 = get_war(ctx["toks"]["qa_lord"])["war"]
        if ctx["pids"]["orsi_bot1"] in w0.get("defense_roster", []):
            wr = withdraw(ctx["toks"]["orsi_bot1"])
            assert wr.status_code == 200, wr.text[:200]
        r = enlist(ctx["toks"]["orsi_bot1"])
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("enlisted") is True, body
        assert body.get("reserve") is False, body
        assert ctx["pids"]["orsi_bot1"] in body.get("defense_roster", []), body
        # attack roster must not change
        w = get_war(ctx["toks"]["qa_lord"])["war"]
        assert len(w["attack_roster"]) == 10
        assert ctx["pids"]["lord_tester"] in w["attack_roster"]

    def test_04_lord_tester_withdraw_promotes_bot9(self, ctx):
        r = withdraw(ctx["toks"]["lord_tester"])
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("promoted") == ctx["pids"]["qa_bot9"], f"promoted={body.get('promoted')} expected {ctx['pids']['qa_bot9']}: {body}"
        assert len(body["attack_roster"]) == 10, body
        assert ctx["pids"]["qa_bot9"] in body["attack_roster"], body
        assert ctx["pids"]["lord_tester"] not in body["attack_roster"], body
        assert body.get("attack_reserve", []) == [], f"attack_reserve should be empty: {body}"

    def test_05_lord_tester_reenlists_goes_to_reserve(self, ctx):
        r = enlist(ctx["toks"]["lord_tester"])
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("reserve") is True, body
        assert body.get("enlisted") is False, body
        assert body.get("reserve_position") == 1, f"reserve_position={body.get('reserve_position')}: {body}"
        w = get_war(ctx["toks"]["qa_lord"])["war"]
        assert ctx["pids"]["lord_tester"] in w.get("attack_reserve", [])
        assert len(w["attack_roster"]) == 10

    def test_06_lord_tester_withdraws_from_reserve(self, ctx):
        r = withdraw(ctx["toks"]["lord_tester"])
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("attack_reserve", []) == [], f"reserve should be empty: {body}"
        # roster unchanged 10, no promotion (no one to promote since reserves empty)
        assert len(body["attack_roster"]) == 10, body
        assert body.get("promoted") in (None,), f"unexpected promotion: {body.get('promoted')}"

    def test_07_war_detail_roster_players_contains_names(self, ctx):
        d = get_war(ctx["toks"]["qa_lord"])
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
        w = get_war(ctx["toks"]["qa_lord"])["war"]
        assert w["status"] == "prep", f"war must remain in prep: {w['status']}"
        assert len(w["attack_roster"]) == 10
        assert ctx["pids"]["qa_bot9"] in w["attack_roster"], "qa.bot9 must end up in attack_roster"
        assert ctx["pids"]["lord_tester"] not in w["attack_roster"], "lord.tester must be OUT of attack_roster"
        assert ctx["pids"]["lord_tester"] not in w.get("attack_reserve", []), "lord.tester must be OUT of attack_reserve"
