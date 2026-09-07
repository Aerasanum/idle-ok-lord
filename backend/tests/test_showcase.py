"""Vetrina Profilo — public player showcase endpoint tests (qa.lord)."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://idle1-v11-build.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

QA_EMAIL = "qa.lord@example.com"
QA_PASSWORD = "QaLordPass!2026"


@pytest.fixture(scope="module")
def qa_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": QA_EMAIL, "password": QA_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def qa_ids(qa_session):
    r = qa_session.get(f"{API}/profile")
    assert r.status_code == 200, r.text
    prof = r.json()
    # /profile shape uses player_id or _id — try both
    pid = prof.get("player_id") or prof.get("_id") or prof.get("id")
    assert pid, f"could not extract qa player_id from profile: {list(prof.keys())}"
    return {"player_id": pid, "profile": prof}


# --- unauthenticated ---
def test_showcase_requires_auth(qa_ids):
    r = requests.get(f"{API}/players/{qa_ids['player_id']}/showcase")
    assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


# --- own showcase ---
def test_own_showcase_shape(qa_session, qa_ids):
    pid = qa_ids["player_id"]
    r = qa_session.get(f"{API}/players/{pid}/showcase")
    assert r.status_code == 200, r.text
    s = r.json()

    assert s["is_me"] is True
    assert s["player_id"] == pid
    assert s["hero"]["name"] == "Sir Aldric", f"hero.name = {s['hero'].get('name')}"
    assert isinstance(s["hero"]["level"], int) and s["hero"]["level"] >= 1

    assert isinstance(s["power"]["total"], (int, float)) and s["power"]["total"] > 0
    assert "hero" in s["power"] and "army" in s["power"]

    cos = s["cosmetics"]
    assert cos.get("lord_skin") == "lord_frost_warden", f"lord_skin = {cos.get('lord_skin')}"
    assert isinstance(cos.get("army"), dict), f"army = {cos.get('army')}"
    assert cos["army"].get("color") and re.match(r"^#[0-9A-Fa-f]{6}$", cos["army"]["color"])
    assert cos["army"].get("glow") and re.match(r"^#[0-9A-Fa-f]{6}$", cos["army"]["glow"])

    assert isinstance(s["gear"], list) and len(s["gear"]) > 0, f"gear empty: {s['gear']}"
    for g in s["gear"]:
        assert "slot" in g and "rarity" in g

    assert isinstance(s["alliance"], dict) and s["alliance"].get("tag") == "QAT", f"alliance = {s.get('alliance')}"
    assert isinstance(s["campaign"]["highest_cleared"], int) and s["campaign"]["highest_cleared"] >= 1
    assert isinstance(s["castle_level"], int) and s["castle_level"] >= 1


# --- another alliance member ---
def test_showcase_other_member_is_not_me(qa_session, qa_ids):
    r = qa_session.get(f"{API}/alliances/mine")
    assert r.status_code == 200, r.text
    data = r.json()
    members = data.get("members") or data.get("alliance", {}).get("members") or []
    assert members, f"no members: {data}"
    other = next((m for m in members if m.get("player_id") and m["player_id"] != qa_ids["player_id"]), None)
    assert other, f"no other member found in {[m.get('player_id') for m in members]}"

    r2 = qa_session.get(f"{API}/players/{other['player_id']}/showcase")
    assert r2.status_code == 200, r2.text
    s = r2.json()
    assert s["is_me"] is False
    assert s["player_id"] == other["player_id"]
    assert isinstance(s["display_name"], str) and s["display_name"]
    # Same alliance → same tag
    assert s["alliance"] and s["alliance"]["tag"] == "QAT"
    # Public power should still be a positive number
    assert s["power"]["total"] > 0


# --- 404 ---
def test_showcase_404(qa_session):
    r = qa_session.get(f"{API}/players/does_not_exist/showcase")
    assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"
    body = r.json()
    detail = body.get("detail") or body.get("error") or body
    assert "player_not_found" in str(detail), f"detail = {detail}"
