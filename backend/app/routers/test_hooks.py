"""Test-only hooks. Mounted ONLY when TEST_HOOKS_ENABLED=true (never in production; config refuses it)."""
from datetime import timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..core import db
from ..core.security import Principal, current_user
from ..core.util import aware, now
from ..domain import scheduler

router = APIRouter(prefix="/_test", tags=["test-hooks"])


class GrantIn(BaseModel):
    resources: dict[str, int] | None = None
    highest_cleared: int | None = None
    castle_level: int | None = None
    hero_level: int | None = None
    units: dict[str, int] | None = None
    research: dict[str, int] | None = None
    email_verified: bool | None = None
    forge: dict[str, int] | None = None  # slot -> forge level (QA: exercise the v1.5 quest alternatives)
    buildings: dict[str, int] | None = None  # building key -> level (QA: seed the maxed end-game account)
    revoke_cosmetics: list[str] | None = None  # skin keys to un-own (QA: replay a purchase on the same account)


class ShiftIn(BaseModel):
    seconds: int
    include_resolved: bool = False  # war-shift only: also age resolved/cancelled wars (clears the 24h attack cooldown in QA)


@router.get("/last-code")
async def last_code(email: str, kind: str = "verify"):
    acc = await db.accounts.find_one({"email": email.strip().casefold()})
    if not acc:
        return {"code": None}
    doc = await db.one_time_codes.find_one({"account_id": acc["_id"], "kind": kind})
    return {"code": (doc or {}).get("test_plain")}


@router.post("/grant")
async def grant(body: GrantIn, p: Principal = Depends(current_user)):
    sets, incs = {}, {"version": 1}
    if body.resources:
        for k, v in body.resources.items():
            incs[f"resources.{k}"] = v
    if body.highest_cleared is not None:
        from ..domain import formulas as F
        sets["campaign.highest_cleared"] = body.highest_cleared
        sets["campaign.current_stage"] = body.highest_cleared + 1
        sets["campaign.active_attempt"] = None
        sets["domain.owned"] = F.domain_tiles_for_stage(body.highest_cleared)
    if body.castle_level is not None:
        sets["kingdom.castle_level"] = body.castle_level
        sets["kingdom.buildings.castle"] = body.castle_level
    if body.buildings:
        for k, v in body.buildings.items():
            sets[f"kingdom.buildings.{k}"] = v
            if k == "castle":
                sets["kingdom.castle_level"] = v
    if body.hero_level is not None:
        sets["hero.level"] = body.hero_level
        sets["hero.xp"] = 0
    if body.units:
        for k, v in body.units.items():
            sets[f"army.units.{k}"] = v
    if body.forge:
        for k, v in body.forge.items():
            sets[f"forge.{k}"] = v
    if body.research:
        cur = (await db.players.find_one({"_id": p.player_id}, {"research": 1}))["research"]
        sets["research"] = {**cur, **body.research}  # node keys contain dots: never use them as Mongo paths
    upd = {"$inc": incs}
    if body.revoke_cosmetics:
        cur = (await db.players.find_one({"_id": p.player_id}, {"cosmetics": 1}) or {}).get("cosmetics") or {}
        for kind in ("lord", "castle", "army"):
            if cur.get(f"{kind}_skin") in body.revoke_cosmetics:
                sets[f"cosmetics.{kind}_skin"] = None
        upd["$pull"] = {"cosmetics.owned": {"$in": body.revoke_cosmetics}}
        # the spend ledger is keyed per player+skin, so the row has to go too or the skin
        # can never be bought again on this account
        await db.purchases.delete_many({"transaction_key": {"$in": [f"skin:{p.player_id}:{k}" for k in body.revoke_cosmetics]}})
    if sets:
        upd["$set"] = sets
    await db.players.update_one({"_id": p.player_id}, upd)
    if body.email_verified is not None:
        await db.accounts.update_one({"_id": p.account_id}, {"$set": {"email_verified": body.email_verified}})
    return {"ok": True}


@router.post("/time-shift")
async def time_shift(body: ShiftIn, p: Principal = Depends(current_user)):
    """Moves this player's timers/attempts/deployments/runs into the past by N seconds (server-side; device clock is never used)."""
    d = timedelta(seconds=body.seconds)
    pl = await db.players.find_one({"_id": p.player_id})
    sets = {}
    for q in ("construction_queue", "recruit_queue", "research_queue"):
        items = pl["kingdom"].get(q, [])
        for i, it in enumerate(items):
            sets[f"kingdom.{q}.{i}.ends_at"] = aware(it["ends_at"]) - d
    if sets:
        sets["kingdom.queue_next_end"] = now() - timedelta(seconds=1)
        await db.players.update_one({"_id": p.player_id}, {"$set": sets})
    for coll in (db.battle_attempts, db.event_deployments, db.dungeon_runs):
        async for doc in coll.find({"player_id": p.player_id, "status": {"$in": ["pending", "running"]}}):
            await coll.update_one({"_id": doc["_id"]}, {"$set": {"ends_at" if "ends_at" in doc else "resolves_at": aware(doc.get("ends_at") or doc.get("resolves_at")) - d}})
    await db.players.update_one({"_id": p.player_id}, {"$set": {"last_seen_at": now() - d, "kingdom.last_production_at": now() - d}})
    await db.event_deployments.update_many({"player_id": p.player_id, "status": "running"}, {"$set": {"ends_at": now() - timedelta(seconds=1)}}) if body.seconds >= 3600 else None
    return {"shifted_seconds": body.seconds}


@router.post("/war-shift")
async def war_shift(body: ShiftIn, p: Principal = Depends(current_user)):
    d = timedelta(seconds=body.seconds)
    n = 0
    async for w in db.alliance_wars.find({"status": {"$in": ["prep", "locked"]}}):
        await db.alliance_wars.update_one({"_id": w["_id"]}, {"$set": {"lock_at": aware(w["lock_at"]) - d, "resolves_at": aware(w["resolves_at"]) - d, "declared_at": aware(w["declared_at"]) - d}})
        n += 1
    displaced = 0
    if body.include_resolved:
        async for w in db.alliance_wars.find({"status": {"$in": ["resolved", "cancelled"]}}):
            await db.alliance_wars.update_one({"_id": w["_id"]}, {"$set": {"declared_at": aware(w["declared_at"]) - d}})
            n += 1
        # An alliance that lost its home castle is barred from declaring for 12h. Ageing
        # that clock too is what lets QA restore a shard after a war suite has run.
        async for a in db.alliances.find({"displaced_until": {"$ne": None}}):
            await db.alliances.update_one({"_id": a["_id"]}, {"$set": {"displaced_until": aware(a["displaced_until"]) - d}})
            displaced += 1
    return {"wars_shifted": n, "alliances_unshifted_displacement": displaced}


@router.post("/tick")
async def tick(p: Principal = Depends(current_user)):
    return await scheduler.tick_once()
