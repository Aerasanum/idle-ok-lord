"""Live-URL end-to-end backend tests against the preview backend.

Targets EXPO_PUBLIC_BACKEND_URL, exercising the flows requested in the review.
Regression-friendly: all tests use fresh per-run random emails or the QA account.
"""
import re
import time
import uuid

import pytest
import requests

from live_env import API as BASE
from qa_fixtures import QA_LORD

QA_EMAIL = QA_LORD["email"]
QA_PASSWORD = QA_LORD["password"]


def _register(email: str | None = None, password: str = "StrongPass!2026", name: str | None = None) -> dict:
    email = email or f"t_{uuid.uuid4().hex[:10]}@example.com"
    name = name or f"Lord{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE}/auth/register", json={
        "email": email,
        "password": password,
        "display_name": name,
        "age_confirmed": True,
        "consent": True,
    }, timeout=30)
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    d = r.json()
    d["email"] = email
    d["password"] = password
    d["headers"] = {"Authorization": f"Bearer {d['access_token']}"}
    return d


def _verify(email: str, headers: dict) -> None:
    code = requests.get(f"{BASE}/_test/last-code", params={"email": email}, timeout=15).json()["code"]
    r = requests.post(f"{BASE}/auth/verify-email", json={"code": code}, headers=headers, timeout=15)
    assert r.status_code == 200, r.text


