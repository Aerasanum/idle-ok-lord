"""All canonical formulas (CANONICAL_SPEC v1.1 + v1.2 live update). No constant here is invented: each maps to a spec field."""
from ..core.canon import canon, region_for_stage, stage_drop_weights, units_by_key
from ..core.util import ceil, rnd


# ---- battle -----------------------------------------------------------------
def difficulty_ramp(stage: int) -> float:
    r = canon()["battle"]["difficulty_ramp"]
    return 1 + r["per_stage"] * max(0, stage - r["start_stage"])


def enemy_power(stage: int) -> int:
    b = canon()["battle"]
    return rnd(b.get("enemy_power_base", 75) * (b.get("enemy_power_growth", 1.047) ** (stage - 1)) * difficulty_ramp(stage))


# ---- unit counters (v1.2) ---------------------------------------------------
def enemy_class(family: str) -> str:
    return canon()["battle"]["enemy_classes"][family]


def stage_enemy_mix(stage: int) -> dict:
    """Share of each enemy class in a stage: region families equally; boss stages 50% boss class + 50% families."""
    region = region_for_stage(min(stage, canon()["battle"]["campaign_stages"]))
    fams = region["enemy_families"]
    mix: dict = {}
    fam_share = 1.0 / len(fams)
    if stage_kind(stage) == "boss":
        bm = canon()["units"]["counters"]["pve_stage_mix"]["boss"]
        mix[enemy_class(region["region_boss"])] = bm["boss_class"]
        fam_share *= bm["families"]
    for f in fams:
        c = enemy_class(f)
        mix[c] = mix.get(c, 0) + fam_share
    return mix


def army_class_mix(formation: dict) -> dict:
    """Class shares of a deployed army weighted by command cost (0 shares when nothing is deployed)."""
    ct = canon()["units"]["counters"]["unit_class"]
    units = units_by_key()
    w: dict = {}
    for k, q in formation.items():
        if q and k in units:
            w[ct[k]] = w.get(ct[k], 0) + units[k]["command_cost"] * q
    tot = sum(w.values())
    return {c: v / tot for c, v in w.items()} if tot else {}


def unit_counter_pct(unit_key: str, mix: dict | None) -> float:
    """Signed % applied to one unit's power against an enemy class mix (+bonus_pct strong, -malus_pct weak, weighted by share)."""
    if not mix:
        return 0.0
    cc = canon()["units"]["counters"]
    row = cc["table"][unit_key]
    pct = 0.0
    for cls, share in mix.items():
        if cls in row["strong_vs"]:
            pct += share * cc["bonus_pct"]
        elif cls in row["weak_vs"]:
            pct -= share * cc["malus_pct"]
    return pct


def stage_kind(stage: int) -> str:
    b = canon()["battle"]
    if stage % b["boss_every_stages"] == 0:
        return "boss"
    if stage % b["elite_every_stages"] == 0:
        return "elite"
    return "normal"


def enemy_required_power(stage: int) -> int:
    b = canon()["battle"]
    kind = stage_kind(stage)
    mult = b["boss_power_multiplier"] if kind == "boss" else b["elite_power_multiplier"] if kind == "elite" else 1.0
    return rnd(enemy_power(stage) * mult)


def first_clear_rewards(stage: int) -> dict:
    return {
        "xp": rnd(25 * stage ** 1.35),
        "gold": rnd(18 * stage ** 1.22),
        "soft": rnd(12 * stage ** 1.18),
    }


def split_soft(total: int) -> dict:
    split = canon()["battle"]["soft_resource_split"]
    out = {k: int(total * v) for k, v in split.items()}
    # keep exact total: remainder to grain (largest share)
    out["grain"] += total - sum(out.values())
    return out


def repeat_rewards(stage: int) -> dict:
    b = canon()["battle"]
    fc = first_clear_rewards(stage)
    return {
        "xp": fc["xp"] * b["repeat_xp_fraction"],
        "gold": fc["gold"] * b["repeat_gold_fraction"],
        "soft": fc["soft"] * b["repeat_soft_resource_fraction"],
    }


