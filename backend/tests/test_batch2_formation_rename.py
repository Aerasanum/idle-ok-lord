"""
Iteration_8 batch: formation suggest/apply, display_name rename, boss battle timing.
Runs against the LIVE preview backend.
"""
import time
import pytest
import requests

from live_env import API, token
from qa_fixtures import ORS_BOTS, QA_LORD

QA_EMAIL = QA_LORD["email"]
QA_PASSWORD = QA_LORD["password"]
ORS_EMAIL = ORS_BOTS[0]["email"]
ORS_PASSWORD = ORS_BOTS[0]["password"]


def _login(email: str, password: str) -> dict:
    return {"Authorization": f"Bearer {token(email, password)}"}


@pytest.fixture(scope="module")
def qa_headers():
    return _login(QA_EMAIL, QA_PASSWORD)


@pytest.fixture(scope="module")
def ors_headers():
    return _login(ORS_EMAIL, ORS_PASSWORD)


# -------- army/suggest --------
class TestArmySuggest:
    def test_suggest_current_stage(self, qa_headers):
        r = requests.get(f"{API}/army/suggest", headers=qa_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        # Required fields
        for k in ("formation", "picks", "army_power", "current_army_power",
                  "command_used", "command_capacity", "formation_slots",
                  "stage", "region", "kind", "enemy_mix", "required_power", "hero_power"):
            assert k in d, f"missing {k}"
        assert isinstance(d["formation"], dict)
        assert isinstance(d["picks"], list) and len(d["picks"]) > 0
        # command_used <= capacity
        assert d["command_used"] <= d["command_capacity"], f"command_used {d['command_used']} > capacity {d['command_capacity']}"
        # number of unit types with quantity > 0 <= formation_slots
        types_used = sum(1 for q in d["formation"].values() if q > 0)
        assert types_used <= d["formation_slots"], f"types {types_used} exceed slots {d['formation_slots']}"
        # every quantity <= owned
        by_key = {p["key"]: p for p in d["picks"]}
        for k, qty in d["formation"].items():
            assert k in by_key, f"formation key {k} missing from picks"
            assert qty <= by_key[k]["owned"], f"{k}: qty {qty} > owned {by_key[k]['owned']}"
        # picks schema
        for p in d["picks"]:
            for f in ("key", "name", "owned", "cost", "per_command", "counter_pct", "quantity"):
                assert f in p, f"pick missing {f}: {p}"

    def test_suggest_stage_50_is_boss(self, qa_headers):
        r = requests.get(f"{API}/army/suggest?stage=50", headers=qa_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["kind"] == "boss", f"expected boss for stage 50, got {d['kind']}"
        assert d["stage"] == 50


# -------- army/formation apply --------
class TestFormationApply:
    def test_apply_suggested_formation(self, qa_headers):
        sug = requests.get(f"{API}/army/suggest", headers=qa_headers, timeout=15).json()
        formation = sug["formation"]
        # Save current formation to restore later
        cur = requests.get(f"{API}/army", headers=qa_headers, timeout=15).json()
        original = dict(cur.get("formation", {}))

        r = requests.put(f"{API}/army/formation", headers=qa_headers, json={"formation": formation}, timeout=15)
        assert r.status_code == 200, r.text
        # Verify GET /army reflects the update
        after = requests.get(f"{API}/army", headers=qa_headers, timeout=15).json()
        applied = after.get("formation", {})
        for k, v in formation.items():
            assert applied.get(k) == v, f"formation {k}: expected {v}, got {applied.get(k)}"

        # Restore original
        requests.put(f"{API}/army/formation", headers=qa_headers, json={"formation": original}, timeout=15)


# -------- account/settings rename --------
class TestAccountRename:
    def test_rename_display_name(self, qa_headers):
        # Grab current
        cur = requests.get(f"{API}/profile", headers=qa_headers, timeout=15).json()
        original_name = cur.get("display_name")
        try:
            r = requests.patch(f"{API}/account/settings", headers=qa_headers,
                               json={"display_name": "QA Temp"}, timeout=15)
            assert r.status_code == 200, r.text
            p = requests.get(f"{API}/profile", headers=qa_headers, timeout=15).json()
            assert p.get("display_name") == "QA Temp", f"expected QA Temp, got {p.get('display_name')}"
        finally:
            # Always restore to canonical 'QA Lord'
            requests.patch(f"{API}/account/settings", headers=qa_headers,
                           json={"display_name": "QA Lord"}, timeout=15)
            p2 = requests.get(f"{API}/profile", headers=qa_headers, timeout=15).json()
            assert p2.get("display_name") == "QA Lord", f"restore failed: {p2.get('display_name')}"


# -------- battle timing: boss wave is last 35% of duration --------
class TestBossBattleTiming:
    def test_boss_wave_last_35pct(self, qa_headers):
        # The QA lord is used because the bots have not cleared stage 50, and a locked
        # stage cannot be attempted at all.
        st = requests.get(f"{API}/battle/stage/50", headers=qa_headers, timeout=15)
        assert st.status_code == 200, st.text
        assert st.json().get("kind") == "boss", f"stage 50 not boss: {st.json().get('kind')}"

        # POST /battle/attempt with stage=50 returns the attempt (with timeline) directly
        r = requests.post(f"{API}/battle/attempt", headers=qa_headers,
                          json={"stage": 50}, timeout=20)
        assert r.status_code == 200, f"attempt failed: {r.status_code} {r.text}"
        data = r.json()
        attempt = data.get("attempt") or data
        assert attempt.get("kind") == "boss", f"attempt kind not boss: {attempt.get('kind')}"
        timeline = attempt.get("timeline") or {}
        waves = timeline.get("waves") or []
        assert len(waves) > 0, f"no waves in timeline: {timeline}"

        duration = float(attempt.get("duration") or (waves[-1]["t_end"] - waves[0]["t_start"]))
        assert duration > 0

        last = waves[-1]
        boss_dur = float(last["t_end"]) - float(last["t_start"])
        ratio = boss_dur / duration
        # spec: ~35% (allow 30-40% band)
        assert 0.30 <= ratio <= 0.40, f"boss wave ratio {ratio:.3f} not ~0.35 (dur={duration}, boss={boss_dur})"
