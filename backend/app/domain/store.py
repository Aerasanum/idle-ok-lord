"""Store & payments (I14): canonical catalog, ruby-priced consumables, RevenueCat webhook/sync with idempotent crediting,
entitlements, restore and refund reconciliation. No client-trusted credit; no fake verification."""
import hashlib
import hmac
import json
import time
from datetime import timedelta

import httpx

from ..core import db, ledger
from ..core.canon import canon
from ..core.config import settings
from ..core.util import aware, clean, day_key, fail, new_id, now
from .liveops import season_bounds, week_start
from .player import production_per_hour
from .progress import Ops, resources_inc

RC_API = "https://api.revenuecat.com/v1"


def catalog() -> dict:
    m = canon()["monetization"]
    ev = canon()["events"]
    return {
        "premium_currency": m["premium_currency"],
        "display_price_rule": m["display_price_rule"],
        "store_products": [
            *[{"sku": r["sku"], "kind": "consumable", "title": f"{r['rubies']} Rubies", "grant": {"rubies": r["rubies"]}, "reference_eur": r["reference_eur"]} for r in m["ruby_packs"]],
            {"sku": m["starter_bundle"]["sku"], "kind": "non_consumable", "title": "Starter Bundle", "grant": m["starter_bundle"]["contents"], "reference_eur": m["starter_bundle"]["reference_eur"], "exclusive_power": m["starter_bundle"]["exclusive_power"]},
            {"sku": ev["event_pass"]["sku"], "kind": "pass", "title": "Event Pass (7 days)", "entitlement": "event_pass", "reference_eur": ev["event_pass"]["reference_eur"], "duration_days": ev["event_pass"]["duration_days"]},
            {"sku": m["season_pass"]["sku"], "kind": "pass", "title": "Season Pass (28 days)", "entitlement": "season_pass", "reference_eur": m["season_pass"]["reference_eur"], "duration_days": m["season_pass"]["duration_days"]},
        ],
        "ruby_items": {
            "resource_crates": m["resource_crates"],
            "dungeon_extra_entry_rubies": m["dungeon_extra_entry_rubies"],
            "alliance_boss_extra_attack_rubies": m["alliance_boss_extra_attack_rubies"],
            "event_energy_refill": ev["energy_refill"],
            "pve_booster": ev["pve_booster"],
            "speedup_formula": m["speedup_formula_rubies"],
            "talent_respec_rubies": canon()["hero"]["talents"]["respec_rubies"],
        },
        "cosmetics_categories": m["cosmetics"],
        "paid_random_gear_or_gacha": m["paid_random_gear_or_gacha"],
        "rewarded_ads": m["rewarded_ads_v1_1"],
        "revenuecat_configured": bool(settings.RC_SECRET),
    }


async def buy_crate(p: dict, key: str) -> dict:
    crate = next((c for c in canon()["monetization"]["resource_crates"] if c["key"] == key), None)
    if not crate:
        raise fail(404, "crate_not_found")
    today = day_key()
    used = (p.get("store_daily") or {}).get(today, {}).get(key, 0)
    if used >= crate["daily_limit"]:
        raise fail(409, "daily_limit", f"Daily limit {crate['daily_limit']}")
    prod = production_per_hour(p)
    grant = {k: int(v * crate["production_hours_equivalent"]) for k, v in prod.items()}
    ops = Ops()
    ops.inc("resources.rubies", -crate["rubies"]).inc(f"store_daily.{today}.{key}", 1)
    resources_inc(ops, grant)
    res = await db.players.update_one({"_id": p["_id"], "version": p["version"], "resources.rubies": {"$gte": crate["rubies"]}}, {**ops.build(), "$inc": {**ops.incs, "version": 1}})
    if res.matched_count == 0:
        raise fail(409, "insufficient_rubies", f"Crate costs {crate['rubies']} Rubies")
    await db.purchases.insert_one({"_id": new_id("rb_"), "transaction_key": f"crate:{p['_id']}:{now().isoformat()}", "player_id": p["_id"], "kind": "ruby_spend", "item": key, "rubies": crate["rubies"], "grant": grant, "created_at": now()})
    return {"crate": key, "granted": grant, "rubies_spent": crate["rubies"]}


# ---- RevenueCat --------------------------------------------------------------------------------------------------
def _product_by_sku(sku: str) -> dict | None:
    return next((x for x in catalog()["store_products"] if x["sku"] == sku), None)


