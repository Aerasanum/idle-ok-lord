"""Kingdom buildings, production, construction queues and timers (I06); research (I07a); army recruitment/formation (I07b)."""
from datetime import timedelta

from ..core import db
from ..core.canon import buildings_by_key, canon, research_by_key, support_formation_slots, units_by_key
from ..core.util import aware, ceil, fail, new_id, now, rnd
from . import formulas as F
from .player import research_pct
from .progress import Ops, alt_quest_progress, quest_progress


def _cost_filter(flt: dict, inc: dict, cost: dict):
    for k, v in cost.items():
        if v:
            flt[f"resources.{k}"] = {"$gte": v}
            inc[f"resources.{k}"] = -v


def _queue_next_end(p: dict, extra_end) -> object:
    ends = [aware(i["ends_at"]) for q in ("construction_queue", "recruit_queue", "research_queue") for i in p["kingdom"].get(q, [])]
    ends.append(extra_end)
    return min(ends)


def building_view(p: dict) -> list[dict]:
    out = []
    cr = research_pct(p["research"], "construction_cost_reduction_pct")
    cs = research_pct(p["research"], "construction_speed_pct")
    castle_speed = research_pct(p["research"], "castle_upgrade_speed_pct")
    in_queue = {i["building"]: i for i in p["kingdom"].get("construction_queue", [])}
    for b in canon()["buildings"]:
        lvl = p["kingdom"]["buildings"].get(b["key"], 0)
        unlocked = p["kingdom"]["castle_level"] >= b["unlock_castle_level"]
        nxt = None
        if lvl < b["max_level"]:
            row = b["levels"][lvl]  # level lvl+1 row
            cost = {k: rnd(v * (1 - cr / 100)) for k, v in row["upgrade_cost"].items()}
            speed = cs + (castle_speed if b["key"] == "castle" else 0)
            minutes = row["upgrade_time_minutes"] * (1 - speed / 100)
            nxt = {"level": lvl + 1, "cost": cost, "minutes": round(minutes, 2), "production_per_hour": row.get("production_per_hour"), "capacity_each_resource": row.get("capacity_each_resource")}
        cur = b["levels"][lvl - 1] if lvl else None
        out.append({"key": b["key"], "name": b["name"], "level": lvl, "max_level": b["max_level"], "unlock_castle_level": b["unlock_castle_level"], "unlocked": unlocked,
                    "current": {"production_per_hour": cur.get("production_per_hour"), "capacity_each_resource": cur.get("capacity_each_resource")} if cur else None,
                    "next": nxt, "in_queue": in_queue.get(b["key"])})
    return out


async def upgrade_building(p: dict, key: str) -> dict:
    b = buildings_by_key().get(key)
    if not b:
        raise fail(404, "building_not_found")
    k = p["kingdom"]
    if k["castle_level"] < b["unlock_castle_level"]:
        raise fail(403, "castle_gate", f"Requires Castle {b['unlock_castle_level']}")
    lvl = k["buildings"].get(key, 0)
    if lvl >= b["max_level"]:
        raise fail(400, "max_level")
    if any(i["building"] == key for i in k.get("construction_queue", [])):
        raise fail(409, "already_queued")
    q = canon()["kingdom"]["construction_queues"]
    cap = q["max"] if k["castle_level"] >= q["second_unlock_castle_level"] else q["start"]
    if len(k.get("construction_queue", [])) >= cap:
        raise fail(409, "queue_full", f"Construction queue full ({cap})")
    row = b["levels"][lvl]
    cr = research_pct(p["research"], "construction_cost_reduction_pct")
    speed = research_pct(p["research"], "construction_speed_pct") + (research_pct(p["research"], "castle_upgrade_speed_pct") if key == "castle" else 0)
    cost = {kk: rnd(v * (1 - cr / 100)) for kk, v in row["upgrade_cost"].items()}
    minutes = row["upgrade_time_minutes"] * (1 - speed / 100)
    flt = {"_id": p["_id"], "version": p["version"]}
    inc = {"version": 1}
    _cost_filter(flt, inc, cost)
    alt_ops = alt_quest_progress(Ops(), p, "all_research_at_max")  # v1.5: a building upgrade counts as the research task when research is maxed
    if minutes <= 0:
        sets = {f"kingdom.buildings.{key}": lvl + 1, "updated_at": now()}
        if key == "castle":
            sets["kingdom.castle_level"] = lvl + 1
        upd = alt_ops.build()
        upd.setdefault("$inc", {}).update(inc)
        upd.setdefault("$set", {}).update(sets)
        res = await db.players.update_one(flt, upd)
        if res.matched_count == 0:
            raise fail(409, "insufficient", "Not enough resources")
        return {"building": key, "level": lvl + 1, "instant": True, "cost": cost}
    ends = now() + timedelta(minutes=minutes)
    item = {"id": new_id("q_"), "building": key, "target_level": lvl + 1, "started_at": now(), "ends_at": ends}
    upd = alt_ops.build()
    upd.setdefault("$inc", {}).update(inc)
    upd["$push"] = {"kingdom.construction_queue": item}
    upd.setdefault("$set", {}).update({"kingdom.queue_next_end": _queue_next_end(p, ends), "updated_at": now()})
    res = await db.players.update_one(flt, upd)
    if res.matched_count == 0:
        raise fail(409, "insufficient", "Not enough resources")
    return {"building": key, "queued": item, "cost": cost}


