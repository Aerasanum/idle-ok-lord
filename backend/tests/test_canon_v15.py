"""Canon v1.5: unlock coherence, rarity tables, domain sequence, rounding, reforge doc, quest alternatives, war casualties."""
import math

from app.core.canon import canon, research_by_key, units_by_key
from app.domain import formulas as F
from app.domain.progress import Ops, alt_quest_progress, quest_alternatives, quest_points
from app.domain.wars import lane_casualties, resolve_lanes


def test_effective_unlock_is_max_of_castle_and_research_gate():
    research = research_by_key()
    for u in canon()["units"]["catalog"]:
        req = u.get("required_research")
        expected = max(u["unlock_castle_level"], research[req]["unlock_castle_level"] if req else 0)
        assert u["effective_unlock_castle_level"] == expected
    units = units_by_key()
    assert units["archer"]["unlock_castle_level"] == 3 and units["archer"]["effective_unlock_castle_level"] == 4
    assert units["cavalry"]["effective_unlock_castle_level"] == 7 and units["war_elephant"]["effective_unlock_castle_level"] == 13


def test_drop_bands_never_list_locked_rarities_and_sum_to_100():
    g = canon()["gear"]
    unlock = g["rarity_unlock_stage"]
    for band in g["stage_drop_weights"]:
        lo, hi = (int(x) for x in band["stages"].split("-"))
        assert sum(band["weights_pct"].values()) == 100
        for r, w in band["weights_pct"].items():
            if w > 0:
                assert unlock[r] <= lo, f"{r} listed in band {band['stages']} but unlocks at {unlock[r]}"
    # bands cover 1..200 contiguously
    edges = [tuple(int(x) for x in b["stages"].split("-")) for b in g["stage_drop_weights"]]
    assert edges[0][0] == 1 and edges[-1][1] == 200 and all(edges[i][1] + 1 == edges[i + 1][0] for i in range(len(edges) - 1))
    # the live filter is now a no-op on the tables (same weights, only renormalized)
    for stage in (1, 9, 10, 24, 25, 49, 50, 90, 140, 180, 200):
        w = F.unlocked_drop_weights(stage)
        assert abs(sum(w.values()) - 1) < 1e-9
        assert all(unlock[r] <= stage for r in w)
    assert "rare" not in F.unlocked_drop_weights(24) and "rare" in F.unlocked_drop_weights(25)
    assert "uncommon" not in F.unlocked_drop_weights(9) and "uncommon" in F.unlocked_drop_weights(10)
    assert "epic" not in F.unlocked_drop_weights(49) and "epic" in F.unlocked_drop_weights(50)


def test_domain_sequence_100_tiles_full_at_200():
    pd = canon()["personal_domain"]
    seq = [F.domain_tiles_for_stage(s) for s in range(0, 201)]
    assert seq[0] == seq[1] == seq[3] == 1 and seq[4] == 2 and seq[5] == 2 and seq[6] == 3
    assert seq[199] == 99 and seq[200] == 100 and max(seq) == 100
    assert all(0 <= seq[i + 1] - seq[i] <= 1 for i in range(200))  # never more than one tile per stage, never decreasing
    assert sum(1 for i in range(1, 201) if seq[i] > seq[i - 1]) == 99  # exactly 99 extra tiles
    for k, v in pd["sequence_examples"].items():
        s = int(k.split("-")[-1])
        assert F.domain_tiles_for_stage(s) == v


def test_rounding_rules_match_formulas():
    assert F.item_level_for_stage(1) == 1 and F.item_level_for_stage(3) == 2 and F.item_level_for_stage(200) == 100 and F.item_level_for_stage(199) == 100
    assert F.talent_points_for_level(4) == 0 and F.talent_points_for_level(5) == 1 and F.talent_points_for_level(100) == 20
    assert F.monsters_per_wave(1) == 4 and F.monsters_per_wave(25) == 4 and F.monsters_per_wave(26) == 5 and F.monsters_per_wave(200) == 11
    assert F.boss_minions(19) == 0 and F.boss_minions(20) == 1 and F.boss_minions(200) == 10
    assert F.forge_next_cost(50, 3)["forge_dust"] == math.ceil((2 + 50 * 0.08) * 1.22 ** 3)
    assert F.speedup_rubies(0) == 5 and F.speedup_rubies(15) == 5 and F.speedup_rubies(15.1) == 6 and F.speedup_rubies(60) == 20
    assert canon()["document"]["rounding"]["speedup_rubies"].startswith("max(5, ceil(")


def test_reforge_documented_behaviour():
    r = canon()["gear"]["reforge"]
    assert r["retired_affix_protected"] is False and "primary stats" in r["never_decrease_applies_to"]


def _player(forge_max: bool, research_max: bool, buildings_max: bool) -> dict:
    c = canon()
    return {
        "_id": "p", "quests": {},
        "forge": {s: (c["gear"]["forge"]["max_level_per_slot"] if forge_max else 0) for s in c["gear"]["slots"]},
        "research": {n["key"]: (n["max_level"] if research_max else 0) for n in c["research"]["nodes"]},
        "kingdom": {"buildings": {b["key"]: (b["max_level"] if buildings_max else 1) for b in c["buildings"]}},
    }


