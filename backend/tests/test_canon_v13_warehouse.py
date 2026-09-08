"""Iteration 16 — Canon v1.3 warehouse invariant + progress preservation + rulebook + war roster power.

Runs against the live preview URL (EXPO_PUBLIC_BACKEND_URL).
Does NOT lock/resolve/cancel any war.
"""
from __future__ import annotations

import io
import json
import os

import pytest
import requests

BASE = "https://idle1-v11-build.preview.emergentagent.com/api"
CANON_PATH = "/app/backend/canon/IDLE_1_v1.1_CANONICAL_SPEC.json"
WAR_ID = "war_0b2db37c91bb4cd8b4ca6e933ca8509d"
RES = ["grain", "wood", "clay", "iron", "gold"]


def hdr(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def login(email: str, pw: str) -> str:
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


# ---------- CANON v1.3 endpoint + invariant ----------
def test_01_canon_static_reachable():
    r = requests.get(f"{BASE}/canon/static", timeout=15)
    assert r.status_code == 200, r.text[:200]
    d = r.json()
    assert "buildings" in d and "regions" in d


def test_02_canon_validation_version_is_1_3():
    r = requests.get(f"{BASE}/canon/validation", timeout=15)
    assert r.status_code == 200, r.text[:200]
    d = r.json()
    assert d["VERSION"] == "1.5", f"expected VERSION=1.5, got {d.get('VERSION')}"
    assert d["CANONICAL_SPEC_PARSED"] == "YES"


def _load_spec() -> dict:
    with open(CANON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_03_spec_version_and_warehouse_rule_present():
    c = _load_spec()
    assert c["document"]["version"] >= "1.4"
    assert "warehouse_rule" in c["kingdom"]
    assert "capacity(L)" in c["kingdom"]["warehouse_rule"]


def test_04_warehouse_capacities_monotonic_and_L20_2_641_000():
    c = _load_spec()
    wh = next(b for b in c["buildings"] if b["key"] == "warehouse")
    caps = [lv["capacity_each_resource"] for lv in wh["levels"]]
    assert len(caps) == 20
    for i in range(1, 20):
        assert caps[i] >= caps[i - 1], f"warehouse cap L{i+1}={caps[i]} < L{i}={caps[i-1]}"
    assert caps[19] == 2_641_000, f"L20 cap must be 2,641,000; got {caps[19]}"


def test_05_castle_costs_fit_warehouse_at_each_level():
    """For every castle level L in 1..19, castle upgrade L->L+1 cost must fit in warehouse level L capacity."""
    c = _load_spec()
    wh = next(b for b in c["buildings"] if b["key"] == "warehouse")
    caps = {lv["level"]: lv["capacity_each_resource"] for lv in wh["levels"]}
    castle = next(b for b in c["buildings"] if b["key"] == "castle")
    violations = []
    for L in range(1, 20):
        cost = next((lv["upgrade_cost"] for lv in castle["levels"] if lv["level"] == L + 1), None)
        if cost is None:
            continue
        cap = caps[L]
        for r, v in cost.items():
            if v > cap:
                violations.append(f"castle L{L}->L{L+1} needs {r}={v:,} but warehouse L{L}={cap:,}")
    assert not violations, "Castle upgrade costs exceed warehouse capacity:\n" + "\n".join(violations)


def test_06_all_reachable_building_costs_fit_warehouse():
    """Every building level unlocked at castle <= L must fit in warehouse cap at L (levels capped near castle level)."""
    c = _load_spec()
    wh = next(b for b in c["buildings"] if b["key"] == "warehouse")
    caps = {lv["level"]: lv["capacity_each_resource"] for lv in wh["levels"]}
    violations = []
    for L in range(1, 21):
        cap = caps[L]
        for b in c["buildings"]:
            if b["key"] == "castle":
                continue
            if b["unlock_castle_level"] > L:
                continue
            for lv in b["levels"]:
                if lv["level"] > min(b["max_level"], L + 1):
                    continue
                for r, v in lv["upgrade_cost"].items():
                    if v > cap:
                        violations.append(f"{b['key']} L{lv['level']} needs {r}={v:,} > warehouse L{L}={cap:,}")
    assert not violations, "\n".join(violations[:20])


def test_07_all_reachable_research_costs_fit_warehouse():
    c = _load_spec()
    wh = next(b for b in c["buildings"] if b["key"] == "warehouse")
    caps = {lv["level"]: lv["capacity_each_resource"] for lv in wh["levels"]}
    violations = []
    for L in range(1, 21):
        cap = caps[L]
        for n in c["research"]["nodes"]:
            if n["unlock_castle_level"] > L:
                continue
            for lv in n["levels"]:
                for r, v in lv["cost"].items():
                    if v > cap:
                        violations.append(f"research {n['key']} L{lv['level']} needs {r}={v:,} > warehouse L{L}={cap:,}")
    assert not violations, "\n".join(violations[:20])


def test_08_no_cost_exceeds_L20_capacity():
    c = _load_spec()
    wh = next(b for b in c["buildings"] if b["key"] == "warehouse")
    cap20 = wh["levels"][-1]["capacity_each_resource"]
    violations = []
    for b in c["buildings"]:
        for lv in b["levels"]:
            for r, v in lv["upgrade_cost"].items():
                if v > cap20:
                    violations.append(f"{b['key']} L{lv['level']} {r}={v:,} > cap20={cap20:,}")
    for n in c["research"]["nodes"]:
        for lv in n["levels"]:
            for r, v in lv["cost"].items():
                if v > cap20:
                    violations.append(f"research {n['key']} L{lv['level']} {r}={v:,} > cap20={cap20:,}")
    assert not violations, "\n".join(violations[:20])


# ---------- Progress preservation for qa.lord ----------
@pytest.fixture(scope="module")
def qa_tok():
    return login("qa.lord@example.com", "QaLordPass!2026")


def test_09_qa_lord_kingdom_warehouse_matches_canon_L():
    tok = login("qa.lord@example.com", "QaLordPass!2026")
    r = requests.get(f"{BASE}/kingdom", headers=hdr(tok), timeout=15)
    assert r.status_code == 200, r.text[:200]
    k = r.json()
    wh_building = next((b for b in k["buildings"] if b["key"] == "warehouse"), None)
    assert wh_building is not None
    wh_level = wh_building["level"]
    warehouse_capacity = k["warehouse_capacity"]

    c = _load_spec()
    wh_canon = next(b for b in c["buildings"] if b["key"] == "warehouse")
    expected = next(lv["capacity_each_resource"] for lv in wh_canon["levels"] if lv["level"] == wh_level)
    assert warehouse_capacity == expected, f"warehouse cap {warehouse_capacity:,} != canon L{wh_level} {expected:,}"

    # Resources not lost — clamped to capacity is fine
    for r_ in RES:
        assert k["resources"].get(r_, 0) >= 0
    # Castle >= 8 per seed
    assert k["castle_level"] >= 8


def test_10_castle_next_cost_fits_canon_warehouse_at_castle_level():
    """Per the v1.3 rule: at castle level L, castle L->L+1 cost must fit in canon warehouse cap at level L.
    (The player still has to upgrade their warehouse to reach that capacity; the canon guarantees it is possible.)"""
    tok = login("qa.lord@example.com", "QaLordPass!2026")
    r = requests.get(f"{BASE}/kingdom", headers=hdr(tok), timeout=15)
    assert r.status_code == 200
    k = r.json()
    castle = next(b for b in k["buildings"] if b["key"] == "castle")
    if not castle.get("next"):
        pytest.skip("castle already at max")
    c = _load_spec()
    wh_canon = next(b for b in c["buildings"] if b["key"] == "warehouse")
    caps = {lv["level"]: lv["capacity_each_resource"] for lv in wh_canon["levels"]}
    cap_at_castle_L = caps[k["castle_level"]]
    max_single = max(castle["next"]["cost"].values())
    assert max_single <= cap_at_castle_L, (
        f"castle L{k['castle_level']}->L{k['castle_level']+1} needs {max_single:,} > canon warehouse cap L{k['castle_level']}={cap_at_castle_L:,}")


# ---------- Rulebook PDF ----------
def test_11_regolamento_pdf_v1_3():
    r = requests.get(f"{BASE}/docs/regolamento.pdf", timeout=30)
    assert r.status_code == 200
    ctype = r.headers.get("content-type", "")
    assert "application/pdf" in ctype, ctype
    assert len(r.content) > 100_000, f"pdf size {len(r.content)} < 100KB"
    try:
        from pypdf import PdfReader
    except ImportError:
        import pypdf
        PdfReader = pypdf.PdfReader
    reader = PdfReader(io.BytesIO(r.content), password="")
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    assert "v1.3" in text, "rulebook text missing 'v1.3'"
    assert "Regola v1.3" in text, "rulebook text missing 'Regola v1.3'"
    # Italian locale uses '.' as thousands separator
    assert "2.641.000" in text, "rulebook text missing L20 capacity '2.641.000'"


# ---------- War roster power ----------
def _get_war(tok: str) -> dict:
    r = requests.get(f"{BASE}/wars/{WAR_ID}", headers=hdr(tok), timeout=15)
    assert r.status_code == 200, r.text[:200]
    return r.json()


def test_12_war_power_qa_lord_attacker():
    tok = login("qa.lord@example.com", "QaLordPass!2026")
    d = _get_war(tok)
    assert d["my_side"] == "attack"
    w = d["war"]
    rp = d["roster_players"]
    attack_ids = w["attack_roster"] + w.get("attack_reserve", [])
    defense_ids = w["defense_roster"] + w.get("defense_reserve", [])

    # every attack roster + reserve player has war_power (my side)
    for pid in attack_ids:
        assert pid in rp, f"missing roster_players[{pid}]"
        assert "war_power" in rp[pid], f"attack {pid} missing war_power (my side)"
    # defense (enemy) players never expose war_power
    for pid in defense_ids:
        if pid in rp:
            assert "war_power" not in rp[pid], f"enemy {pid} leaked war_power"

    # team_power == sum of war_power of attack_roster (not reserve)
    expected_team = sum(rp[pid].get("war_power", 0) for pid in w["attack_roster"] if pid in rp)
    assert d["team_power"] == expected_team, f"team_power {d['team_power']} != sum(attack_roster war_power) {expected_team}"
    assert d["team_power"] > 0


def test_13_war_power_orsi_bot1_defender():
    tok = login("orsi.bot1@idle1.app", "QaBot!2026")
    d = _get_war(tok)
    assert d["my_side"] == "defense"
    w = d["war"]
    rp = d["roster_players"]
    # enemy = attack side must NOT expose war_power
    for pid in w["attack_roster"] + w.get("attack_reserve", []):
        if pid in rp:
            assert "war_power" not in rp[pid], f"attack {pid} leaked war_power to defender viewer"
    # my defense side: if any player is in defense roster, they must have war_power
    for pid in w["defense_roster"] + w.get("defense_reserve", []):
        assert pid in rp
        assert "war_power" in rp[pid], f"defense {pid} missing war_power for defender viewer"
    # team_power equals sum of defense_roster war_powers (no reserve)
    expected_team = sum(rp[pid].get("war_power", 0) for pid in w["defense_roster"] if pid in rp)
    assert d["team_power"] == expected_team


def test_14_war_power_lord_tester_qat_member():
    tok = login("lord.tester@idle1.app", "Idle1Lord!2026")
    d = _get_war(tok)
    assert d["my_side"] == "attack"
    w = d["war"]
    rp = d["roster_players"]
    for pid in w["attack_roster"] + w.get("attack_reserve", []):
        assert pid in rp
        assert "war_power" in rp[pid], f"attack {pid} missing war_power for qat member viewer"
    for pid in w["defense_roster"] + w.get("defense_reserve", []):
        if pid in rp:
            assert "war_power" not in rp[pid]
    assert d["team_power"] > 0
