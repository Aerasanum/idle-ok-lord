"""Player state: creation, derived stats, lazy settlement of production/timers/offline accrual."""
from datetime import timedelta

from ..core import db
from ..core.canon import buildings_by_key, canon, research_by_key, support_formation_slots, units_by_key
from ..core.util import aware, clean, fail, new_id, now, rnd
from . import formulas as F

ONLINE_GAP_SECONDS = 300  # implementation parameter: gaps longer than this accrue to the offline chest (not a gameplay value)
SOFT = ["grain", "wood", "clay", "iron", "gold"]


def initial_state(account_id: str, display_name: str) -> dict:
    c = canon()
    slots = c["gear"]["slots"]
    return {
        "_id": new_id("p_"),
        "account_id": account_id,
        "display_name": display_name,
        "heraldic_color": "#800020",
        "version": 1,
        "created_at": now(),
        "updated_at": now(),
        "last_seen_at": now(),
        "resources": dict(c["resources"]["initial"], war_coins=0, event_tokens=0),
        "hero": {"level": 1, "xp": 0, "talents": {"warrior": 0, "guardian": 0, "commander": 0, "fortune": 0}, "skill_slots": [None, None, None]},
        "forge": {s: 0 for s in slots},
        "equipped": {s: None for s in slots},
        "inventory_capacity": c["gear"]["inventory"]["base_slots"],
        "auto_salvage": {"enabled": False, "max_rarity": "common", "below_equipped": False, "slots": []},
        "kingdom": {
            "castle_level": 1,
            "buildings": {"castle": 1, "farm": 1, "lumberyard": 1, "clay_pit": 1, "warehouse": 1},
            "construction_queue": [],
            "recruit_queue": [],
            "research_queue": [],
            "queue_next_end": None,
            "last_production_at": now(),
        },
        "research": {},
        "army": {"units": {}, "formation": {}},
        "domain": {"owned": 1},
        "campaign": {"highest_cleared": 0, "current_stage": 1, "active_attempt": None},
        "offline": {"chest_from": None, "pending_hours": 0.0, "pending_production": {}, "pending_timers": []},
        "stats": {
            "kills": 0, "legendary_or_higher_items_found": 0, "units_recruited_total": 0, "event_deployments_completed": 0,
            "alliance_war_lanes_or_boss_attacks": 0, "dungeon_runs": 0, "forge_upgrades": 0, "items_found": 0, "offline_hours": 0.0,
        },
        "quests": {"daily": None, "weekly": None, "login": {"cycle_day": 0, "last_claim_day": None}},
        "achievements_claimed": [],
        "codex": {"regions": [], "monster_families": [], "bosses": [], "units": [], "gear_rarities": []},
        "codex_milestones_claimed": [],
        "events": {"energy": c["events"]["energy"]["max"], "energy_at": now(), "paid_refills": {}, "track_points": 0, "event_key": None,
                   "claimed_free": [], "claimed_premium": [], "deployments_today": {}, "booster_until": None},
        "dungeons": {"day": None, "entries": {}},
        "season": {"points": 0, "claimed_free": [], "claimed_premium": [], "season_key": None},
        "alliance_id": None,
        "cosmetics": {"owned": [], "hero_cloak": None, "profile_frame": None, "castle_skin": None},
        "settings": {"push_nonessential": True, "analytics": False, "consent_at": None, "language": "it", "tutorial_done": False, "music_volume": 0.6, "sfx_volume": 0.8},
        "recent_ledger_keys": [],
        "recent_attempts": [],
    }


async def get_player(player_id: str) -> dict:
    p = await db.players.find_one({"_id": player_id})
    if not p:
        raise fail(404, "player_not_found")
    return p


# ---- derived --------------------------------------------------------------------------
def research_pct(research: dict, effect_key: str) -> float:
    total = 0.0
    nodes = research_by_key()
    for k, lvl in research.items():
        n = nodes.get(k)
        if n and n["effect_key"] == effect_key and lvl:
            total += n["effect_per_level_pct"] * lvl
    return total


def production_per_hour(p: dict, territory_bonus: dict | None = None) -> dict:
    """Canonical building production x (1 + resource research + all-resource research + domain bonus + territory bonus)."""
    b = buildings_by_key()
    out = {k: 0.0 for k in SOFT}
    for key, lvl in p["kingdom"]["buildings"].items():
        row = b[key]["levels"][lvl - 1]
        for res, val in (row.get("production_per_hour") or {}).items():
            out[res] += val
    dom = F.domain_bonus_pct(p["domain"]["owned"])
    allp = research_pct(p["research"], "all_resource_production_pct")
    tb = territory_bonus or {}
    for res in out:
        pct = research_pct(p["research"], f"{res}_production_pct") + allp + dom
        pct += tb.get("basic_resource_production_pct", 0) if res in ("grain", "wood", "clay") else 0
        pct += tb.get("iron_and_gold_production_pct", 0) if res in ("iron", "gold") else 0
        out[res] = out[res] * (1 + pct / 100)
    return out