async def _grant_product(player_id: str, sku: str, transaction_key: str, store: str, expires_ms: int | None) -> dict:
    prod = _product_by_sku(sku)
    if not prod:
        raise fail(400, "unknown_product")
    p = await db.players.find_one({"_id": player_id})
    if not p:
        raise fail(404, "player_not_found")
    ops = Ops()
    result = {"sku": sku, "kind": prod["kind"]}
    if prod["kind"] == "consumable":
        resources_inc(ops, prod["grant"])
        result["granted"] = prod["grant"]
    elif prod["kind"] == "non_consumable":
        g = prod["grant"]
        soft = {k: int(v * g["soft_resource_hours_equivalent"]) for k, v in production_per_hour(p).items()}
        resources_inc(ops, {"rubies": g["rubies"], "forge_dust": g["forge_dust"], **soft})
        ops.add("cosmetics.owned", f"hero_cloak:{g['cosmetic_cloak']}")
        result["granted"] = {"rubies": g["rubies"], "forge_dust": g["forge_dust"], **soft, "cosmetic": g["cosmetic_cloak"]}
    else:
        ent = prod["entitlement"]
        if expires_ms:
            exp = aware(__import__("datetime").datetime.fromtimestamp(expires_ms / 1000, tz=__import__("datetime").timezone.utc))
        else:
            exp = week_start() + timedelta(days=7) if ent == "event_pass" else season_bounds()[1]
        await db.entitlements.update_one({"player_id": player_id, "entitlement": ent}, {"$set": {"expires_at": exp, "sku": sku, "store": store, "transaction_key": transaction_key, "updated_at": now(), "revoked": False}}, upsert=True)
        result["entitlement"] = {ent: exp.isoformat()}
    if ops.incs or ops.add_to_set:
        await ledger.apply_to_player(f"iap:{transaction_key}", player_id, "iap_credit", ops.build(), result)
    return result


async def record_and_credit(player_id: str, sku: str, transaction_id: str, store: str, source: str, expires_ms: int | None, raw: dict | None = None) -> dict:
    """Idempotent: purchase transaction id is unique across credit attempts."""
    key = f"{store}:{transaction_id}:{sku}"
    existing = await db.purchases.find_one({"transaction_key": key})
    if existing and existing.get("status") == "credited":
        return {"duplicate": True, "result": existing.get("result")}
    if not existing:
        await db.purchases.insert_one({"_id": new_id("pur_"), "transaction_key": key, "player_id": player_id, "sku": sku, "store": store, "transaction_id": transaction_id, "source": source, "status": "verified", "created_at": now(), "raw": raw})
    result = await _grant_product(player_id, sku, key, store, expires_ms)
    await db.purchases.update_one({"transaction_key": key}, {"$set": {"status": "credited", "credited_at": now(), "result": result}})
    await db.notifications.insert_one({"_id": new_id("n_"), "player_id": player_id, "kind": "purchase_credited", "title": "Purchase credited", "message": f"{sku} delivered to your treasury.", "created_at": now(), "read": False})
    return {"duplicate": False, "result": result}


async def refund(player_id: str, sku: str, transaction_id: str, store: str) -> dict:
    key = f"{store}:{transaction_id}:{sku}"
    pur = await db.purchases.find_one({"transaction_key": key})
    if not pur or pur.get("status") == "refunded":
        return {"refunded": False}
    prod = _product_by_sku(sku)
    if prod and prod["kind"] == "pass":
        await db.entitlements.update_one({"player_id": player_id, "entitlement": prod["entitlement"]}, {"$set": {"revoked": True, "expires_at": now(), "updated_at": now()}})
    elif prod and prod["kind"] == "consumable":
        amount = prod["grant"]["rubies"]
        p = await db.players.find_one({"_id": player_id}, {"resources.rubies": 1})
        deduct = min(amount, max(0, (p or {}).get("resources", {}).get("rubies", 0)))  # only unspent rubies are clawed back
        ops = Ops().inc("resources.rubies", -deduct)
        await ledger.apply_to_player(f"refund:{key}", player_id, "iap_refund", ops.build(), {"deducted": deduct})
    await db.purchases.update_one({"transaction_key": key}, {"$set": {"status": "refunded", "refunded_at": now()}})
    return {"refunded": True}


