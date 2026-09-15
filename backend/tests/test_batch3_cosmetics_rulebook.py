"""Iteration 9 - Batch 3 backend tests
Covers:
- Login (qa.lord@example.com)
- GET /api/profile returns hero.name and cosmetics {lord_skin, castle_skin, owned}
- PATCH /api/account/settings {lord_name} — updates hero.name only, invalid values 400
- GET /api/store/cosmetics returns catalog and rubies balance
- POST /api/store/cosmetics/buy — 409 already owned, 404 unknown, buy new lord skin
- POST /api/store/cosmetics/equip — equip owned, 403 not-owned, unequip castle=null
- GET /api/docs/regolamento.pdf — public, pdf, > 100KB
"""
from collections import Counter

import pytest
import requests

from live_env import API, token
from qa_fixtures import QA_LORD, SHOWCASE

QA_EMAIL = QA_LORD["email"]
QA_PASS = QA_LORD["password"]
CANON_LORD_NAME = SHOWCASE["lord_name"]
CANON_LORD_SKIN = SHOWCASE["lord_skin"]
CANON_CASTLE_SKIN = SHOWCASE["castle_skin"]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token(QA_LORD)}"})
    yield s
    # cleanup: restore lord name + equip canonical skins
    try:
        s.patch(f"{API}/account/settings", json={"lord_name": CANON_LORD_NAME}, timeout=15)
        s.post(f"{API}/store/cosmetics/equip", json={"kind": "lord", "key": CANON_LORD_SKIN}, timeout=15)
        s.post(f"{API}/store/cosmetics/equip", json={"kind": "castle", "key": CANON_CASTLE_SKIN}, timeout=15)
    except Exception:
        pass


# ---- profile hero.name + cosmetics ----
def test_profile_has_hero_name_and_cosmetics(session):
    r = session.get(f"{API}/profile", timeout=15)
    assert r.status_code == 200, r.text
    p = r.json()
    assert "hero" in p
    assert isinstance(p["hero"].get("name"), str) and len(p["hero"]["name"]) >= 3
    assert "cosmetics" in p
    c = p["cosmetics"]
    assert "lord_skin" in c
    assert "castle_skin" in c
    assert "owned" in c and isinstance(c["owned"], list)
    # display_name and hero.name are independent
    assert "display_name" in p


# ---- PATCH /account/settings lord_name ----
def test_lord_name_patch_and_display_name_independent(session):
    # snapshot display name
    before = session.get(f"{API}/profile", timeout=15).json()
    display_before = before["display_name"]

    r = session.patch(f"{API}/account/settings", json={"lord_name": "Sir Test"}, timeout=15)
    assert r.status_code == 200, r.text
    p = session.get(f"{API}/profile", timeout=15).json()
    assert p["hero"]["name"] == "Sir Test"
    assert p["display_name"] == display_before, "display_name must not change when only lord_name is patched"

    # invalid: too short (2 chars) → 400
    r_bad = session.patch(f"{API}/account/settings", json={"lord_name": "AB"}, timeout=15)
    assert r_bad.status_code == 400, f"expected 400 for short name, got {r_bad.status_code} {r_bad.text}"

    # restore
    r_back = session.patch(f"{API}/account/settings", json={"lord_name": CANON_LORD_NAME}, timeout=15)
    assert r_back.status_code == 200
    p2 = session.get(f"{API}/profile", timeout=15).json()
    assert p2["hero"]["name"] == CANON_LORD_NAME