def warehouse_capacity(p: dict) -> int:
    lvl = p["kingdom"]["buildings"].get("warehouse", 1)
    cap = buildings_by_key()["warehouse"]["levels"][lvl - 1]["capacity_each_resource"]
    return int(cap * (1 + research_pct(p["research"], "warehouse_capacity_pct") / 100))


def talents_pct(p: dict) -> dict:
    t = p["hero"]["talents"]
    return {"attack": t.get("warrior", 0) * 2, "hp_def": t.get("guardian", 0) * 2, "army": t.get("commander", 0) * 1.5, "fortune": t.get("fortune", 0) * 1.5}


def hero_stats(p: dict, items: list[dict]) -> dict:
    """Additive base+gear (forge-multiplied) stats, then percentage talents/affixes."""
    base = F.hero_base_stats(p["hero"]["level"])
    add = dict(base)
    affix = {}
    for it in items:
        fm = F.forge_multiplier(p["forge"].get(it["slot"], 0))
        for k, v in it["stats"].items():
            add[k] = add.get(k, 0) + v * fm
        for a in it.get("affixes", []):
            affix[a["key"]] = affix.get(a["key"], 0) + a["value"]
    caps = canon()["gear"]["affix_values"]["caps"]
    for k in list(affix):
        if k in caps:
            affix[k] = min(affix[k], caps[k])
    tp = talents_pct(p)
    crit = (affix.get("crit_chance_pct", 0) / 100) * (affix.get("crit_damage_pct", 0) / 100)
    atk = add["attack"] * (1 + tp["attack"] / 100) * (1 + crit) * (1 + affix.get("attack_speed_pct", 0) / 100)
    dfn = add["defense"] * (1 + tp["hp_def"] / 100)
    hp = add["hp"] * (1 + tp["hp_def"] / 100) * (1 + affix.get("lifesteal_pct", 0) / 100) / max(0.01, 1 - affix.get("dodge_pct", 0) / 100)
    power = rnd(atk * 2 + dfn * 1.5 + hp * 0.15)
    return {"attack": rnd(atk), "defense": rnd(dfn), "hp": rnd(hp), "power": power, "affixes": affix, "base": base,
            "boss_damage_pct": affix.get("boss_damage_pct", 0), "gold_find_pct": affix.get("gold_find_pct", 0) + tp["fortune"],
            "gear_find_pct": affix.get("gear_find_pct", 0) + tp["fortune"]}


def army_power(p: dict, affix_army_pct: float, territory_pct: float = 0.0, enemy_mix: dict | None = None) -> tuple[int, dict, dict]:
    """Returns (total, per-unit power, per-unit counter %). Counter % (v1.2) applies only when an enemy class mix is given."""
    units = units_by_key()
    total = 0.0
    per_unit = {}
    counter = {}
    for key, qty in p["army"]["formation"].items():
        if not qty or key not in units:
            continue
        mult = F.unit_power_multiplier(key, p["research"], p["hero"]["talents"], affix_army_pct, territory_pct)
        cpct = F.unit_counter_pct(key, enemy_mix)
        val = qty * units[key]["base_power"] * mult * (1 + cpct / 100)
        per_unit[key] = rnd(val)
        counter[key] = round(cpct, 1)
        total += val
    return rnd(total), per_unit, counter


async def equipped_items(p: dict) -> list[dict]:
    ids = [v for v in p["equipped"].values() if v]
    if not ids:
        return []
    return await db.gear_items.find({"_id": {"$in": ids}, "owner_id": p["_id"]}).to_list(20)


async def combat_profile(p: dict, territory: dict | None = None, enemy_mix: dict | None = None) -> dict:
    items = await equipped_items(p)
    hs = hero_stats(p, items)
    tb = territory or {}
    ap, per_unit, counter = army_power(p, hs["affixes"].get("army_power_pct", 0), tb.get("war_roster_power_pct", 0), enemy_mix)
    cap = F.command_capacity(p["hero"]["level"], p["kingdom"]["castle_level"])
    used = sum(units_by_key()[k]["command_cost"] * q for k, q in p["army"]["formation"].items() if k in units_by_key())
    return {
        "hero": hs,
        "army_power": ap,
        "army_per_unit": per_unit,
        "army_counter_pct": counter,
        "enemy_mix": enemy_mix or {},
        "total_power": hs["power"] + ap,
        "command_capacity": cap,
        "command_used": used,
        "formation_slots": support_formation_slots(p["kingdom"]["castle_level"]),
        "army_deployed": used > 0,
    }