def _signature_ok(raw: bytes, header: str | None) -> bool:
    """RevenueCat HMAC signature (`t=<unix>,v1=<hex>` over `<t>.<body>`), enforced only when the signing secret is configured."""
    if not settings.RC_WEBHOOK_SIGNING_SECRET:
        return True
    if not header:
        return False
    parts = dict(x.split("=", 1) for x in header.split(",") if "=" in x)
    try:
        ts, supplied = parts["t"], parts["v1"]
        if abs(time.time() - int(ts)) > 300:
            return False
        expected = hmac.new(settings.RC_WEBHOOK_SIGNING_SECRET.encode(), (ts + ".").encode() + raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, supplied)
    except (KeyError, ValueError):
        return False


async def handle_webhook(raw: bytes, authorization: str | None, signature: str | None = None) -> dict:
    if not settings.RC_WEBHOOK_TOKEN or not hmac.compare_digest(authorization or "", f"Bearer {settings.RC_WEBHOOK_TOKEN}"):
        raise fail(401, "invalid_webhook_auth")
    if not _signature_ok(raw, signature):
        raise fail(401, "invalid_webhook_signature")
    payload = json.loads(raw)
    event = payload.get("event", payload)
    event_id = event.get("id")
    if not event_id:
        raise fail(400, "missing_event_id")
    try:
        await db.rc_events.insert_one({"_id": event_id, "event_id": event_id, "type": event.get("type"), "received_at": now(), "event": event})
    except Exception as exc:
        if "duplicate" in str(exc).lower():
            return {"ok": True, "duplicate": True}
        raise
    typ = event.get("type")
    pid = event.get("app_user_id")
    sku = event.get("product_id")
    store = (event.get("store") or "unknown").lower()
    tx = event.get("transaction_id") or event.get("original_transaction_id") or event_id
    if typ in ("INITIAL_PURCHASE", "NON_RENEWING_PURCHASE", "RENEWAL", "UNCANCELLATION", "REFUND_REVERSED") and pid and sku and _product_by_sku(sku):
        await record_and_credit(pid, sku, tx, store, "webhook", event.get("expiration_at_ms"), event)
    elif typ in ("CANCELLATION",) and event.get("cancel_reason") == "CUSTOMER_SUPPORT" and pid and sku:
        await refund(pid, sku, tx, store)
    elif typ in ("EXPIRATION",) and pid and sku and (_product_by_sku(sku) or {}).get("kind") == "pass":
        await db.entitlements.update_one({"player_id": pid, "entitlement": _product_by_sku(sku)["entitlement"]}, {"$set": {"expires_at": now(), "updated_at": now()}})
    await db.rc_events.update_one({"_id": event_id}, {"$set": {"processed_at": now()}})
    return {"ok": True}


async def sync_subscriber(player_id: str) -> dict:
    """Restore / verify: authoritative reconciliation against RevenueCat REST API (server-side, secret key)."""
    if not settings.RC_SECRET:
        raise fail(503, "store_verification_unavailable", "RevenueCat secret key not configured (owner deployment input)")
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{RC_API}/subscribers/{player_id}", headers={"Authorization": f"Bearer {settings.RC_SECRET}"})
    if r.status_code != 200:
        raise fail(502, "store_verification_failed")
    sub = r.json().get("subscriber", {})
    credited = []
    for sku, txs in (sub.get("non_subscriptions") or {}).items():
        for t in txs:
            if _product_by_sku(sku):
                res = await record_and_credit(player_id, sku, t.get("id"), (t.get("store") or "unknown").lower(), "restore", None, t)
                credited.append({"sku": sku, "transaction_id": t.get("id"), "duplicate": res["duplicate"]})
    for sku, s in (sub.get("subscriptions") or {}).items():
        if _product_by_sku(sku) and s.get("expires_date"):
            exp = aware(__import__("datetime").datetime.fromisoformat(s["expires_date"].replace("Z", "+00:00")))
            ent = _product_by_sku(sku)["entitlement"]
            await db.entitlements.update_one({"player_id": player_id, "entitlement": ent}, {"$set": {"expires_at": exp, "sku": sku, "updated_at": now(), "revoked": bool(s.get("refunded_at"))}}, upsert=True)
    return {"restored": credited, "entitlements": await entitlements_view(player_id)}


async def entitlements_view(player_id: str) -> dict:
    rows = await db.entitlements.find({"player_id": player_id}).to_list(10)
    return {r["entitlement"]: {"active": (not r.get("revoked")) and aware(r["expires_at"]) > now(), "expires_at": aware(r["expires_at"]).isoformat()} for r in rows}


async def purchase_history(player_id: str) -> list[dict]:
    return [clean(x) for x in await db.purchases.find({"player_id": player_id}, {"raw": 0}).sort("created_at", -1).limit(50).to_list(50)]