async def speedup(p: dict, queue: str, item_id: str) -> dict:
    if queue not in ("construction_queue", "recruit_queue", "research_queue"):
        raise fail(400, "bad_queue")
    items = p["kingdom"].get(queue, [])
    idx = next((i for i, it in enumerate(items) if it["id"] == item_id), None)
    if idx is None:
        raise fail(404, "queue_item_not_found")
    remaining_min = max(0.0, (aware(items[idx]["ends_at"]) - now()).total_seconds() / 60)
    cost = F.speedup_rubies(remaining_min)
    res = await db.players.update_one(
        {"_id": p["_id"], "version": p["version"], "resources.rubies": {"$gte": cost}},
        {"$inc": {"resources.rubies": -cost, "version": 1}, "$set": {f"kingdom.{queue}.{idx}.ends_at": now() - timedelta(seconds=1), "kingdom.queue_next_end": now(), "updated_at": now()}},
    )
    if res.matched_count == 0:
        raise fail(409, "insufficient_rubies", f"Speedup costs {cost} Rubies")
    return {"rubies_spent": cost, "queue": queue, "item_id": item_id}


# ---- research --------------------------------------------------------------------------------------------
def research_view(p: dict) -> list[dict]:
    out = []
    queued = {i["node"]: i for i in p["kingdom"].get("research_queue", [])}
    for n in canon()["research"]["nodes"]:
        lvl = p["research"].get(n["key"], 0)
        nxt = n["levels"][lvl] if lvl < n["max_level"] else None
        out.append({"key": n["key"], "name": n["name"], "branch": n["branch"], "effect_key": n["effect_key"], "effect_per_level_pct": n["effect_per_level_pct"],
                    "level": lvl, "max_level": n["max_level"], "unlock_castle_level": n["unlock_castle_level"], "unlocked": p["kingdom"]["castle_level"] >= n["unlock_castle_level"],
                    "effect_total_pct": n["effect_per_level_pct"] * lvl, "next": nxt, "in_queue": queued.get(n["key"])})
    return out


