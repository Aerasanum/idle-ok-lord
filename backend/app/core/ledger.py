"""Idempotency ledger. A unique key is reserved BEFORE side effects; the player-state update carries the
key in `recent_ledger_keys` with a `$ne` guard so a crash between update and ledger commit cannot double-apply."""
from typing import Any

from pymongo.errors import DuplicateKeyError

from . import db
from .util import fail, now

RECENT_KEYS_KEEP = 600


async def reserve(key: str, player_id: str, kind: str, payload: dict | None = None) -> dict:
    doc = {
        "_id": key,
        "key": key,
        "player_id": player_id,
        "kind": kind,
        "status": "reserved",
        "payload": payload or {},
        "result": None,
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        await db.ledgers.insert_one(doc)
        return doc
    except DuplicateKeyError:
        existing = await db.ledgers.find_one({"_id": key})
        return existing


async def commit(key: str, result: Any) -> None:
    await db.ledgers.update_one({"_id": key}, {"$set": {"status": "applied", "result": result, "updated_at": now()}})


async def mark_failed(key: str, reason: str) -> None:
    await db.ledgers.update_one({"_id": key}, {"$set": {"status": "failed", "result": {"reason": reason}, "updated_at": now()}})


async def apply_to_player(
    key: str,
    player_id: str,
    kind: str,
    update: dict,
    result: Any,
    extra_filter: dict | None = None,
    payload: dict | None = None,
) -> tuple[Any, bool]:
    """Apply `update` to the player exactly once under `key`. Returns (result, applied_now)."""
    led = await reserve(key, player_id, kind, payload)
    if led["status"] == "applied":
        return led["result"], False
    if led["status"] == "failed":
        # a previous attempt failed its guard; allow re-evaluation
        await db.ledgers.update_one({"_id": key}, {"$set": {"status": "reserved", "updated_at": now()}})
    flt = {"_id": player_id, "recent_ledger_keys": {"$ne": key}}
    if extra_filter:
        flt.update(extra_filter)
    upd = dict(update)
    push = upd.setdefault("$push", {})
    push["recent_ledger_keys"] = {"$each": [key], "$slice": -RECENT_KEYS_KEEP}
    upd.setdefault("$inc", {})["version"] = 1
    upd.setdefault("$set", {})["updated_at"] = now()
    res = await db.players.update_one(flt, upd)
    if res.matched_count == 0:
        p = await db.players.find_one({"_id": player_id}, {"recent_ledger_keys": 1})
        if p and key in (p.get("recent_ledger_keys") or []):
            await commit(key, result)
            return result, True
        await mark_failed(key, "guard_failed")
        raise fail(409, "guard_failed", "State changed or insufficient resources")
    await commit(key, result)
    return result, True
