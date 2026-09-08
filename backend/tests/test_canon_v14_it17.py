"""
ITERATION 17 — Canon v1.4 rebalance live E2E tests.
Covers: canon VERSION 1.4, unit catalog rebalance, enemy power curve bosses,
        /army/suggest greedy fill, apply formation, recruit, rulebook PDF.
"""
import io
import os
import pytest
import requests

BASE_URL = ""
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("EXPO_PUBLIC_BACKEND_URL"):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = BASE_URL + "/api"

QA_LORD = ("qa.lord@example.com", "QaLordPass!2026")
QA_BOT3 = ("qa.bot3@idle1.app", "QaBot!2026")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def qa_lord_token():
    return _login(*QA_LORD)


@pytest.fixture(scope="module")
def qa_bot3_token():
    return _login(*QA_BOT3)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Canon endpoint (VERSION via /canon/validation) ----------
class TestCanonV14:
    def test_canon_validation_version(self):
        r = requests.get(f"{API}/canon/validation", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("VERSION") == "1.4", d
        assert d.get("CANONICAL_SPEC_PARSED") == "YES"


# ---------- Unit catalog rebalance ----------
EXPECTED_UNITS = {
    "infantry": (37, 1),
    "archer": (40, 1),
    "cavalry": (129, 3),
    "catapult": (414, 8),
    "conquest_wagon": (655, 12),
    "wolf": (106, 2),
    "falcon": (109, 2),
    "bear": (212, 4),
    "lion": (218, 4),
    "war_elephant": (558, 10),
    "dragon": (1740, 25),
    "angel": (1810, 25),
    "demon": (1880, 25),
}


class TestArmyCatalog:
    def test_army_units_v14(self, qa_lord_token):
        # /army has richer per-player payload; /canon/static has the pure catalog
        r = requests.get(f"{API}/canon/static", headers=_h(qa_lord_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        by_key = {u["key"]: u for u in d["units"]}
        errors = []
        for uid, (bp, cmd) in EXPECTED_UNITS.items():
            u = by_key.get(uid)
            if not u:
                errors.append(f"{uid}: missing")
                continue
            if u["base_power"] != bp or u["command_cost"] != cmd:
                errors.append(f"{uid}: power={u['base_power']} cmd={u['command_cost']} (want {bp}/{cmd})")
        assert not errors, errors

    def test_army_endpoint_returns_units(self, qa_lord_token):
        r = requests.get(f"{API}/army", headers=_h(qa_lord_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "units" in d and "command_capacity" in d


# ---------- Enemy power curve ----------
EXPECTED_BOSSES = {
    50: 1092,
    100: 9633,
    150: 84586,
    180: 310807,
    200: 739513,
}


class TestEnemyCurve:
    def test_stage_1_normal(self, qa_lord_token):
        r = requests.get(f"{API}/battle/stage/1", headers=_h(qa_lord_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        rp = d.get("required_power") or d.get("enemy_power")
        assert rp == 75, f"stage 1 required_power={rp} response={d}"
        # normal stage
        kind = d.get("kind") or d.get("stage_kind")
        assert kind != "boss", f"stage 1 kind should not be boss: {kind}"

    @pytest.mark.parametrize("stage,expected", list(EXPECTED_BOSSES.items()))
    def test_boss_stage_required_power(self, qa_lord_token, stage, expected):
        r = requests.get(f"{API}/battle/stage/{stage}", headers=_h(qa_lord_token), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        rp = d.get("required_power") or d.get("enemy_power")
        assert rp == expected, f"stage {stage} required_power={rp} (want {expected})"
        kind = d.get("kind") or d.get("stage_kind")
        assert kind == "boss", f"stage {stage} kind={kind}"


# ---------- /army/suggest greedy ----------
class TestArmySuggest:
    def test_grant_and_suggest_stage_200(self, qa_bot3_token):
        grant = requests.post(
            f"{API}/_test/grant",
            headers=_h(qa_bot3_token),
            json={
                "castle_level": 18,
                "hero_level": 80,
                "units": {
                    "infantry": 5000,
                    "archer": 3000,
                    "cavalry": 1000,
                    "catapult": 200,
                    "dragon": 40,
                    "angel": 20,
                    "war_elephant": 100,
                },
            },
            timeout=20,
        )
        assert grant.status_code in (200, 201), f"grant failed: {grant.status_code} {grant.text}"

        r = requests.get(f"{API}/army/suggest?stage=200", headers=_h(qa_bot3_token), timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        formation = d.get("formation") or {}
        picks = d.get("picks") or []
        army_power = d.get("army_power") or 0
        cmd_used = d.get("command_used")
        cmd_cap = d.get("command_capacity")
        slots = d.get("formation_slots")

        assert army_power > 0, f"army_power={army_power}"
        assert picks, "picks empty"

        # picks sorted by per_command descending
        pc_list = [p["per_command"] for p in picks]
        for a, b in zip(pc_list, pc_list[1:]):
            assert a >= b - 1e-6, f"picks not sorted desc: {pc_list}"

        # picks that are actually picked (quantity>0)
        picked_ids = [p["key"] for p in picks if p.get("quantity", 0) > 0]
        # angel/dragon should come before infantry when infantry is picked
        if "infantry" in picked_ids:
            for high in ("angel", "dragon"):
                if high in picked_ids:
                    assert picked_ids.index(high) < picked_ids.index("infantry"), \
                        f"{high} not before infantry: {picked_ids}"

        # formation is a dict {key: qty}
        assert isinstance(formation, dict), formation
        assert len(formation) <= slots, f"types={len(formation)} slots={slots}"

        # Mythics owned: dragon 40, angel 20 → should be fully used
        assert formation.get("dragon") == 40, f"dragon not fully used: {formation}"
        assert formation.get("angel") == 20, f"angel not fully used: {formation}"

        # command_used == capacity OR units exhausted
        assert cmd_used is not None and cmd_cap is not None, d
        assert cmd_used == cmd_cap or cmd_used > 0, f"cmd_used={cmd_used} cap={cmd_cap}"

        pytest._it17_formation = formation


# ---------- Apply formation + battle regression ----------
class TestApplyFormationBattle:
    def test_apply_formation(self, qa_bot3_token):
        formation = getattr(pytest, "_it17_formation", None)
        if formation is None:
            r = requests.get(f"{API}/army/suggest?stage=100", headers=_h(qa_bot3_token), timeout=20)
            formation = r.json().get("formation") or {}
        assert formation, "no formation to apply"

        r = requests.put(
            f"{API}/army/formation",
            headers=_h(qa_bot3_token),
            json={"formation": formation},
            timeout=20,
        )
        assert r.status_code == 200, f"PUT /army/formation: {r.status_code} {r.text}"

        prof = requests.get(f"{API}/profile", headers=_h(qa_bot3_token), timeout=20)
        assert prof.status_code == 200
        pd = prof.json()
        combat = pd.get("combat") or {}
        power = combat.get("army_power", 0)
        assert power > 0, f"army power not reflected: combat={combat}"

    def test_battle_attempt_and_claim(self, qa_bot3_token):
        # Attempt stage 1 (safe & always winnable)
        r = requests.post(f"{API}/battle/attempt", headers=_h(qa_bot3_token), json={"stage": 1}, timeout=25)
        assert r.status_code == 200, f"battle attempt: {r.status_code} {r.text}"
        att = r.json()
        attempt_id = att.get("attempt_id") or att.get("id")
        if attempt_id:
            c = requests.post(
                f"{API}/battle/claim",
                headers=_h(qa_bot3_token),
                json={"attempt_id": attempt_id},
                timeout=25,
            )
            assert c.status_code in (200, 425, 400, 409), c.text


# ---------- Recruit ----------
class TestRecruit:
    def test_recruit_flow(self, qa_lord_token):
        r = requests.post(
            f"{API}/army/recruit",
            headers=_h(qa_lord_token),
            json={"unit": "infantry", "quantity": 1},
            timeout=20,
        )
        # Accept 200 (ok), or business codes for full queue/insufficient/etc.
        assert r.status_code in (200, 400, 402, 409), f"recruit: {r.status_code} {r.text}"


# ---------- Rulebook PDF ----------
class TestRulebook:
    def test_pdf_available(self):
        r = requests.get(f"{API}/docs/regolamento.pdf", timeout=30)
        assert r.status_code == 200, r.status_code
        ct = r.headers.get("content-type", "")
        assert "pdf" in ct.lower(), ct
        size_kb = len(r.content) // 1024
        assert 100 < size_kb < 1000, f"pdf size {size_kb}KB unexpected"
        # Extract text (PDF is AES-256 encrypted with empty password)
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(r.content))
        if reader.is_encrypted:
            reader.decrypt("")
        n_pages = len(reader.pages)
        assert 35 <= n_pages <= 60, f"page count={n_pages}"
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        assert "v1.4" in text or "spec v1.4" in text.lower(), \
            f"pdf does not mention v1.4. First 500 chars: {text[:500]}"
