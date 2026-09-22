"""Unit tests: canonical formulas must reproduce the CANONICAL_SPEC sample tables exactly (v1.1 baseline + v1.2 live update)."""
from app.core.canon import REQUIRED_SPEC_HASH, canon, compute_spec_hash, validation_report
from app.domain import formulas as F
from app.domain.domain_map import conquest_order
from app.domain.hero import apply_xp


def test_canon_validation():
    r = validation_report()
    assert r["VERSION"] == "1.8"
    assert r["SPEC_HASH"] == REQUIRED_SPEC_HASH == compute_spec_hash(canon())
    assert r["GEAR_SLOTS"] == 9 and r["CAMPAIGN_STAGES"] == 200 and r["RESEARCH_NODES"] == 48 and r["UNITS"] == 13


def test_enemy_power_table():
    # v1.1 audit table (04_GAMEPLAY_ECONOMIA_LIVEOPS): stage 1 = 75, stage 200 = 698,958 before the v1.2 ramp (x1.6 at 200)
    assert F.enemy_power(1) == 75 and F.enemy_power(50) == round(75 * 1.043 ** 49)
    assert F.difficulty_ramp(50) == 1 and abs(F.difficulty_ramp(100) - 1.075) < 1e-9 and abs(F.difficulty_ramp(200) - 1.225) < 1e-9
    assert F.enemy_power(200) == round(75 * 1.043 ** 199 * 1.225)  # v1.4 curve: boss 200 stays beatable
    assert F.enemy_required_power(200) == round(F.enemy_power(200) * 1.85)
    assert F.enemy_required_power(5) == round(F.enemy_power(5) * 1.35)


def test_unit_counters_v12():
    cc = canon()["units"]["counters"]
    assert cc["bonus_pct"] == 30 and cc["malus_pct"] == 20 and len(cc["table"]) == 13
    assert next(u for u in canon()["units"]["catalog"] if u["key"] == "conquest_wagon")["name"] == "Ariete d'Assedio"
    # every family and boss has a class
    fams = {f for r in canon()["battle"]["regions"] for f in r["enemy_families"]} | {r["region_boss"] for r in canon()["battle"]["regions"]}
    assert fams <= set(canon()["battle"]["enemy_classes"])
    # region 1: 2 umanoidi + 2 bestie -> infantry (+30 vs bestie) = +15%; boss stage 10: 50% giganti + 25% umanoidi + 25% bestie
    assert F.stage_enemy_mix(5) == {"umanoidi": 0.5, "bestie": 0.5}
    assert F.unit_counter_pct("infantry", F.stage_enemy_mix(5)) == 15.0
    assert F.unit_counter_pct("archer", F.stage_enemy_mix(5)) == 5.0  # +30*0.5 -20*0.5
    m10 = F.stage_enemy_mix(10)
    assert abs(m10["giganti"] - 0.5) < 1e-9 and abs(F.unit_counter_pct("catapult", m10) - (15 - 5)) < 1e-9
    assert F.unit_counter_pct("dragon", None) == 0.0
    # army class mix weighted by command cost
    mix = F.army_class_mix({"infantry": 10, "cavalry": 2})  # 10*1 umanoidi, 2*3 bestie
    assert abs(mix["umanoidi"] - 10 / 16) < 1e-9 and abs(mix["bestie"] - 6 / 16) < 1e-9
    assert F.army_class_mix({}) == {}


def test_war_lane_counters_v12():
    from app.domain.wars import lane_power
    a = {"war_power": 1000, "hero_power": 500, "army_per_unit": {"archer": 500}, "army_class_mix": {"umanoidi": 1.0}, "roster_pct": 0}
    d = {"war_power": 1000, "hero_power": 500, "army_per_unit": {"catapult": 500}, "army_class_mix": {"corazzati": 1.0}, "roster_pct": 0}
    pa, ca = lane_power(a, d)  # archers -20% vs corazzati -> 500 + 400
    pd, cd = lane_power(d, a)  # catapult neutral vs umanoidi
    assert abs(pa - 900) < 1e-6 and abs(ca + 20) < 1e-6 and abs(pd - 1000) < 1e-6 and cd == 0.0
    npc = {"npc": True, "war_power": 700}
    assert lane_power(a, npc) == (1000.0, 0.0) and lane_power(npc, a) == (700.0, 0.0)
    legacy = {"war_power": 1234}
    assert lane_power(legacy, a) == (1234.0, 0.0)