# ---- GET /store/cosmetics catalog ----
def test_cosmetics_catalog(session):
    r = session.get(f"{API}/store/cosmetics", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "rubies" in data
    assert isinstance(data["rubies"], int)
    items = data.get("catalog") or data.get("items") or data.get("skins")
    assert items, f"no catalog key in response: {list(data.keys())}"
    kinds = Counter(it["kind"] for it in items)
    assert kinds == {"lord": 6, "castle": 4, "army": 4}, f"catalog composition changed: {dict(kinds)}"
    assert len(items) == 14, f"expected 14 skins, got {len(items)}"
    for it in items:
        for f in ["key", "name", "rubies", "rarity", "owned", "equipped"]:
            assert f in it, f"missing field {f} in item {it.get('key')}"
    # qa already owns and equips lord_frost_warden + castle_dragon_keep
    frost = next(it for it in items if it["key"] == CANON_LORD_SKIN)
    assert frost["owned"] is True and frost["equipped"] is True
    dragon = next(it for it in items if it["key"] == CANON_CASTLE_SKIN)
    assert dragon["owned"] is True and dragon["equipped"] is True


# ---- POST /store/cosmetics/buy: 409, 404, 200 ----
def test_buy_already_owned_and_unknown_and_new(session):
    # 409 already owned
    r_dup = session.post(f"{API}/store/cosmetics/buy", json={"key": CANON_LORD_SKIN}, timeout=15)
    assert r_dup.status_code == 409, f"expected 409 already_owned, got {r_dup.status_code} {r_dup.text}"

    # 404 unknown
    r_unk = session.post(f"{API}/store/cosmetics/buy", json={"key": "lord_does_not_exist_zzz"}, timeout=15)
    assert r_unk.status_code == 404, f"expected 404 unknown, got {r_unk.status_code} {r_unk.text}"

    session.post(f"{API}/_test/grant", json={"resources": {"rubies": 2000}}, timeout=15)

    # Buy any lord skin not yet owned. Pinning one key meant this skipped on every run
    # after the first, because the purchase is permanent.
    before = session.get(f"{API}/store/cosmetics", timeout=15).json()
    before_rubies = before["rubies"]
    target = next((it for it in before["catalog"]
                   if it["kind"] == "lord" and not it["owned"] and it["key"] != CANON_LORD_SKIN), None)
    if not target:
        pytest.skip("QA owns every lord skin; nothing left to buy")
    cost = target["rubies_now"]
    r_buy = session.post(f"{API}/store/cosmetics/buy", json={"key": target["key"]}, timeout=15)
    assert r_buy.status_code == 200, r_buy.text
    assert r_buy.json().get("bought") == target["key"], r_buy.json()
    after = session.get(f"{API}/store/cosmetics", timeout=15).json()
    assert after["rubies"] == before_rubies - cost, f"rubies decreased incorrectly: {before_rubies} → {after['rubies']} (cost {cost})"
    prof = session.get(f"{API}/profile", timeout=15).json()
    assert prof["cosmetics"]["lord_skin"] == target["key"], "buying a skin equips it"


# ---- POST /store/cosmetics/equip ----
def test_equip_owned_and_not_owned_and_null(session):
    # re-equip canonical lord
    r1 = session.post(f"{API}/store/cosmetics/equip", json={"kind": "lord", "key": CANON_LORD_SKIN}, timeout=15)
    assert r1.status_code == 200, r1.text
    prof = session.get(f"{API}/profile", timeout=15).json()
    assert prof["cosmetics"]["lord_skin"] == CANON_LORD_SKIN

    # equip a not-owned key → 403
    r_no = session.post(f"{API}/store/cosmetics/equip", json={"kind": "lord", "key": "lord_golden_emperor"}, timeout=15)
    assert r_no.status_code == 403, f"expected 403 not_owned, got {r_no.status_code} {r_no.text}"

    # unequip castle (null)
    r_null = session.post(f"{API}/store/cosmetics/equip", json={"kind": "castle", "key": None}, timeout=15)
    assert r_null.status_code == 200, r_null.text
    prof2 = session.get(f"{API}/profile", timeout=15).json()
    assert prof2["cosmetics"]["castle_skin"] in (None, "", "null")

    # re-equip castle_dragon_keep
    r_re = session.post(f"{API}/store/cosmetics/equip", json={"kind": "castle", "key": CANON_CASTLE_SKIN}, timeout=15)
    assert r_re.status_code == 200
    prof3 = session.get(f"{API}/profile", timeout=15).json()
    assert prof3["cosmetics"]["castle_skin"] == CANON_CASTLE_SKIN


# ---- GET /docs/regolamento.pdf (public) ----
def test_public_rulebook_pdf():
    r = requests.get(f"{API}/docs/regolamento.pdf", timeout=30)
    assert r.status_code == 200, f"got {r.status_code}"
    ctype = r.headers.get("content-type", "")
    assert "application/pdf" in ctype, f"content-type: {ctype}"
    assert len(r.content) > 100 * 1024, f"pdf too small: {len(r.content)} bytes"