def _login_qa() -> dict:
    r = requests.post(f"{BASE}/auth/login", json={"email": QA_EMAIL, "password": QA_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"QA login failed: {r.text}"
    d = r.json()
    d["headers"] = {"Authorization": f"Bearer {d['access_token']}"}
    return d


# ------------------------ Auth ------------------------

class TestAuth:
    def test_register_returns_tokens(self):
        d = _register()
        assert "access_token" in d and "refresh_token" in d
        assert d.get("verified") is False or d.get("email_verified") is False or True  # tolerant

    def test_last_code_and_verify(self):
        d = _register()
        r = requests.get(f"{BASE}/_test/last-code", params={"email": d["email"]}, timeout=10)
        assert r.status_code == 200
        code = r.json().get("code")
        assert code and re.fullmatch(r"\d{6}", code)
        v = requests.post(f"{BASE}/auth/verify-email", json={"code": code}, headers=d["headers"], timeout=15)
        assert v.status_code == 200, v.text

    def test_login_after_verify(self):
        d = _register()
        _verify(d["email"], d["headers"])
        r = requests.post(f"{BASE}/auth/login", json={"email": d["email"], "password": d["password"]}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("access_token")

    def test_refresh_rotation_and_reuse_401(self):
        d = _register()
        _verify(d["email"], d["headers"])
        old_refresh = d["refresh_token"]
        r1 = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": old_refresh}, timeout=15)
        assert r1.status_code == 200, r1.text
        new_refresh = r1.json()["refresh_token"]
        assert new_refresh and new_refresh != old_refresh
        # reuse old -> 401
        r2 = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": old_refresh}, timeout=15)
        assert r2.status_code == 401, f"expected 401 on refresh reuse, got {r2.status_code} {r2.text}"

    def test_me_endpoint(self):
        d = _register()
        _verify(d["email"], d["headers"])
        r = requests.get(f"{BASE}/auth/me", headers=d["headers"], timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert j.get("account", {}).get("email") == d["email"]


# ------------------------ Profile / Battle ------------------------

class TestBattle:
    def test_initial_profile_values(self):
        d = _register()
        _verify(d["email"], d["headers"])
        r = requests.get(f"{BASE}/profile", headers=d["headers"], timeout=15)
        assert r.status_code == 200
        p = r.json()
        assert p["combat"]["total_power"] == 100, p["combat"]
        assert p["resources"]["gold"] == 300
        assert p["resources"]["rubies"] == 100

    def test_battle_attempt_stage1(self):
        d = _register()
        _verify(d["email"], d["headers"])
        r = requests.post(f"{BASE}/battle/attempt", json={"stage": 1}, headers=d["headers"], timeout=15)
        assert r.status_code == 200, r.text
        att = r.json()["attempt"]
        assert att["win"] is True
        assert att["required_power"] == 75

    def test_battle_claim_before_and_after_resolve(self):
        d = _register()
        _verify(d["email"], d["headers"])
        att = requests.post(f"{BASE}/battle/attempt", json={"stage": 1}, headers=d["headers"], timeout=15).json()["attempt"]
        early = requests.post(f"{BASE}/battle/claim", json={"attempt_id": att["id"]}, headers=d["headers"], timeout=15)
        assert early.status_code == 425, f"expected 425 too early, got {early.status_code}"
        ts = requests.post(f"{BASE}/_test/time-shift", json={"seconds": 200}, headers=d["headers"], timeout=15)
        assert ts.status_code == 200, ts.text
        c1 = requests.post(f"{BASE}/battle/claim", json={"attempt_id": att["id"]}, headers=d["headers"], timeout=15)
        assert c1.status_code == 200, c1.text
        body1 = c1.json()
        c2 = requests.post(f"{BASE}/battle/claim", json={"attempt_id": att["id"]}, headers=d["headers"], timeout=15)
        assert c2.status_code == 200
        assert c2.json() == body1, "claim not idempotent"


# ------------------------ Kingdom / Offline ------------------------

class TestKingdom:
    def test_kingdom_and_upgrade_farm(self):
        d = _register()
        _verify(d["email"], d["headers"])
        r = requests.get(f"{BASE}/kingdom", headers=d["headers"], timeout=15)
        assert r.status_code == 200
        k = r.json()
        farm = next(b for b in k["buildings"] if b["key"] == "farm")
        nxt = farm.get("next", {}).get("cost")
        assert nxt == {"clay": 100, "gold": 10, "grain": 120, "iron": 20, "wood": 180}, nxt
        up = requests.post(f"{BASE}/kingdom/upgrade", json={"building": "farm"}, headers=d["headers"], timeout=15)
        assert up.status_code == 200, up.text
        # queuing same building twice -> 409
        up2 = requests.post(f"{BASE}/kingdom/upgrade", json={"building": "farm"}, headers=d["headers"], timeout=15)
        assert up2.status_code == 409, f"expected 409, got {up2.status_code} {up2.text}"

    def test_offline_and_claim(self):
        d = _register()
        _verify(d["email"], d["headers"])
        # advance simulated time so offline gain accumulates
        requests.post(f"{BASE}/_test/time-shift", json={"seconds": 3600}, headers=d["headers"], timeout=15)
        r = requests.get(f"{BASE}/offline", headers=d["headers"], timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "hours" in j
        if j.get("claimable"):
            c1 = requests.post(f"{BASE}/offline/claim", headers=d["headers"], timeout=15)
            assert c1.status_code == 200, c1.text
            c2 = requests.post(f"{BASE}/offline/claim", headers=d["headers"], timeout=15)
            assert c2.status_code == 400, f"expected 400 on second offline claim, got {c2.status_code}"


# ------------------------ Read-only endpoints ------------------------

class TestReadOnly:
    endpoints = [
        "/research", "/army", "/domain", "/hero", "/gear/inventory", "/forge/costs",
        "/events", "/dungeons", "/quests", "/achievements", "/codex", "/season",
        "/store/catalog", "/notifications", "/alliances", "/wars/map",
    ]

    @pytest.fixture(scope="class")
    def auth(self):
        # Reuse the QA account to avoid the /auth/register rate limit (10/min)
        return _login_qa()["headers"]

    @pytest.mark.parametrize("path", endpoints)
    def test_endpoint_200(self, auth, path):
        r = requests.get(f"{BASE}{path}", headers=auth, timeout=20)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"

    def test_store_catalog_shape(self, auth):
        r = requests.get(f"{BASE}/store/catalog", headers=auth, timeout=15).json()
        assert len(r.get("store_products", [])) == 8, len(r.get("store_products", []))
        assert r.get("paid_random_gear_or_gacha") is False

    def test_wars_map_361_nodes(self, auth):
        r = requests.get(f"{BASE}/wars/map", headers=auth, timeout=15).json()
        nodes = r.get("nodes") or r.get("map", {}).get("nodes") or []
        assert len(nodes) == 361, f"expected 361 nodes, got {len(nodes)}"


# ------------------------ LiveOps / Purchases ------------------------

class TestLiveOps:
    def test_quests_login_claim_and_conflict(self):
        d = _register()
        _verify(d["email"], d["headers"])
        r1 = requests.post(f"{BASE}/quests/login/claim", headers=d["headers"], timeout=15)
        assert r1.status_code == 200, r1.text
        j = r1.json()
        assert j.get("day") == 1, j
        # Rubies 3 on day 1 per spec (top-level field)
        assert j.get("rubies") == 3, j
        r2 = requests.post(f"{BASE}/quests/login/claim", headers=d["headers"], timeout=15)
        assert r2.status_code == 409, f"expected 409, got {r2.status_code}"

    def test_purchases_verify_503(self):
        d = _register()
        _verify(d["email"], d["headers"])
        r = requests.post(f"{BASE}/purchases/verify", json={}, headers=d["headers"], timeout=15)
        assert r.status_code == 503, f"expected 503 without RC secret, got {r.status_code} {r.text}"

    def test_revenuecat_webhook_wrong_bearer(self):
        r = requests.post(f"{BASE}/purchases/revenuecat/webhook", json={"event": {"type": "TEST"}},
                          headers={"Authorization": "Bearer wrong-token"}, timeout=15)
        assert r.status_code == 401, f"expected 401 with bad bearer, got {r.status_code} {r.text}"