def test_first_clear_rewards_table():
    assert F.first_clear_rewards(200) == {"xp": 31940, "gold": 11549, "soft": 6229}
    assert F.first_clear_rewards(1) == {"xp": 25, "gold": 18, "soft": 12}
    assert F.split_soft(6229) == {"grain": 6229 - int(6229 * 0.28) - int(6229 * 0.24) - int(6229 * 0.18), "wood": int(6229 * 0.28), "clay": int(6229 * 0.24), "iron": int(6229 * 0.18)}


def test_hero_xp_table():
    assert F.xp_to_next(1) == 120 and F.xp_to_next(2) == round(80 * 2 ** 1.55 + 80)
    lvl, xp, gained = apply_xp(1, 0, 120)
    assert (lvl, xp, gained) == (2, 0, 1)
    lvl, xp, _ = apply_xp(99, 0, 10**9)
    assert lvl == 100


def test_command_capacity_samples():
    assert F.command_capacity(1, 1) == 80 and F.command_capacity(100, 20) == 9050


def test_item_level_and_stats_samples():
    assert F.item_level_for_stage(1) == 1 and F.item_level_for_stage(199) == 100 and F.item_level_for_stage(250) == 100
    assert F.item_base_stats("weapon", 50, "rare")["attack"] == 99  # round(10*(1+50*0.12)*1.42) = round(99.4)
    assert F.item_base_stats("chest", 100, "legendary")["hp"] == 2288  # 80*13*2.2


def test_forge_costs_cumulative_samples():
    for il, row in canon()["gear"]["forge"]["samples"].items():
        il = int(il)
        gold = sum(F.forge_next_cost(il, f)["gold"] for f in range(20))
        dust = sum(F.forge_next_cost(il, f)["forge_dust"] for f in range(20))
        assert abs(gold - row["gold_0_to_20"]) / row["gold_0_to_20"] < 0.01, (il, gold)
        assert abs(dust - row["forge_dust_0_to_20"]) / row["forge_dust_0_to_20"] < 0.05, (il, dust)
    assert F.forge_multiplier(20) == 1 + 0.8 + 0.8


def test_offline_hourly_equivalence_stage_200():
    rep = F.repeat_rewards(200)
    eff = canon()["offline"]["battle_loot_efficiency"]
    cycles = 3600 / canon()["battle"]["repeat_farm_cycle_seconds"]
    # audit table: stage 200 offline/hour = 33,537 XP · 29,103 Gold · 10,465 soft
    assert abs(round(rep["xp"] * cycles * eff) - 33537) <= 1
    assert abs(round(rep["gold"] * cycles * eff) - 29103) <= 1
    assert abs(round(rep["soft"] * cycles * eff) - 10465) <= 1


def test_drop_weights_respect_rarity_unlock():
    w = F.unlocked_drop_weights(10)
    assert "rare" not in w and abs(sum(w.values()) - 1) < 1e-9  # rare unlocks at 25 (Bible rarity table)
    assert "epic" not in F.unlocked_drop_weights(30)
    assert "ancient" in F.unlocked_drop_weights(190)


def test_domain_order_is_adjacent_and_complete():
    order = conquest_order()
    assert len(order) == 100 and len(set(order)) == 100 and order[0] == 44
    owned = {order[0]}
    for idx in order[1:]:
        x, y = idx % 10, idx // 10
        assert any((nx + ny * 10) in owned for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if 0 <= nx < 10 and 0 <= ny < 10)
        owned.add(idx)
    assert F.domain_tiles_for_stage(200) == 100 and F.domain_tiles_for_stage(3) == 1 and F.domain_tiles_for_stage(4) == 2 and F.domain_tiles_for_stage(199) == 99


def test_speedup_and_boss_formulas():
    assert F.speedup_rubies(2) == 5 and F.speedup_rubies(60) == 20
    assert F.boss_hp(1) == 500000 and F.boss_hp(10) == round(500000 * 10 ** 1.8)
    assert F.boss_attack_damage(1000) == 4000
    assert F.salvage_yield("legendary", 100, __import__("random").Random(1))["forge_dust"] == 40 + 10 * 5
