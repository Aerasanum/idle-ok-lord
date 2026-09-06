"""Gear: canonical drop rolls, item generation, equip/auto-equip, salvage/auto-salvage, forge, reforge (I05)."""
import random

from pymongo.errors import DuplicateKeyError

from ..core import db
from ..core.canon import canon
from ..core.util import fail, new_id, now, rnd
from . import formulas as F
from .progress import Ops, resources_inc

RARITY_ORDER = None


def order() -> list:
    return canon()["gear"]["rarity_order"]


def ridx(r: str) -> int:
    return order().index(r)


def roll_rarity(stage: int, rng: random.Random, min_rarity: str | None = None, rolls: int = 1) -> str:
    weights = F.unlocked_drop_weights(stage)
    keys = list(weights)
    best = None
    for _ in range(max(1, rolls)):
        x = rng.random()
        acc = 0.0
        pick = keys[-1]
        for k in keys:
            acc += weights[k]
            if x <= acc:
                pick = k
                break
        if best is None or ridx(pick) > ridx(best):
            best = pick
    if min_rarity and ridx(best) < ridx(min_rarity):
        best = min_rarity
    return best


def roll_slot(rng: random.Random) -> str:
    w = canon()["gear"]["slot_drop_weights_pct"]
    x = rng.random() * sum(w.values())
    acc = 0.0
    for k, v in w.items():
        acc += v
        if x <= acc:
            return k
    return list(w)[-1]


def roll_affixes(rarity: str, item_level: int, rng: random.Random) -> list[dict]:
    g = canon()["gear"]
    n = F.rarity_rule(rarity)["affix_count"]
    pool = list(g["affix_pool"])
    rng.shuffle(pool)
    lo, hi = g["affix_values"]["roll_scalar_range"]
    return [{"key": k, "value": F.affix_value(k, item_level, rarity, rng.uniform(lo, hi))} for k in pool[:n]]


def item_score(item: dict, forge_level: int = 0) -> int:
    fm = F.forge_multiplier(forge_level)
    s = item["stats"]
    return rnd((s.get("attack", 0) * 2 + s.get("defense", 0) * 1.5 + s.get("hp", 0) * 0.15) * fm)


def make_item(item_id: str, owner_id: str, source_stage: int, rarity: str, rng: random.Random, source: str, slot: str | None = None) -> dict:
    il = F.item_level_for_stage(source_stage)
    slot = slot or roll_slot(rng)
    stats = F.item_base_stats(slot, il, rarity)
    item = {
        "_id": item_id, "owner_id": owner_id, "slot": slot, "rarity": rarity, "item_level": il, "stats": stats,
        "affixes": roll_affixes(rarity, il, rng), "source": source, "source_stage": source_stage, "created_at": now(),
    }
    item["score"] = item_score(item)
    return item


def stage_drop_plan(stage: int, kind: str, first_clear: bool, gear_find_pct: float, rng: random.Random) -> list[str]:
    """Rarities of items dropped by a stage clear. Repeat farming halves normal chance and boss guarantee."""
    gd = canon()["battle"]["gear_drop"]
    mult = 1.0 if first_clear else gd["repeat_drop_rate_multiplier"]
    find = 1 + gear_find_pct / 100
    out = []
    if kind == "boss":
        min_r = gd["milestone_boss_minimum_rarity"].get(str(stage)) if first_clear else None
        guaranteed = gd["boss_guaranteed_items"] if first_clear else 0
        if not first_clear and rng.random() < gd["repeat_drop_rate_multiplier"]:
            guaranteed = gd["boss_guaranteed_items"]
        for _ in range(guaranteed):
            out.append(roll_rarity(stage, rng, min_r))
        if rng.random() * 100 < gd["boss_extra_item_roll_pct"] * mult * find:
            out.append(roll_rarity(stage, rng))
    else:
        pct = gd["elite_stage_clear_roll_pct"] if kind == "elite" else gd["normal_stage_clear_roll_pct"]
        if rng.random() * 100 < pct * mult * find:
            out.append(roll_rarity(stage, rng))
    return out


# ---- inventory application (auto-equip / auto-salvage) -----------------------------------------------------
async def owned_count(owner_id: str) -> int:
    return await db.gear_items.count_documents({"owner_id": owner_id})


def should_auto_salvage(p: dict, item: dict, equipped_in_slot: dict | None) -> bool:
    if p["campaign"]["highest_cleared"] < canon()["gear"]["inventory"]["auto_salvage_unlock_stage"]:
        return False
    a = p.get("auto_salvage") or {}
    if not a.get("enabled"):
        return False
    if ridx(item["rarity"]) <= ridx(a.get("max_rarity", "common")):
        return True
    if a.get("below_equipped") and equipped_in_slot and item["item_level"] < equipped_in_slot["item_level"]:
        return True
    if item["slot"] in (a.get("slots") or []):
        return True
    return False