def victory_duration(required: int, total_power: int) -> int:
    return max(18, min(90, rnd(18 + 55 * (required / max(total_power, 1)))))


def monsters_per_wave(stage: int) -> int:
    return min(12, 4 + (stage - 1) // 25)


def boss_minions(stage: int) -> int:
    return min(10, stage // 20)


def offline_gear_rolls_per_hour(highest_stage: int) -> float:
    return min(1.2, 0.35 + highest_stage / 250)


# ---- hero -------------------------------------------------------------------
def xp_to_next(level: int) -> int:
    return rnd(80 * level ** 1.55 + 40 * level)


def hero_base_stats(level: int) -> dict:
    h = canon()["hero"]
    b, g = h["base_stats"], h["stat_growth_per_level"]
    return {
        "attack": b["attack"] + (level - 1) * g["attack"],
        "defense": b["defense"] + (level - 1) * g["defense"],
        "hp": b["hp"] + (level - 1) * g["hp"],
    }


def talent_points_for_level(level: int) -> int:
    return min(20, level // 5)


def command_capacity(hero_level: int, castle_level: int) -> int:
    return 50 + hero_level * 10 + castle_level ** 2 * 20


# ---- gear -------------------------------------------------------------------
def item_level_for_stage(stage: int) -> int:
    return min(100, max(1, ceil(stage / 2)))


def forge_multiplier(f: int) -> float:
    return 1 + 0.04 * f + 0.002 * f * f


def forge_next_cost(item_level: int, forge_level: int) -> dict:
    return {
        "gold": rnd((25 + item_level * 8) * (1.35 ** forge_level)),
        "forge_dust": ceil((2 + item_level * 0.08) * (1.22 ** forge_level)),
    }


def rarity_rule(rarity: str) -> dict:
    return canon()["gear"]["rarity_rules"][rarity]


def item_base_stats(slot: str, item_level: int, rarity: str) -> dict:
    coeffs = canon()["gear"]["slot_base_coefficients"][slot]
    mult = rarity_rule(rarity)["stat_multiplier"]
    return {k: rnd(c * (1 + item_level * 0.12) * mult) for k, c in coeffs.items()}


def affix_value(key: str, item_level: int, rarity: str, roll_scalar: float) -> float:
    av = canon()["gear"]["affix_values"]
    v = av["base_at_item100"][key] * (0.35 + 0.65 * item_level / 100) * av["rarity_affix_multiplier"][rarity] * roll_scalar
    v = round(v, 2)
    cap = av["caps"].get(key)
    return min(v, cap) if cap is not None else v


def unlocked_drop_weights(stage: int) -> dict:
    """Band weights renormalized over rarities whose canonical unlock stage is reached (Bible rarity table)."""
    weights = stage_drop_weights(stage)
    unlock = canon()["gear"]["rarity_unlock_stage"]
    ok = {r: w for r, w in weights.items() if unlock[r] <= stage and w > 0}
    if not ok:
        ok = {"common": 100.0}
    total = sum(ok.values())
    return {r: w / total for r, w in ok.items()}


def salvage_yield(rarity: str, item_level: int, rng) -> dict:
    s = canon()["gear"]["salvage"]
    out = {"forge_dust": s["rarity_base"][rarity] + (item_level // 10) * s["rarity_level_factor"][rarity]}
    order = canon()["gear"]["rarity_order"]
    if order.index(rarity) >= order.index("legendary") and rng.random() * 100 < s["legendary_or_higher_extra_reforge_stone_chance_pct"]:
        out["reforge_stone"] = 1
    if rarity in ("mythic", "ancient") and rng.random() * 100 < s["mythic_or_ancient_mythic_essence_chance_pct"]:
        out["mythic_essence"] = 1
    return out


def reforge_cost(item_level: int, rarity: str) -> dict:
    r = canon()["gear"]["reforge"]
    return {"gold": rnd(50 * item_level * rarity_rule(rarity)["stat_multiplier"]), "reforge_stone": r["reforge_stone_cost_by_rarity"][rarity]}


# ---- kingdom ----------------------------------------------------------------
def speedup_rubies(remaining_minutes: float) -> int:
    return max(5, ceil(remaining_minutes / 3))


def domain_bonus_pct(owned_tiles: int) -> float:
    pd = canon()["personal_domain"]
    return min(pd["production_bonus_cap_pct"], (owned_tiles // 10) * pd["production_bonus_per_10_owned_tiles_pct"])


def domain_tiles_for_stage(highest_cleared: int) -> int:
    """v1.5: 1 start tile + 1 tile at every even cleared stage from `first_extra_tile_stage` (4) to 200 -> exactly 100 at stage 200."""
    pd = canon()["personal_domain"]
    every = canon()["battle"]["domain_tile_every_stages"]
    extra = max(0, (highest_cleared - pd["first_extra_tile_stage"]) // every + 1) if highest_cleared >= pd["first_extra_tile_stage"] else 0
    return min(pd["tiles_total"], pd["start_owned_tiles"] + extra)


# ---- events / dungeons / boss ----------------------------------------------------
def event_deploy_rewards(highest_stage: int, mult: float) -> dict:
    return {
        "event_tokens": rnd((20 + highest_stage * 0.35) * mult),
        "gold": rnd((150 + highest_stage * 8) * mult),
        "soft_hours": 0.25 * mult,
        "gear_roll_pct": min(35, 5 + highest_stage * 0.10),
    }


def boss_hp(tier: int) -> int:
    return rnd(500000 * tier ** 1.8)


def boss_attack_damage(campaign_power: int) -> int:
    return rnd(campaign_power * 4.0)


def dungeon_rewards(key: str, tier: int, highest_stage: int, production_per_hour: dict) -> dict:
    if key == "treasury_vault":
        return {"gold": rnd(1000 * 1.15 ** (tier - 1)), "soft": {k: int(v * 2) for k, v in production_per_hour.items() if k != "gold"}}
    if key == "forge_depths":
        return {"forge_dust": 80 + 25 * tier, "reforge_stone": 1 + tier // 3}
    if key == "ancient_ruins":
        return {"gear_rolls": 1, "rarity_rolls": 2 if tier <= 5 else 3, "mythic_essence": max(0, tier - 6)}
    if key == "monster_hunt":
        return {"xp": 4 * first_clear_rewards(max(1, highest_stage))["xp"], "event_tokens": 25 + 5 * tier}
    raise ValueError(key)


def unit_power_multiplier(unit_key: str, research: dict, talents: dict, affix_army_pct: float, territory_pct: float) -> float:
    """Additive percentage stack of applicable research, talents, gear affixes and territory bonuses."""
    u = units_by_key()[unit_key]
    cat = u["category"]
    nodes = {n["key"]: n for n in canon()["research"]["nodes"]}
    pct = 0.0
    for key, lvl in research.items():
        if not lvl or key not in nodes:
            continue
        eff = nodes[key]["effect_key"]
        per = nodes[key]["effect_per_level_pct"] * lvl
        applies = (
            eff == "army_power_pct"
            or eff == "army_hp_pct"
            or (eff == f"{unit_key}_power_pct")
            or (eff == "all_regular_units_power_pct" and cat == "regular")
            or (eff in ("siege_damage_pct", "siege_units_power_pct") and cat == "siege")
            or (eff in ("beast_power_pct",) and cat == "beast")
            or (eff == "wolf_falcon_power_pct" and unit_key in ("wolf", "falcon"))
            or (eff == "bear_lion_power_pct" and unit_key in ("bear", "lion"))
            or (eff == "elephant_power_pct" and unit_key == "war_elephant")
            or (eff in ("mythic_power_pct", "mythic_hp_pct") and cat == "mythic")
        )
        if applies:
            pct += per
    pct += talents.get("commander", 0) * 1.5
    pct += affix_army_pct
    pct += territory_pct
    return 1 + pct / 100


def region_info(stage: int) -> dict:
    r = region_for_stage(min(stage, 200))
    return {"region": r["region"], "name": r["name"], "boss": r["region_boss"], "families": r["enemy_families"], "visual": r["visual"]}