async def start_research(p: dict, key: str) -> dict:
    n = research_by_key().get(key)
    if not n:
        raise fail(404, "node_not_found")
    if p["kingdom"]["castle_level"] < n["unlock_castle_level"]:
        raise fail(403, "castle_gate", f"Requires Castle {n['unlock_castle_level']}")
    lvl = p["research"].get(key, 0)
    if lvl >= n["max_level"]:
        raise fail(400, "max_level")
    if len(p["kingdom"].get("research_queue", [])) >= canon()["kingdom"]["research_queues"]:
        raise fail(409, "queue_full", "Research queue is busy")
    row = n["levels"][lvl]
    flt = {"_id": p["_id"], "version": p["version"]}
    inc = {"version": 1}
    _cost_filter(flt, inc, row["cost"])
    ends = now() + timedelta(minutes=row["time_minutes"])
    item = {"id": new_id("q_"), "node": key, "target_level": lvl + 1, "started_at": now(), "ends_at": ends}
    ops = Ops()
    quest_progress(ops, p, "start_or_finish_research")
    upd = ops.build()
    upd.setdefault("$inc", {}).update(inc)
    upd["$push"] = {"kingdom.research_queue": item}
    upd.setdefault("$set", {}).update({"kingdom.queue_next_end": _queue_next_end(p, ends), "updated_at": now()})
    res = await db.players.update_one(flt, upd)
    if res.matched_count == 0:
        raise fail(409, "insufficient", "Not enough resources")
    return {"node": key, "queued": item, "cost": row["cost"]}


# ---- army -------------------------------------------------------------------------------------------------
def unit_gates(p: dict, u: dict) -> dict:
    req = u.get("required_research")
    return {
        "castle": p["kingdom"]["castle_level"] >= u["unlock_castle_level"],
        "research": (not req) or p["research"].get(req, 0) >= 1,
        "campaign": p["campaign"]["highest_cleared"] >= u["unlock_campaign_stage"],
    }


def army_view(p: dict) -> list[dict]:
    out = []
    speed = research_pct(p["research"], "beast_recruit_speed_pct")
    research = research_by_key()
    for u in canon()["units"]["catalog"]:
        g = unit_gates(p, u)
        minutes = u["recruit_time_minutes_each"] * (1 - (speed if u["category"] == "beast" else 0) / 100)
        req = u.get("required_research")
        out.append({**{k: u[k] for k in ("key", "name", "category", "role", "base_power", "command_cost", "attack", "defense", "hp", "recruit_cost", "unlock_campaign_stage", "unlock_castle_level", "required_research")},
                    "effective_unlock_castle_level": u.get("effective_unlock_castle_level", u["unlock_castle_level"]),
                    "required_research_name": research[req]["name"] if req and req in research else None,
                    "required_research_castle_level": research[req]["unlock_castle_level"] if req and req in research else None,
                    "recruit_minutes_each": round(minutes, 3), "owned": p["army"]["units"].get(u["key"], 0), "deployed": p["army"]["formation"].get(u["key"], 0), "gates": g, "unlocked": all(g.values())})
    return out


async def recruit(p: dict, unit: str, quantity: int) -> dict:
    u = units_by_key().get(unit)
    if not u:
        raise fail(404, "unit_not_found")
    if quantity < 1 or quantity > 5000:
        raise fail(400, "bad_quantity")
    g = unit_gates(p, u)
    if not all(g.values()):
        raise fail(403, "unit_locked", f"Gates not met: {[k for k, v in g.items() if not v]}")
    q = canon()["kingdom"]["recruit_queues"]
    cap = q["max"] if p["kingdom"]["castle_level"] >= q["second_unlock_castle_level"] else q["start"]
    if len(p["kingdom"].get("recruit_queue", [])) >= cap:
        raise fail(409, "queue_full", f"Recruit queue full ({cap})")
    cost = {k: v * quantity for k, v in u["recruit_cost"].items()}
    speed = research_pct(p["research"], "beast_recruit_speed_pct") if u["category"] == "beast" else 0
    minutes = u["recruit_time_minutes_each"] * quantity * (1 - speed / 100)
    flt = {"_id": p["_id"], "version": p["version"]}
    inc = {"version": 1, "stats.units_recruited_total": quantity}
    _cost_filter(flt, inc, cost)
    ends = now() + timedelta(minutes=minutes)
    item = {"id": new_id("q_"), "unit": unit, "quantity": quantity, "started_at": now(), "ends_at": ends}
    ops = Ops()
    quest_progress(ops, p, "recruit_units", "recruit_units", quantity)
    alt_quest_progress(ops, p, "all_research_and_buildings_at_max")  # v1.5: recruiting counts as the research task when research and buildings are maxed
    ops.add("codex.units", unit)
    upd = ops.build()
    upd.setdefault("$inc", {}).update(inc)
    upd["$push"] = {"kingdom.recruit_queue": item}
    upd.setdefault("$set", {}).update({"kingdom.queue_next_end": _queue_next_end(p, ends), "updated_at": now()})
    res = await db.players.update_one(flt, upd)
    if res.matched_count == 0:
        raise fail(409, "insufficient", "Not enough resources")
    return {"unit": unit, "quantity": quantity, "queued": item, "cost": cost}