def test_quest_alternatives_activate_only_when_maxed():
    assert quest_alternatives(_player(False, False, False)) == {}
    a = quest_alternatives(_player(True, False, False))
    assert set(a) == {"forge_upgrade", "forge_upgrades"} and a["forge_upgrade"]["when"] == "all_forge_slots_at_max"
    b = quest_alternatives(_player(False, True, False))
    assert set(b) == {"start_or_finish_research"} and b["start_or_finish_research"]["when"] == "all_research_at_max"
    cc = quest_alternatives(_player(False, True, True))
    assert cc["start_or_finish_research"]["when"] == "all_research_and_buildings_at_max"
    # alternative progress credits the same counters
    p = _player(True, False, False)
    ops = alt_quest_progress(Ops(), p, "all_forge_slots_at_max", 3)
    upd = ops.build()
    assert upd["$set"]["quests.daily"]["progress"]["forge_upgrade"] == 3 and upd["$set"]["quests.weekly"]["progress"]["forge_upgrades"] == 3
    # a player without a maxed forge gets nothing from the alternative
    assert alt_quest_progress(Ops(), _player(False, False, False), "all_forge_slots_at_max").build() == {}
    _, detail = quest_points("daily", p)
    assert detail["tasks"]["forge_upgrade"]["alt_active"] and "Riforgia" in detail["tasks"]["forge_upgrade"]["text"]
    assert not detail["tasks"]["clear_stages"]["alt_active"] and detail["tasks"]["clear_stages"]["text"].startswith("Supera")


def _entry(pid, formation, power):
    return {"player_id": pid, "display_name": pid, "war_power": power, "total_power": power, "hero_power": 0, "deployed_army": formation, "defense_pct": 0}


def test_lane_casualties_formulas_and_bounds():
    dep = {"infantry": 1000, "cavalry": 100, "catapult": 10, "dragon": 4}
    # even duel (r = 1): winner 25%, loser 30%
    w = lane_casualties(_entry("a", dep, 100), True, 1000, 1000, False)
    l = lane_casualties(_entry("b", dep, 100), False, 1000, 1000, False)
    assert w["rate_pct"] == 25.0 and l["rate_pct"] == 30.0
    assert w["units"]["infantry"]["lost"] == 250 and l["units"]["infantry"]["lost"] == 300
    assert w["units"]["dragon"]["lost"] == int(4 * 0.25 * 0.6) == 0 and l["units"]["dragon"]["lost"] == int(4 * 0.30 * 0.6) == 0
    assert w["units"]["catapult"]["lost"] == int(10 * 0.25 * 0.8) == 2
    # crushing (r = 0.25): winner 10%, loser 52.5%; defender x0.85
    w2 = lane_casualties(_entry("a", dep, 100), True, 4000, 1000, False)
    l2 = lane_casualties(_entry("b", dep, 100), False, 1000, 4000, True)
    assert w2["rate_pct"] == 10.0 and l2["rate_pct"] == round(52.5 * 0.85, 1)
    assert l2["units"]["infantry"]["lost"] == int(1000 * 0.525 * 0.85)
    # bounds: never above deployed, at least one survivor per type, totals consistent
    for c in (w, l, w2, l2):
        for k, v in c["units"].items():
            assert 0 <= v["lost"] < v["deployed"] and v["survived"] >= 1 and v["lost"] + v["survived"] == v["deployed"]
        assert c["lost_total"] == sum(v["lost"] for v in c["units"].values())
    # NPC and empty entries never lose troops
    assert lane_casualties({"npc": True, "war_power": 10}, False, 10, 100, True) is None
    assert lane_casualties({"player_id": None, "empty": True, "war_power": 0}, False, 0, 100, False) is None


def test_resolve_lanes_attaches_casualties_and_skips_empty_lanes():
    aw = canon()["alliance_war"]
    attackers = [_entry(f"a{i}", {"infantry": 100}, 1000 - i) for i in range(8)]
    attackers += [{"player_id": None, "display_name": "Corsia vuota", "npc": True, "empty": True, "war_power": 0, "total_power": 0, "defense_pct": 0}] * 2
    defenders = [_entry(f"d{i}", {"archer": 50}, 900 - i) for i in range(10)]
    snap = {"attackers": attackers, "defenders": defenders, "seed": "war_test", "node_type": "city", "defender_fortress_adjacent_pct": 0, "variance_range": aw["seeded_variance_range"]}
    res = resolve_lanes(snap)
    assert len(res["lanes"]) == 10
    for lane in res["lanes"]:
        if lane["attacker"] == "Corsia vuota":
            assert lane["attacker_casualties"] is None and lane["defender_casualties"] is None and not lane["attacker_wins"]
        else:
            a, d = lane["attacker_casualties"], lane["defender_casualties"]
            assert a["won"] == lane["attacker_wins"] and d["won"] == (not lane["attacker_wins"])
            assert a["units"]["infantry"]["deployed"] == 100 and 0 <= a["units"]["infantry"]["lost"] < 100
            assert d["units"]["archer"]["deployed"] == 50 and 0 <= d["units"]["archer"]["lost"] < 50
            # the loser of a lane always loses a larger share than the winner
            loser, winner = (d, a) if lane["attacker_wins"] else (a, d)
            assert loser["rate_pct"] > winner["rate_pct"]