async def materialize_items(p: dict, key: str, plan: list[tuple[str, int, str]], rng: random.Random, ops: Ops) -> dict:
    """Create items deterministically under ledger `key`; apply auto-equip, auto-salvage, capacity. Returns summary."""
    equipped = {}
    ids = [v for v in p["equipped"].values() if v]
    if ids:
        for it in await db.gear_items.find({"_id": {"$in": ids}}).to_list(20):
            equipped[it["slot"]] = it
    count = await owned_count(p["_id"])
    cap = p.get("inventory_capacity", 150)
    summary = {"found": [], "equipped": [], "salvaged": [], "materials": {}, "inventory_full": False}
    new_equipped = dict(p["equipped"])
    for i, (rarity, stage, source) in enumerate(plan):
        item_id = f"{key}:g{i}"
        item = make_item(item_id, p["_id"], stage, rarity, rng, source)
        summary["found"].append({"id": item_id, "slot": item["slot"], "rarity": rarity, "item_level": item["item_level"], "score": item["score"]})
        if ridx(rarity) >= ridx("legendary"):
            ops.inc("stats.legendary_or_higher_items_found", 1)
        ops.inc("stats.items_found", 1)
        ops.add("codex.gear_rarities", rarity)
        cur = equipped.get(item["slot"])
        better = cur is None or item["score"] > item_score(cur)
        salvage = False
        if better:
            new_equipped[item["slot"]] = item_id
            equipped[item["slot"]] = item
            summary["equipped"].append(item_id)
        elif should_auto_salvage(p, item, cur) or count >= cap:
            salvage = True
            if count >= cap:
                summary["inventory_full"] = True
        if salvage:
            y = F.salvage_yield(rarity, item["item_level"], rng)
            for k, v in y.items():
                summary["materials"][k] = summary["materials"].get(k, 0) + v
            summary["salvaged"].append({"id": item_id, "rarity": rarity, "yield": y})
            continue
        try:
            await db.gear_items.insert_one(item)
            count += 1 if not better else 0
        except DuplicateKeyError:
            pass
    resources_inc(ops, summary["materials"])
    for slot, iid in new_equipped.items():
        if iid != p["equipped"].get(slot):
            ops.set(f"equipped.{slot}", iid)
    return summary


# ---- player actions -----------------------------------------------------------------------------------------
async def list_inventory(p: dict) -> list[dict]:
    items = await db.gear_items.find({"owner_id": p["_id"]}).sort("created_at", -1).to_list(400)
    eq = {v: k for k, v in p["equipped"].items() if v}
    for it in items:
        it["equipped_slot"] = eq.get(it["_id"])
        it["score_forged"] = item_score(it, p["forge"].get(it["slot"], 0))
    return items


async def equip(p: dict, item_id: str) -> dict:
    it = await db.gear_items.find_one({"_id": item_id, "owner_id": p["_id"]})
    if not it:
        raise fail(404, "item_not_found")
    res = await db.players.update_one({"_id": p["_id"], "version": p["version"]}, {"$set": {f"equipped.{it['slot']}": item_id, "updated_at": now()}, "$inc": {"version": 1}})
    if res.matched_count == 0:
        raise fail(409, "state_changed")
    return {"equipped": {it["slot"]: item_id}}


async def unequip(p: dict, slot: str) -> dict:
    if slot not in canon()["gear"]["slots"]:
        raise fail(400, "bad_slot")
    await db.players.update_one({"_id": p["_id"]}, {"$set": {f"equipped.{slot}": None, "updated_at": now()}, "$inc": {"version": 1}})
    return {"equipped": {slot: None}}


async def auto_equip(p: dict) -> dict:
    items = await list_inventory(p)
    best = {}
    for it in items:
        if it["slot"] not in best or it["score"] > best[it["slot"]]["score"]:
            best[it["slot"]] = it
    sets = {f"equipped.{s}": it["_id"] for s, it in best.items() if p["equipped"].get(s) != it["_id"]}
    if sets:
        sets["updated_at"] = now()
        await db.players.update_one({"_id": p["_id"]}, {"$set": sets, "$inc": {"version": 1}})
    return {"changed": len([k for k in sets if k.startswith("equipped.")])}


async def salvage(p: dict, item_ids: list[str]) -> dict:
    ids = [i for i in item_ids if i not in p["equipped"].values()]
    if not ids:
        raise fail(400, "nothing_to_salvage", "Equipped items cannot be salvaged")
    items = await db.gear_items.find({"_id": {"$in": ids}, "owner_id": p["_id"]}).to_list(400)
    rng = random.SystemRandom()
    total = {}
    done = []
    for it in items:
        res = await db.gear_items.delete_one({"_id": it["_id"], "owner_id": p["_id"]})
        if res.deleted_count:
            y = F.salvage_yield(it["rarity"], it["item_level"], rng)
            for k, v in y.items():
                total[k] = total.get(k, 0) + v
            done.append(it["_id"])
    if total:
        ops = Ops()
        resources_inc(ops, total)
        ops.inc("version", 1).set("updated_at", now())
        await db.players.update_one({"_id": p["_id"]}, ops.build())
    return {"salvaged": done, "materials": total}


