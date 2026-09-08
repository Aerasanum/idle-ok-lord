"""End-game verification (iteration 19) for the max.lord account.

Runs against the live preview backend using EXPO_PUBLIC_BACKEND_URL.
Only READS max.lord's state where possible; write operations that mutate the
account are limited to the ones explicitly listed in the review request
(battle attempt/claim, army recruit, alliance join). Forge/research/kingdom
upgrade are only probed to assert the 400 max-level responses (no state change).
"""
import os
import re
import time
import pytest
import requests
from pathlib import Path


def _load_backend_url() -> str:
    # Prefer EXPO_PUBLIC_BACKEND_URL from /app/frontend/.env
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            m = re.match(r"\s*EXPO_PUBLIC_BACKEND_URL\s*=\s*\"?([^\"\s]+)\"?", line)
            if m:
                return m.group(1).rstrip("/")
    v = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
    if not v:
        raise RuntimeError("EXPO_PUBLIC_BACKEND_URL not set")
    return v.rstrip("/")


BASE = _load_backend_url() + "/api"
EMAIL = "max.lord@idle1.app"
PASSWORD = "MaxLord!2026"


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:300]}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, r.json()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


# --- profile / domain / campaign ---
class TestProfile:
    def test_profile_shows_maxed_state(self, sess):
        r = sess.get(f"{BASE}/profile", timeout=30)
        assert r.status_code == 200, r.text[:300]
        p = r.json()
        assert p.get("domain", {}).get("owned") == 100, p.get("domain")
        camp = p.get("campaign", {})
        assert camp.get("highest_cleared") == 200, camp
        # castle 20
        assert p.get("castle_level", p.get("castle", {}).get("level")) == 20 or \
            p.get("kingdom", {}).get("castle_level") == 20


# --- battle stage 200 ---
class TestBattleStage200:
    def test_stage_200_required_power(self, sess):
        r = sess.get(f"{BASE}/battle/stage/200", timeout=30)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert j.get("required_power") == 739513, j.get("required_power")

    def test_attempt_and_claim_stage_200(self, sess):
        r = sess.post(f"{BASE}/battle/attempt", json={"stage": 200}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        att = j.get("attempt") or j
        assert att.get("win") is True, att
        aid = att.get("id") or att.get("attempt_id") or j.get("attempt_id")
        assert aid, j
        # advance clock and claim
        r2 = sess.post(f"{BASE}/_test/time-shift", json={"seconds": 120}, timeout=30)
        assert r2.status_code == 200, r2.text[:300]
        r3 = sess.post(f"{BASE}/battle/claim", json={"attempt_id": aid}, timeout=60)
        assert r3.status_code == 200, r3.text[:300]
        c = r3.json()
        assert (c.get("win") is True) or (c.get("attempt", {}).get("win") is True), c


# --- army recruit ---
class TestArmyRecruit:
    def test_recruit_demon(self, sess):
        # queue may be occupied from background load simulator; time-shift
        # ahead enough to drain any pending queue then recruit.
        sess.post(f"{BASE}/_test/time-shift", json={"seconds": 24 * 3600}, timeout=30)
        r = sess.post(f"{BASE}/army/recruit", json={"unit": "demon", "quantity": 10}, timeout=30)
        # Accept 200 OK or 409 queue_full (background simulator races with us)
        assert r.status_code in (200, 409), f"{r.status_code} {r.text[:300]}"
        if r.status_code == 409:
            assert "queue_full" in r.text, r.text[:300]


# --- max-level guards (should return 400/409) ---
class TestMaxLevelGuards:
    def test_forge_upgrade_maxed(self, sess):
        r = sess.post(f"{BASE}/forge/upgrade", json={"slot": "weapon"}, timeout=30)
        assert r.status_code in (400, 409), f"{r.status_code} {r.text[:300]}"
        assert "forge_max" in r.text or "max" in r.text.lower(), r.text[:300]

    def test_research_start_maxed(self, sess):
        # pick any node - use economy.crop_yield which exists in canon
        r = sess.post(f"{BASE}/research/start", json={"node": "economy.crop_yield"}, timeout=30)
        assert r.status_code in (400, 409), f"{r.status_code} {r.text[:300]}"
        assert "max_level" in r.text or "max" in r.text.lower(), r.text[:300]

    def test_kingdom_upgrade_maxed(self, sess):
        r = sess.post(f"{BASE}/kingdom/upgrade", json={"building": "farm"}, timeout=30)
        assert r.status_code in (400, 409), f"{r.status_code} {r.text[:300]}"
        assert "max_level" in r.text or "max" in r.text.lower(), r.text[:300]


# --- quests alternatives ---
class TestQuestAlternatives:
    def test_quests_alt_active(self, sess):
        r = sess.get(f"{BASE}/quests", timeout=30)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        daily = j.get("daily", {})
        templates = {t.get("key"): t for t in daily.get("templates", [])}
        assert "forge_upgrade" in templates, list(templates.keys())
        assert templates["forge_upgrade"].get("alt_active") is True, templates["forge_upgrade"]
        assert templates.get("start_or_finish_research", {}).get("alt_active") is True, templates.get("start_or_finish_research")
        # Italian text with 'alternativa' marker on either the template or the task
        tasks = daily.get("tasks", {})
        combined = str(templates.get("forge_upgrade", {})) + str(tasks.get("forge_upgrade", {}))
        assert "Riforgia" in combined or "riforgia" in combined.lower(), combined[:500]


# --- alliances and wars ---
class TestAlliancesAndWars:
    def test_join_or_create_alliance(self, sess):
        r = sess.post(
            f"{BASE}/alliances",
            json={"name": "Maximus Guard", "tag": "MAX", "join_mode": "open"},
            timeout=30,
        )
        # 200 create or already_member ~ 409
        assert r.status_code in (200, 201, 400, 409), f"{r.status_code} {r.text[:300]}"
        if r.status_code >= 400:
            assert "already_member" in r.text or "already" in r.text.lower() or "name_taken" in r.text, r.text[:300]

    def test_wars_map(self, sess):
        r = sess.get(f"{BASE}/wars/map", timeout=30)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        # map should carry nodes or similar list
        assert isinstance(j, dict), type(j)
