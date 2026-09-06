"""Offline progression (I10): server-timestamp chest, 12h cap, idempotent single claim."""
from ..core import db, ledger
from ..core.canon import canon
from ..core.util import aware, clean, fail, new_id, now, rnd, seeded_rng
from . import formulas as F
from .gear import materialize_items, roll_rarity
from .hero import apply_xp
from .player import research_pct
from .progress import Ops, quest_progress, resources_inc

OFFLINE_CYCLES_PER_HOUR = 3600 / 120  # derived from battle.repeat_farm_cycle_seconds


def preview(p: dict) -> dict:
    off = p["offline"]
    o = canon()["offline"]
    hours = min(o["max_hours"], off.get("pending_hours", 0.0))
    hc = p["campaign"]["highest_cleared"]
    loot = {"xp": 0, "gold": 0, "soft": 0, "kills": 0, "gear_rolls": 0.0}
    if hc >= 1 and hours > 0:
        rep = F.repeat_rewards(hc)
        eff = o["battle_loot_efficiency"] * (1 + research_pct(p["research"], "offline_loot_pct") / 100)
        cycles = OFFLINE_CYCLES_PER_HOUR * hours
        loot = {
            "xp": rnd(rep["xp"] * cycles * eff), "gold": rnd(rep["gold"] * cycles * eff), "soft": rnd(rep["soft"] * cycles * eff),
            "kills": rnd(F.monsters_per_wave(hc) * canon()["battle"]["waves_per_stage"] * cycles),
            "gear_rolls": round(F.offline_gear_rolls_per_hour(hc) * o["gear_roll_efficiency"] * hours, 3),
        }
    return {
        "hours": round(hours, 3), "max_hours": o["max_hours"], "chest_from": clean({"t": off.get("chest_from")})["t"], "full": hours >= o["max_hours"],
        "production": off.get("pending_production", {}), "battle_loot": loot, "completed_timers": [clean(t) for t in off.get("pending_timers", [])],
        "claimable": hours > 0 or bool(off.get("pending_timers")) or any(v > 0 for v in off.get("pending_production", {}).values()),
    }


async def claim(p: dict) -> dict:
    pv = preview(p)
    if not pv["claimable"]:
        raise fail(400, "nothing_to_claim")
    chest_from = aware(p["offline"].get("chest_from")) or now()
    key = f"offline:{p['_id']}:{chest_from.isoformat()}"
    rng = seeded_rng(key)
    ops = Ops()
    loot = pv["battle_loot"]
    level, xp, gained = apply_xp(p["hero"]["level"], p["hero"]["xp"], loot["xp"])
    ops.set("hero.level", level).set("hero.xp", xp)
    resources_inc(ops, {"gold": loot["gold"], **F.split_soft(loot["soft"]), **{k: int(v) for k, v in pv["production"].items()}})
    ops.inc("stats.kills", loot["kills"]).inc("stats.offline_hours", pv["hours"])
    rolls = int(loot["gear_rolls"]) + (1 if rng.random() < loot["gear_rolls"] - int(loot["gear_rolls"]) else 0)
    hc = p["campaign"]["highest_cleared"]
    gear = None
    if rolls and hc >= 1:
        gear = await materialize_items(p, key, [(roll_rarity(hc, rng), hc, "offline") for _ in range(rolls)], rng, ops)
    quest_progress(ops, p, "claim_offline", None, 1)
    if pv["hours"] > 0:
        quest_progress(ops, p, None, "collect_offline_hours", pv["hours"])
    ops.set("offline", {"chest_from": None, "pending_hours": 0.0, "pending_production": {}, "pending_timers": []})
    result = {"claimed": True, "hours": pv["hours"], "xp": loot["xp"], "levels_gained": gained, "gold": loot["gold"], "soft": F.split_soft(loot["soft"]),
              "production": pv["production"], "kills": loot["kills"], "gear": gear, "completed_timers": pv["completed_timers"], "interval": {"from": chest_from.isoformat(), "to": now().isoformat()}}
    res, applied = await ledger.apply_to_player(key, p["_id"], "offline_claim", ops.build(), result, extra_filter={"offline.chest_from": p["offline"].get("chest_from")})
    if applied:
        await db.offline_claims.insert_one({"_id": new_id("oc_"), "player_id": p["_id"], "key": key, "interval_start": chest_from, "interval_end": now(), "hours": pv["hours"], "result": result, "created_at": now()})
    return res