async def forge_upgrade(p: dict, slot: str) -> dict:
    g = canon()["gear"]["forge"]
    if slot not in canon()["gear"]["slots"]:
        raise fail(400, "bad_slot")
    level = p["forge"].get(slot, 0)
    if level >= g["max_level_per_slot"]:
        raise fail(400, "forge_max", "Slot already at +20")
    iid = p["equipped"].get(slot)
    if not iid:
        raise fail(400, "slot_empty", "Equip an item in this slot to forge it")
    it = await db.gear_items.find_one({"_id": iid, "owner_id": p["_id"]})
    if not it:
        raise fail(404, "item_not_found")
    cost = F.forge_next_cost(it["item_level"], level)
    ops = Ops()
    ops.inc("resources.gold", -cost["gold"]).inc("resources.forge_dust", -cost["forge_dust"]).inc(f"forge.{slot}", 1)
    ops.inc("stats.forge_upgrades", 1).inc("version", 1).set("updated_at", now())
    from .progress import quest_progress
    quest_progress(ops, p, "forge_upgrade", "forge_upgrades")
    res = await db.players.update_one(
        {"_id": p["_id"], f"forge.{slot}": level, "resources.gold": {"$gte": cost["gold"]}, "resources.forge_dust": {"$gte": cost["forge_dust"]}},
        ops.build(),
    )
    if res.matched_count == 0:
        raise fail(409, "insufficient_or_changed", "Not enough Gold/Forge Dust")
    return {"slot": slot, "forge_level": level + 1, "cost": cost, "next_cost": F.forge_next_cost(it["item_level"], level + 1) if level + 1 < g["max_level_per_slot"] else None}


async def reforge(p: dict, item_id: str, affix_index: int) -> dict:
    it = await db.gear_items.find_one({"_id": item_id, "owner_id": p["_id"]})
    if not it:
        raise fail(404, "item_not_found")
    if affix_index < 0 or affix_index >= len(it.get("affixes", [])):
        raise fail(400, "bad_affix")
    cost = F.reforge_cost(it["item_level"], it["rarity"])
    rng = random.SystemRandom()
    others = {a["key"] for i, a in enumerate(it["affixes"]) if i != affix_index}
    pool = [k for k in canon()["gear"]["affix_pool"] if k not in others]
    key = rng.choice(pool)
    lo, hi = canon()["gear"]["affix_values"]["roll_scalar_range"]
    new_affix = {"key": key, "value": F.affix_value(key, it["item_level"], it["rarity"], rng.uniform(lo, hi))}
    res = await db.players.update_one(
        {"_id": p["_id"], "resources.gold": {"$gte": cost["gold"]}, "resources.reforge_stone": {"$gte": cost["reforge_stone"]}},
        {"$inc": {"resources.gold": -cost["gold"], "resources.reforge_stone": -cost["reforge_stone"], "version": 1}, "$set": {"updated_at": now()}},
    )
    if res.matched_count == 0:
        raise fail(409, "insufficient", "Not enough Gold/Reforge Stones")
    affixes = list(it["affixes"])
    affixes[affix_index] = new_affix
    await db.gear_items.update_one({"_id": item_id}, {"$set": {"affixes": affixes, "reforged_at": now()}})
    return {"item_id": item_id, "affixes": affixes, "cost": cost}


async def expand_inventory(p: dict) -> dict:
    inv = canon()["gear"]["inventory"]
    cur = p.get("inventory_capacity", inv["base_slots"])
    nxt = next((e for e in inv["expansions"] if e["to_slots"] > cur), None)
    if not nxt or cur >= inv["hard_cap_slots"]:
        raise fail(400, "inventory_max")
    flt = {"_id": p["_id"], "inventory_capacity": cur}
    inc = {"version": 1}
    for k, v in nxt["cost"].items():
        flt[f"resources.{k}"] = {"$gte": v}
        inc[f"resources.{k}"] = -v
    res = await db.players.update_one(flt, {"$inc": inc, "$set": {"inventory_capacity": nxt["to_slots"], "updated_at": now()}})
    if res.matched_count == 0:
        raise fail(409, "insufficient")
    return {"inventory_capacity": nxt["to_slots"], "cost": nxt["cost"]}


async def set_auto_salvage(p: dict, cfg: dict) -> dict:
    if p["campaign"]["highest_cleared"] < canon()["gear"]["inventory"]["auto_salvage_unlock_stage"]:
        raise fail(403, "auto_salvage_locked", "Auto Salvage unlocks at stage 20")
    if cfg.get("max_rarity") not in order():
        raise fail(400, "bad_rarity")
    a = {"enabled": bool(cfg.get("enabled")), "max_rarity": cfg["max_rarity"], "below_equipped": bool(cfg.get("below_equipped")), "slots": [s for s in cfg.get("slots", []) if s in canon()["gear"]["slots"]]}
    await db.players.update_one({"_id": p["_id"]}, {"$set": {"auto_salvage": a, "updated_at": now()}, "$inc": {"version": 1}})
    return a
