"""Canon v1.5 (idempotent): rulebook coherence pass + permanent casualties in Alliance Wars.

1. Units: nominal vs effective unlock (effective = max(castle gate, castle level of the required research)); all gates kept.
2. Gear drops: rarity tables split so no band lists a weight for a rarity not yet unlocked; explicit filter rule + exceptions.
3. Domain: 100 tiles total, full at stage 200: 1 start tile + 1 tile at every even cleared stage from 4 to 200 (99).
4. Rounding rules made explicit (item level, talents, monsters, dust, speedups) - they match formulas.py and the tables.
5. Reforge: actual behaviour documented (the retired affix is NOT protected; primary stats / rarity are).
6. Quests: templates get Italian texts + alternative objectives when Forge or research are maxed.
7. Alliance War casualties: both sides lose a share of the deployed troops (formulas below); PvE unchanged.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PATH = os.path.join(ROOT, "canon", "IDLE_1_v1.1_CANONICAL_SPEC.json")
MIRROR = os.path.join(os.path.dirname(ROOT), "docs", "CANONICAL_SPEC.json")

DROP_BANDS = [
    {"stages": "1-9", "weights_pct": {"common": 100, "uncommon": 0, "rare": 0, "epic": 0, "legendary": 0, "mythic": 0, "ancient": 0}},
    {"stages": "10-24", "weights_pct": {"common": 77, "uncommon": 23, "rare": 0, "epic": 0, "legendary": 0, "mythic": 0, "ancient": 0}},
    {"stages": "25-49", "weights_pct": {"common": 56, "uncommon": 35, "rare": 9, "epic": 0, "legendary": 0, "mythic": 0, "ancient": 0}},
    {"stages": "50-89", "weights_pct": {"common": 35, "uncommon": 38, "rare": 22, "epic": 5, "legendary": 0, "mythic": 0, "ancient": 0}},
    {"stages": "90-139", "weights_pct": {"common": 15, "uncommon": 30, "rare": 35, "epic": 17, "legendary": 3, "mythic": 0, "ancient": 0}},
    {"stages": "140-179", "weights_pct": {"common": 5, "uncommon": 15, "rare": 30, "epic": 30, "legendary": 17, "mythic": 3, "ancient": 0}},
    {"stages": "180-200", "weights_pct": {"common": 2, "uncommon": 8, "rare": 20, "epic": 30, "legendary": 25, "mythic": 12, "ancient": 3}},
]

DAILY_TEXT = {
    "clear_stages": "Supera 10 stage (anche ripetuti)",
    "claim_offline": "Ritira il forziere offline",
    "forge_upgrade": "Potenzia la Forgia di uno slot",
    "recruit_units": "Recluta 25 unità",
    "start_or_finish_research": "Avvia o completa una ricerca",
    "run_dungeon": "Completa 2 dungeon",
    "event_deployment": "Completa 1 spedizione evento",
    "alliance_action": "Fai un'azione di alleanza (donazione, chat, guerra o Titano)",
}
WEEKLY_TEXT = {
    "clear_stages": "Supera 50 stage (anche ripetuti)",
    "forge_upgrades": "Potenzia la Forgia 5 volte",
    "recruit_units": "Recluta 250 unità",
    "dungeon_runs": "Completa 10 dungeon",
    "event_deployments": "Completa 10 spedizioni evento",
    "alliance_war_or_boss": "Partecipa a 2 guerre d'alleanza o attacchi al Titano",
    "collect_offline_hours": "Raccogli 24 ore di progresso offline",
}
FORGE_ALT = [{"when": "all_forge_slots_at_max", "text": "Riforgia o smantella oggetti (Forgia al massimo su tutti gli slot)", "counts": "1 per oggetto riforgiato o smantellato"}]
RESEARCH_ALT = [
    {"when": "all_research_at_max", "text": "Avvia o completa un potenziamento edificio (Ricerca al massimo)", "counts": "1 per potenziamento avviato"},
    {"when": "all_research_and_buildings_at_max", "text": "Recluta unità (Ricerca ed edifici al massimo)", "counts": "1 per ordine di reclutamento"},
]


def main() -> None:
    c = json.load(open(PATH))
    # 1. unlocks -------------------------------------------------------------------------------------------------
    nodes = {n["key"]: n for n in c["research"]["nodes"]}
    for u in c["units"]["catalog"]:
        req = u.get("required_research")
        rc = nodes[req]["unlock_castle_level"] if req else 0
        u["effective_unlock_castle_level"] = max(u["unlock_castle_level"], rc)
        u["alliance_war_permanent_death"] = True
        u["pve_permanent_death"] = False
    c["units"]["recruit_gate_rule"] = ("all listed castle / research (level >= 1) / campaign-stage gates must be satisfied. 'unlock_castle_level' is the nominal castle gate; "
                                       "'effective_unlock_castle_level' = max(nominal castle gate, castle level that unlocks the required research) is the first castle level at "
                                       "which the unit can actually be recruited (the research itself must still be completed and the campaign stage reached)")
    c["units"]["casualties"] = "PvE (campaign, dungeons, events, Titan Hunt): no permanent loss. Alliance War: permanent losses of deployed troops on both sides, see alliance_war.casualties"
    c["units"]["ownership"] = "recruited quantities persist; only Alliance War lanes remove troops permanently (alliance_war.casualties); PvE never does"
    # 2. rarity ----------------------------------------------------------------------------------------------------
    c["gear"]["stage_drop_weights"] = DROP_BANDS
    c["gear"]["drop_filter_rule"] = {
        "rule": "a rarity can drop only from its rarity_unlock_stage; in every band the weight of a locked rarity is 0 and the remaining weights are renormalized (unlocked_drop_weights). "
                "The tables above already respect this: bands are split at every unlock stage (10 uncommon, 25 rare, 50 epic, 90 legendary, 140 mythic, 180 ancient)",
        "exceptions": [
            "milestone bosses guarantee a minimum rarity (battle.gear_drop.milestone_boss_minimum_rarity: 50 epic, 100 legendary, 150 mythic, 200 ancient) - the minimum is applied after the roll",
            "Event Pass premium track milestones guarantee a minimum rarity and roll twice keeping the best (events.event_track.premium_guaranteed_gear_milestones)",
            "login calendar day 7 rolls twice keeping the best; Ancient Ruins dungeon rolls 2-3 times keeping the best - all rolls still use the unlocked table of the highest cleared stage",
        ],
    }
    # 3. domain ----------------------------------------------------------------------------------------------------
    pd = c["personal_domain"]
    pd["start_owned_tiles"] = 1
    pd["tiles_total"] = 100
    pd["first_extra_tile_stage"] = 4
    pd["full_domain_at_stage"] = 200
    pd["conquest_rule"] = "start with 1 tile; +1 adjacent tile at every even cleared campaign stage from 4 to 200 (99 tiles) - owned = min(100, 1 + max(0, floor((highest_cleared - 4) / 2) + 1))"
    pd["tiles_formula"] = "min(tiles_total, start_owned_tiles + max(0, floor((highest_cleared - first_extra_tile_stage) / battle.domain_tile_every_stages) + 1))"
    pd["sequence_examples"] = {"1-3": 1, "4": 2, "5": 2, "6": 3, "10": 5, "50": 25, "100": 50, "150": 75, "198": 99, "199": 99, "200": 100}
    # 4. rounding --------------------------------------------------------------------------------------------------
    c["document"]["rounding"] = {
        "round": "half away from zero: round(x) = floor(x + 0.5) for x >= 0 (util.rnd). Used by every formula written as round()",
        "ceil_floor": "⌈x⌉ / ⌊x⌋ are exact integer ceiling / floor",
        "item_level": "min(100, max(1, ceil(stage / 2)))",
        "talent_points": "min(20, floor(hero_level / 5))",
        "monsters_per_wave": "min(12, 4 + floor((stage - 1) / 25))",
        "boss_minions": "min(10, floor(stage / 20))",
        "forge_gold_cost": "round((25 + item_level * 8) * 1.35^F)",
        "forge_dust_cost": "ceil((2 + item_level * 0.08) * 1.22^F)",
        "salvage_dust": "rarity_base + floor(item_level / 10) * rarity_level_factor (integer, no rounding needed)",
        "speedup_rubies": "max(5, ceil(remaining_minutes / 3)) with remaining_minutes as a real number (seconds count)",
        "affix_value": "round(value, 2 decimals) then min(value, cap)",
        "enemy_power": "round(75 * 1.043^(stage-1) * ramp), then required = round(enemy_power * multiplier)",
        "recruit_time": "minutes kept as real numbers (3 decimals in the API)",
    }
    c["hero"]["talents"]["points_rule"] = "min(20, floor(level / 5))"
    c["battle"]["monsters_per_wave_formula"] = "min(12, 4 + floor((stage - 1) / 25))"
    c["battle"]["boss_minions_formula"] = "min(10, floor(stage / 20))"
    c["kingdom"]["speedup_rubies_formula"] = "max(5, ceil(remaining_minutes / 3))"
    c["gear"]["item_level_formula"] = "min(100, max(1, ceil(source_stage / 2)))"
    # 5. reforge ---------------------------------------------------------------------------------------------------
    c["gear"]["reforge"]["effect"] = ("replaces ONE chosen secondary affix with a new random affix drawn from the affix pool minus the affixes already present on the other slots "
                                      "of the item (the same affix type can come back), with a fresh value roll (roll_scalar 0.85-1.15). The new affix may be of a different "
                                      "type and its value may be lower or higher than the retired one. Primary stats, rarity, item level, Forge level and the other affixes never change")
    c["gear"]["reforge"]["retired_affix_protected"] = False
    c["gear"]["reforge"]["never_decrease_applies_to"] = ["primary stats", "rarity", "item level", "forge level", "the other affixes"]
    # 6. quests ----------------------------------------------------------------------------------------------------
    for t in c["quests"]["daily"]["templates"]:
        t["text"] = DAILY_TEXT[t["key"]]
        t.pop("alternatives", None)
        if t["key"] == "forge_upgrade":
            t["alternatives"] = FORGE_ALT
        if t["key"] == "start_or_finish_research":
            t["alternatives"] = RESEARCH_ALT
    for t in c["quests"]["weekly"]["templates"]:
        t["text"] = WEEKLY_TEXT[t["key"]]
        t.pop("alternatives", None)
        if t["key"] == "forge_upgrades":
            t["alternatives"] = FORGE_ALT
    c["quests"]["fallback_rule"] = ("when the base objective of a task is permanently impossible (Forge +20 on all 9 slots; all 48 research nodes at level 5; then also all buildings at max), "
                                    "the first applicable alternative increments the SAME counter and its text replaces the base text in the app. Conditions are evaluated live on the player")
    # 7. alliance war casualties -----------------------------------------------------------------------------------
    c["alliance_war"]["casualties"] = {
        "enabled": True,
        "scope": "Alliance War lanes only (attack and defense). PvE never removes troops",
        "power_ratio": "r = min(A, D) / max(A, D), where A and D are the final lane powers (after counters, bonuses and seeded variance) - 1 = even duel, ~0 = crushing",
        "loser_rate": {"formula": "0.30 + 0.30 * (1 - r)", "min_pct": 30, "max_pct": 60},
        "winner_rate": {"formula": "0.05 + 0.20 * r", "min_pct": 5, "max_pct": 25},
        "defender_multiplier": 0.85,
        "category_multiplier": {"regular": 1.0, "beast": 0.9, "siege": 0.8, "mythic": 0.6},
        "per_unit_type": "lost = min(floor(deployed * rate * defender_mult * category_mult), deployed, owned_now); rate < 1 so at least one unit of every deployed type survives",
        "npc_and_empty_lanes": "NPC garrisons have no troops to lose; a player whose lane opponent is an empty lane ('Corsia vuota') fights nobody and loses nothing; a player facing an NPC garrison suffers normal losses",
        "application": "computed from the locked snapshot's deployed_army and the resolved lane; deducted ONCE per war and player (ledger key war_losses:<war_id>:<player_id>) from army.units; "
                       "the formation is clamped to the survivors; war snapshots are never modified. Losses are reported in war.result.casualties and in the alliance chat",
        "examples_note": "see rulebook chapter 11.3 for the worked examples (attacker/defender x winner/loser)",
    }
    # document ---------------------------------------------------------------------------------------------------
    c["document"]["version"] = "1.5"
    c["document"]["changelog_v1_5"] = [
        "Units: effective_unlock_castle_level (nominal castle gate vs research castle gate); all gates kept.",
        "Gear: rarity drop bands split at every unlock stage (1-9 / 10-24 / 25-49 ...); explicit drop_filter_rule with exceptions.",
        "Domain: 100 tiles, full at stage 200 (1 start tile + 1 at every even stage from 4 to 200).",
        "Rounding rules made explicit (document.rounding).",
        "Reforge: the retired affix is not protected; primary stats/rarity/item level/forge never change.",
        "Quests: Italian texts + alternatives when Forge / research (and buildings) are maxed.",
        "Alliance War: permanent casualties on both sides (alliance_war.casualties); PvE unchanged.",
    ]
    from app.core.canon import compute_spec_hash
    c["document"]["spec_hash"] = compute_spec_hash(c)
    json.dump(c, open(PATH, "w"), ensure_ascii=False, indent=2)
    json.dump(c, open(MIRROR, "w"), ensure_ascii=False, indent=2)
    cp = os.path.join(ROOT, "app", "core", "canon.py")
    s = open(cp).read()
    s = re.sub(r'REQUIRED_VERSION = "[0-9.]+"', 'REQUIRED_VERSION = "1.5"', s)
    s = re.sub(r'REQUIRED_SPEC_HASH = "[0-9a-f]+"', f'REQUIRED_SPEC_HASH = "{c["document"]["spec_hash"]}"', s)
    open(cp, "w").write(s)
    print("hash:", c["document"]["spec_hash"])
    for u in c["units"]["catalog"]:
        if u["effective_unlock_castle_level"] != u["unlock_castle_level"]:
            print(f"  {u['key']}: castello nominale {u['unlock_castle_level']} -> effettivo {u['effective_unlock_castle_level']} (ricerca {u['required_research']})")


if __name__ == "__main__":
    main()
