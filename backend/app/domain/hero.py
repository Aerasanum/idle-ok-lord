"""Hero XP/levels, skills and talents (I04)."""
from ..core import db
from ..core.canon import canon
from ..core.util import fail, now
from . import formulas as F


def apply_xp(level: int, xp: int, gain: int) -> tuple[int, int, int]:
    """Returns (new_level, new_xp, levels_gained). XP is the only level gate."""
    mx = canon()["hero"]["max_level"]
    xp += int(gain)
    gained = 0
    while level < mx and xp >= F.xp_to_next(level):
        xp -= F.xp_to_next(level)
        level += 1
        gained += 1
    if level >= mx:
        xp = min(xp, F.xp_to_next(mx))
    return level, xp, gained


def unlocked_skills(level: int) -> list[dict]:
    return [s for s in canon()["hero"]["auto_skills"] if s["unlock_level"] <= level]


def unlocked_slot_count(level: int) -> int:
    return sum(1 for l in canon()["hero"]["skill_slot_unlock_levels"] if level >= l)


async def set_skill_slots(p: dict, slots: list) -> dict:
    lvl = p["hero"]["level"]
    n = unlocked_slot_count(lvl)
    if len(slots) != 3:
        raise fail(400, "bad_slots", "Exactly 3 slots")
    keys = {s["key"]: s for s in unlocked_skills(lvl)}
    out = []
    seen = set()
    for i, k in enumerate(slots):
        if k is None:
            out.append(None)
            continue
        if i >= n:
            raise fail(403, "slot_locked", f"Skill slot {i + 1} unlocks at level {canon()['hero']['skill_slot_unlock_levels'][i]}")
        if k not in keys or k in seen:
            raise fail(400, "bad_skill")
        seen.add(k)
        out.append(k)
    await db.players.update_one({"_id": p["_id"]}, {"$set": {"hero.skill_slots": out, "updated_at": now()}, "$inc": {"version": 1}})
    return {"skill_slots": out}


async def allocate_talent(p: dict, branch: str) -> dict:
    br = canon()["hero"]["talents"]["branches"]
    if branch not in br:
        raise fail(400, "bad_branch")
    t = p["hero"]["talents"]
    total = F.talent_points_for_level(p["hero"]["level"])
    if sum(t.values()) >= total:
        raise fail(403, "no_points", "No talent points available")
    if t.get(branch, 0) >= br[branch]["max_ranks"]:
        raise fail(400, "branch_max")
    res = await db.players.update_one(
        {"_id": p["_id"], f"hero.talents.{branch}": t.get(branch, 0), "version": p["version"]},
        {"$inc": {f"hero.talents.{branch}": 1, "version": 1}, "$set": {"updated_at": now()}},
    )
    if res.matched_count == 0:
        raise fail(409, "state_changed")
    t2 = dict(t)
    t2[branch] = t.get(branch, 0) + 1
    return {"talents": t2, "points_total": total, "points_spent": sum(t2.values())}


async def respec(p: dict) -> dict:
    cost = canon()["hero"]["talents"]["respec_rubies"]
    res = await db.players.update_one(
        {"_id": p["_id"], "resources.rubies": {"$gte": cost}},
        {"$inc": {"resources.rubies": -cost, "version": 1}, "$set": {"hero.talents": {"warrior": 0, "guardian": 0, "commander": 0, "fortune": 0}, "updated_at": now()}},
    )
    if res.matched_count == 0:
        raise fail(409, "insufficient_rubies", f"Respec costs {cost} Rubies")
    return {"talents": {"warrior": 0, "guardian": 0, "commander": 0, "fortune": 0}, "rubies_spent": cost}
