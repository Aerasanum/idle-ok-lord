"""Unit tests: canonical formulas must reproduce the CANONICAL_SPEC v1.1 sample tables exactly."""
from app.core.canon import canon, validation_report
from app.domain import formulas as F
from app.domain.domain_map import conquest_order
from app.domain.hero import apply_xp


def test_canon_validation():
    r = validation_report()
    assert r["VERSION"] == "1.1"
    assert r["SPEC_HASH"] == "a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995"
    assert r["GEAR_SLOTS"] == 9 and r["CAMPAIGN_STAGES"] == 200 and r["RESEARCH_NODES"] == 48 and r["UNITS"] == 13


def test_enemy_power_table():
    # audit table (04_GAMEPLAY_ECONOMIA_LIVEOPS): stage 1 = 75, stage 200 = 698,958
    assert F.enemy_power(1) == 75 and F.enemy_power(200) == 698958
    assert F.enemy_required_power(200) == round(698958 * 1.85)
    assert F.enemy_required_power(5) == round(F.enemy_power(5) * 1.35)


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
    assert F.domain_tiles_for_stage(200) == 100 and F.domain_tiles_for_stage(3) == 2


def test_speedup_and_boss_formulas():
    assert F.speedup_rubies(2) == 5 and F.speedup_rubies(60) == 20
    assert F.boss_hp(1) == 500000 and F.boss_hp(10) == round(500000 * 10 ** 1.8)
    assert F.boss_attack_damage(1000) == 4000
    assert F.salvage_yield("legendary", 100, __import__("random").Random(1))["forge_dust"] == 40 + 10 * 5