def suggest_formation(p: dict, affix_army_pct: float, enemy_mix: dict, territory_pct: float = 0.0) -> dict:
    """Best formation vs an enemy class mix (v1.2): pick the top unit types by power-per-command (counters applied), then fill the
    command capacity greedily. Deterministic; respects owned quantities, formation slots and command capacity."""
    units = units_by_key()
    slots = support_formation_slots(p["kingdom"]["castle_level"])
    cap = F.command_capacity(p["hero"]["level"], p["kingdom"]["castle_level"])
    cands = []
    for k, owned in p["army"]["units"].items():
        if k not in units or owned <= 0:
            continue
        u = units[k]
        mult = F.unit_power_multiplier(k, p["research"], p["hero"]["talents"], affix_army_pct, territory_pct)
        cpct = F.unit_counter_pct(k, enemy_mix)
        per_unit = u["base_power"] * mult * (1 + cpct / 100)
        cands.append({"key": k, "name": u["name"], "owned": owned, "cost": u["command_cost"], "per_unit": per_unit, "per_command": per_unit / u["command_cost"], "counter_pct": round(cpct, 1)})
    cands.sort(key=lambda c: -c["per_command"])
    # greedy fill in order of power-per-command: a type only takes a slot if at least one unit fits; low-stock types no longer
    # waste slots, and leftover command is filled by the next-best types (fixes "Suggerisci" leaving capacity unused)
    formation: dict = {}
    left = cap
    chosen = []
    for c in cands:
        if len(chosen) >= slots or left < c["cost"]:
            continue
        q = min(c["owned"], left // c["cost"])
        if q > 0:
            formation[c["key"]] = int(q)
            left -= q * c["cost"]
            chosen.append(c)
        if left <= 0:
            break
    power = sum(formation[k] * next(c["per_unit"] for c in chosen if c["key"] == k) for k in formation)
    return {"formation": formation, "army_power": rnd(power), "command_used": cap - left, "command_capacity": cap, "formation_slots": slots,
            "picks": [{**{kk: vv for kk, vv in c.items() if kk != "per_unit"}, "per_command": round(c["per_command"], 2), "quantity": formation.get(c["key"], 0)} for c in cands]}



async def set_formation(p: dict, formation: dict) -> dict:
    units = units_by_key()
    slots = support_formation_slots(p["kingdom"]["castle_level"])
    clean_f = {k: int(v) for k, v in formation.items() if k in units and int(v) > 0}
    if len(clean_f) > slots:
        raise fail(400, "too_many_types", f"Formation allows {slots} unit types at Castle {p['kingdom']['castle_level']}")
    for k, v in clean_f.items():
        if v > p["army"]["units"].get(k, 0):
            raise fail(400, "not_enough_units", f"You own {p['army']['units'].get(k, 0)} {units[k]['name']}")
    cap = F.command_capacity(p["hero"]["level"], p["kingdom"]["castle_level"])
    used = sum(units[k]["command_cost"] * v for k, v in clean_f.items())
    if used > cap:
        raise fail(400, "command_exceeded", f"Command {used}/{cap}")
    res = await db.players.update_one({"_id": p["_id"], "version": p["version"]}, {"$set": {"army.formation": clean_f, "updated_at": now()}, "$inc": {"version": 1}})
    if res.matched_count == 0:
        raise fail(409, "state_changed")
    return {"formation": clean_f, "command_used": used, "command_capacity": cap}
