"""Batch 4 backend tests (live API via public EXPO_PUBLIC_BACKEND_URL):
- cosmetics catalog now has 14 items (6 lord + 4 castle + 4 army) with rubies_now
- daily deal is deterministic, discount_pct=30, ends at next UTC midnight (<=24h)
- army skins: equip 403 (not owned), equip null (unequip), re-equip owned, bad_kind 400
- daily-deal buy path: rubies decrease by exactly deal.rubies; response deal:true

Restores QA state at teardown (lord_frost_warden / castle_dragon_keep / army_crimson_legion).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests

from live_env import API as BASE, token
from qa_fixtures import QA_LORD, SHOWCASE

QA_EMAIL = QA_LORD["email"]
QA_PASS = QA_LORD["password"]

CANON_LORD = SHOWCASE["lord_skin"]
CANON_CASTLE = SHOWCASE["castle_skin"]
CANON_ARMY = SHOWCASE["army_skin"]


@pytest.fixture(scope="module")
def h() -> dict:
    tok = token(QA_LORD)
    yield {"Authorization": f"Bearer {tok}"}
    # teardown: restore canonical skins
    for kind, key in (("lord", CANON_LORD), ("castle", CANON_CASTLE), ("army", CANON_ARMY)):
        requests.post(f"{BASE}/store/cosmetics/equip", json={"kind": kind, "key": key}, headers={"Authorization": f"Bearer {tok}"}, timeout=15)


# ---------------- cosmetics catalog + daily deal ----------------
def test_catalog_has_14_items_including_4_army(h):
    r = requests.get(f"{BASE}/store/cosmetics", headers=h, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    cat = d["catalog"]
    assert len(cat) == 14, f"expected 14 items, got {len(cat)}"
    by_kind = {}
    for c in cat:
        by_kind.setdefault(c["kind"], []).append(c)
    assert len(by_kind["lord"]) == 6
    assert len(by_kind["castle"]) == 4
    assert len(by_kind["army"]) == 4
    for a in by_kind["army"]:
        assert "color" in a and a["color"].startswith("#"), a
        assert "glow" in a and a["glow"].startswith("#"), a
    for c in cat:
        assert "rubies_now" in c


def test_daily_deal_shape_and_pricing(h):
    r = requests.get(f"{BASE}/store/cosmetics", headers=h, timeout=15)
    d = r.json()
    deal = d["deal"]
    assert set(deal) >= {"key", "kind", "name", "rubies", "original_rubies", "discount_pct", "ends_at"}
    assert deal["discount_pct"] == 30
    assert deal["rubies"] == round(deal["original_rubies"] * 0.7)
    ends = datetime.fromisoformat(deal["ends_at"].replace("Z", "+00:00"))
    if ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = (ends - now).total_seconds()
    assert 0 < delta <= 24 * 3600 + 60, f"ends_at should be within next 24h (in future), got delta={delta}"
    # ends_at should be a UTC midnight
    assert ends.hour == 0 and ends.minute == 0 and ends.second == 0

    # catalog rubies_now matches deal for the deal key, and equals base rubies otherwise
    for c in d["catalog"]:
        if c["key"] == deal["key"]:
            assert c["rubies_now"] == deal["rubies"]
        else:
            assert c["rubies_now"] == c["rubies"]


# ---------------- buy daily deal ----------------
def test_buy_deal_deducts_discounted_price(h):
    deal_key = requests.get(f"{BASE}/store/cosmetics", headers=h, timeout=15).json()["deal"]["key"]
    # The deal rotates daily and a previous run may already have bought today's skin, so
    # un-own it first: the purchase path must be exercised on every run, not just the first.
    requests.post(f"{BASE}/_test/grant", json={"revoke_cosmetics": [deal_key]}, headers=h, timeout=15)

    r = requests.get(f"{BASE}/store/cosmetics", headers=h, timeout=15)
    d = r.json()
    deal = d["deal"]
    rubies_before = d["rubies"]
    assert deal["key"] == deal_key
    assert deal_key not in (d.get("owned") or [])

    # top up if needed
    if rubies_before < deal["rubies"] + 50:
        requests.post(f"{BASE}/_test/grant", json={"resources": {"rubies": 2000}}, headers=h, timeout=15)
        rubies_before = requests.get(f"{BASE}/store/cosmetics", headers=h, timeout=15).json()["rubies"]

    r = requests.post(f"{BASE}/store/cosmetics/buy", json={"key": deal["key"]}, headers=h, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("bought") == deal["key"]
    assert body.get("deal") is True
    assert body.get("rubies_spent") == deal["rubies"]

    # verify balance
    d2 = requests.get(f"{BASE}/store/cosmetics", headers=h, timeout=15).json()
    assert d2["rubies"] == rubies_before - deal["rubies"], (rubies_before, d2["rubies"], deal["rubies"])
    assert deal["key"] in d2["owned"]

    # give the skin back unless it is one the seed owns, so the QA lord keeps its seeded set
    if deal_key not in (CANON_LORD, CANON_CASTLE, CANON_ARMY):
        requests.post(f"{BASE}/_test/grant", json={"revoke_cosmetics": [deal_key]}, headers=h, timeout=15)


# ---------------- army skin equip semantics ----------------
def test_equip_army_not_owned_returns_403(h):
    # azure_order may have been bought by the deal test on a day when it was the deal
    requests.post(f"{BASE}/_test/grant", json={"revoke_cosmetics": ["army_azure_order"]}, headers=h, timeout=15)
    r = requests.post(f"{BASE}/store/cosmetics/equip", json={"kind": "army", "key": "army_azure_order"}, headers=h, timeout=15)
    assert r.status_code == 403, r.text
    body = r.json()
    assert "not_owned" in str(body).lower() or body.get("detail", {}).get("code") == "not_owned"


def test_equip_army_null_then_re_equip_crimson(h):
    # equip null (unequip)
    r = requests.post(f"{BASE}/store/cosmetics/equip", json={"kind": "army", "key": None}, headers=h, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("equipped") is None

    prof = requests.get(f"{BASE}/profile", headers=h, timeout=15).json()
    assert prof["cosmetics"]["army"] is None, prof["cosmetics"]

    # re-equip crimson
    r = requests.post(f"{BASE}/store/cosmetics/equip", json={"kind": "army", "key": CANON_ARMY}, headers=h, timeout=15)
    assert r.status_code == 200, r.text

    prof = requests.get(f"{BASE}/profile", headers=h, timeout=15).json()
    army = prof["cosmetics"]["army"]
    assert army is not None and army["key"] == CANON_ARMY
    assert army["name"] == "Legione Cremisi"
    assert army["color"] == "#B3162B"
    assert army["glow"] == "#FF6A3D"


def test_equip_bad_kind_returns_400(h):
    r = requests.post(f"{BASE}/store/cosmetics/equip", json={"kind": "banner", "key": None}, headers=h, timeout=15)
    assert r.status_code == 400, r.text