# ---- settlement -----------------------------------------------------------------------------
def _apply_completed_queues(p: dict, t) -> tuple[dict, list]:
    """Return ($set/$inc ops, completed timers) for queue items with ends_at <= t."""
    k = p["kingdom"]
    sets, incs, done = {}, {}, []
    research_done = {}
    remaining = {}
    for qname in ("construction_queue", "recruit_queue", "research_queue"):
        keep = []
        for item in k.get(qname, []):
            if aware(item["ends_at"]) <= t:
                done.append({"queue": qname, **{kk: vv for kk, vv in item.items() if kk != "ends_at"}, "ended_at": item["ends_at"]})
                if qname == "construction_queue":
                    sets[f"kingdom.buildings.{item['building']}"] = item["target_level"]
                    if item["building"] == "castle":
                        sets["kingdom.castle_level"] = item["target_level"]
                elif qname == "research_queue":
                    research_done[item["node"]] = item["target_level"]  # node keys contain dots: never use them as Mongo paths
                elif qname == "recruit_queue":
                    incs[f"army.units.{item['unit']}"] = incs.get(f"army.units.{item['unit']}", 0) + item["quantity"]
            else:
                keep.append(item)
        remaining[qname] = keep
    if research_done:
        sets["research"] = {**p.get("research", {}), **research_done}
    if done:
        for qname, keep in remaining.items():
            sets[f"kingdom.{qname}"] = keep
        ends = [aware(i["ends_at"]) for q in remaining.values() for i in q]
        sets["kingdom.queue_next_end"] = min(ends) if ends else None
    ops = {}
    if sets:
        ops["$set"] = sets
    if incs:
        ops["$inc"] = incs
    return ops, done


async def settle(p: dict) -> dict:
    """Lazy settlement: complete timers, credit online production or accrue offline chest. Version-guarded."""
    t = now()
    last_seen = aware(p.get("last_seen_at")) or t
    gap = (t - last_seen).total_seconds()
    ops, done = _apply_completed_queues(p, t)
    sets = ops.setdefault("$set", {})
    incs = ops.setdefault("$inc", {})
    prod = production_per_hour(p)
    cap = warehouse_capacity(p)
    last_prod = aware(p["kingdom"].get("last_production_at")) or t
    hours = max(0.0, (t - last_prod).total_seconds() / 3600)
    off = p["offline"]
    if gap <= ONLINE_GAP_SECONDS:
        for res, per_h in prod.items():
            gain = per_h * hours
            cur = p["resources"].get(res, 0)
            if gain > 0 and cur < cap:
                incs[f"resources.{res}"] = incs.get(f"resources.{res}", 0) + int(min(gain, cap - cur))
    else:
        max_h = canon()["offline"]["max_hours"]
        already = off.get("pending_hours", 0.0)
        add_h = max(0.0, min(hours, max_h - already))
        if add_h > 0:
            eff = canon()["offline"]["resource_efficiency"]
            for res, per_h in prod.items():
                incs[f"offline.pending_production.{res}"] = incs.get(f"offline.pending_production.{res}", 0) + int(per_h * add_h * eff)
            incs["offline.pending_hours"] = add_h
            if not off.get("chest_from"):
                sets["offline.chest_from"] = last_prod
        if done:
            sets["offline.pending_timers"] = (off.get("pending_timers") or []) + [{"queue": d["queue"], "ended_at": d["ended_at"], **{k: v for k, v in d.items() if k in ("building", "target_level", "node", "unit", "quantity")}} for d in done]
    sets["kingdom.last_production_at"] = t
    sets["last_seen_at"] = t
    sets["updated_at"] = t
    incs["version"] = 1
    if not incs:
        ops.pop("$inc", None)
    res = await db.players.update_one({"_id": p["_id"], "version": p["version"]}, ops)
    if res.matched_count == 0:
        return await db.players.find_one({"_id": p["_id"]})
    return await db.players.find_one({"_id": p["_id"]})


async def load(player_id: str) -> dict:
    return await settle(await get_player(player_id))


async def public_state(p: dict) -> dict:
    prof = await combat_profile(p)
    items = await equipped_items(p)
    out = clean({k: v for k, v in p.items() if k not in ("recent_ledger_keys", "account_id")})
    out["combat"] = prof
    out["equipped_items"] = [clean(i) for i in items]
    out["production_per_hour"] = {k: rnd(v) for k, v in production_per_hour(p).items()}
    out["warehouse_capacity"] = warehouse_capacity(p)
    out["xp_to_next"] = F.xp_to_next(p["hero"]["level"])
    out["talent_points_total"] = F.talent_points_for_level(p["hero"]["level"])
    out["talent_points_spent"] = sum(p["hero"]["talents"].values())
    out["server_time"] = now().isoformat()
    return out
