"""Canonical v1.2 live update (owner-approved, June 2026): unit counters, late-game difficulty ramp, siege wagon rename.

Statistics of all 13 units are unchanged. Applies the changes to backend/canon/IDLE_1_v1.1_CANONICAL_SPEC.json (kept at the same
path — settings.CANON_PATH), recomputes document.spec_hash with app.core.canon.compute_spec_hash and mirrors docs/CANONICAL_SPEC.json.
Idempotent: re-running produces the same file.

Usage: python scripts/canon_v12.py
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.core.canon import compute_spec_hash  # noqa: E402

CANON = BACKEND / "canon" / "IDLE_1_v1.1_CANONICAL_SPEC.json"
DOCS = BACKEND.parent / "docs" / "CANONICAL_SPEC.json"

ENEMY_CLASSES = {
    # Umanoidi
    "Goblin Raider": "umanoidi", "Road Bandit": "umanoidi", "Cultist": "umanoidi", "Orc Reaver": "umanoidi", "Ash Raider": "umanoidi",
    "North Raider": "umanoidi", "Desert Marauder": "umanoidi", "Dragon Cultist": "umanoidi",
    # Bestie
    "Wild Boar": "bestie", "Marsh Wolf": "bestie", "Dark Wolf": "bestie", "Giant Spider": "bestie", "Warg": "bestie", "Frost Wolf": "bestie",
    "Giant Scorpion": "bestie", "World Beast": "bestie",
    # Giganti
    "Ogre Warlord": "giganti", "Forest Troll": "giganti", "Ancient Treant": "giganti", "Mountain Tyrant": "giganti", "Ice Troll": "giganti",
    "Ice Giant King": "giganti", "Sea Troll": "giganti", "Ancient Titan": "giganti",
    # Corazzati
    "Armored Ogre": "corazzati", "Stone Golem": "corazzati", "Sand Golem": "corazzati", "Magma Golem": "corazzati", "Celestial Construct": "corazzati",
    "Fallen Knight": "corazzati",
    # Volanti
    "Harpy": "volanti", "Winged Horror": "volanti", "Wyvern": "volanti", "Fallen Seraph": "volanti",
    # Spiriti / non-morti
    "Undead Legionary": "spiriti", "Fire Imp": "spiriti", "Bone Colossus": "spiriti", "Frost Wraith": "spiriti", "Djinn Acolyte": "spiriti",
    "Drowned Soldier": "spiriti", "Siren": "spiriti", "Infernal Herald": "spiriti", "Demon Legionary": "spiriti",
    # Draghi
    "Drake": "draghi", "Sand Wyrm": "draghi", "Leviathan Spawn": "draghi", "Leviathan": "draghi", "Elder Dragon": "draghi", "Abyss Wyrm": "draghi",
    "World Devourer": "draghi",
}
CLASS_LABEL = {"umanoidi": "Umanoidi", "bestie": "Bestie", "giganti": "Giganti", "corazzati": "Corazzati", "volanti": "Volanti", "spiriti": "Spiriti", "draghi": "Draghi"}
UNIT_CLASS = {"infantry": "umanoidi", "archer": "umanoidi", "cavalry": "bestie", "catapult": "corazzati", "conquest_wagon": "corazzati", "bear": "bestie", "wolf": "bestie",
              "lion": "bestie", "falcon": "volanti", "war_elephant": "bestie", "dragon": "draghi", "angel": "volanti", "demon": "spiriti"}
TABLE = {
    "infantry": (["bestie", "giganti"], ["volanti", "spiriti"]),
    "archer": (["volanti", "umanoidi"], ["corazzati", "bestie"]),
    "cavalry": (["umanoidi", "spiriti"], ["corazzati", "giganti"]),
    "catapult": (["corazzati", "giganti"], ["volanti", "bestie"]),
    "conquest_wagon": (["umanoidi", "corazzati"], ["volanti", "spiriti"]),
    "bear": (["umanoidi", "corazzati"], ["volanti", "draghi"]),
    "wolf": (["bestie", "umanoidi"], ["corazzati", "giganti"]),
    "lion": (["bestie", "spiriti"], ["corazzati", "volanti"]),
    "falcon": (["volanti", "umanoidi"], ["corazzati", "draghi"]),
    "war_elephant": (["corazzati", "giganti"], ["spiriti", "volanti"]),
    "dragon": (["umanoidi", "bestie", "corazzati", "giganti"], ["spiriti"]),
    "angel": (["spiriti", "draghi", "volanti", "umanoidi"], ["corazzati"]),
    "demon": (["umanoidi", "bestie", "giganti", "spiriti"], ["draghi"]),
}


def main():
    data = json.load(open(CANON, encoding="utf-8"))
    families = {f for r in data["battle"]["regions"] for f in r["enemy_families"]} | {r["region_boss"] for r in data["battle"]["regions"]}
    missing = families - set(ENEMY_CLASSES)
    assert not missing, f"unclassified enemy families: {missing}"
    for u in data["units"]["catalog"]:
        if u["key"] == "conquest_wagon":
            u["name"] = "Ariete d'Assedio"
            u["rename_note"] = "v1.2: renamed from 'Carro di Conquista' (does not conquer domain tiles); key unchanged"
    data["units"]["counters"] = {
        "bonus_pct": 30, "malus_pct": 20,
        "class_labels": CLASS_LABEL,
        "unit_class": UNIT_CLASS,
        "table": {k: {"strong_vs": s, "weak_vs": w} for k, (s, w) in TABLE.items()},
        "pve_rule": "unit_power *= 1 + sum(mix_share[class] * (bonus_pct if class in strong_vs else -malus_pct if class in weak_vs else 0))/100; mix = stage enemy classes",
        "pve_stage_mix": {"normal_elite": "region enemy_families, equal shares", "boss": {"boss_class": 0.5, "families": 0.5}},
        "war_rule": "per lane, each side's per-unit army power is multiplied against the opponent's deployed army class mix (share = command_cost*quantity); NPC defenders are neutral",
    }
    data["battle"]["enemy_classes"] = ENEMY_CLASSES
    data["battle"]["enemy_power_formula"] = "round(75 * 1.047^(stage-1) * (1 + 0.004*max(0, stage-50)))"
    data["battle"]["difficulty_ramp"] = {"start_stage": 50, "per_stage": 0.004, "note": "v1.2 progressive late-game difficulty: +20% at 100, +40% at 150, +60% at 200"}
    doc = data["document"]
    doc["version"] = "1.2"
    doc["status"] = "LIVE_UPDATE_v1.2"
    doc["balance_status"] = "v1.2 live update (owner-approved): unit counters, late-game difficulty ramp, siege wagon rename; unit statistics unchanged from v1.1"
    doc["changelog_v1_2"] = [
        "units.counters: strong_vs (+30%) / weak_vs (-20%) per unit against 7 enemy classes (PvE stage mix, war lane opponent mix)",
        "battle.enemy_classes: class of every enemy family and region boss",
        "battle.enemy_power_formula: multiplied by difficulty ramp 1 + 0.004*max(0, stage-50)",
        "units.catalog[conquest_wagon].name: 'Ariete d'Assedio'",
    ]
    doc["spec_hash"] = compute_spec_hash(data)
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    CANON.write_text(text, encoding="utf-8")
    DOCS.write_text(text, encoding="utf-8")
    print("spec_hash:", doc["spec_hash"])


if __name__ == "__main__":
    main()
