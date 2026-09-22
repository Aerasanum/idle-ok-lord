"""Canon v1.8 (idempotent): two more idle dungeons - Harvest Caverns (soft-resource haul scaling with the tier) and
Training Grounds (free troops of an unlocked unit chosen at entry) - plus Italian display strings for every dungeon."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PATH = os.path.join(ROOT, "canon", "IDLE_1_v1.1_CANONICAL_SPEC.json")
MIRROR = os.path.join(os.path.dirname(ROOT), "docs", "CANONICAL_SPEC.json")

NEW = [
    {
        "key": "harvest_caverns",
        "name": "Harvest Caverns",
        "reward": "Large soft-resource haul (no gold)",
        "formula": "soft resources = (1 + 0.5*tier) hours of current building production; no gold",
    },
    {
        "key": "training_grounds",
        "name": "Training Grounds",
        "reward": "Free troops of an unlocked unit chosen at entry",
        "formula": "free recruit minutes = 20*tier; quantity = max(1, floor(free recruit minutes / recruit_time_minutes_each(chosen unit)))",
    },
]

IT = {
    "treasury_vault": ("Tesoreria Reale", "Oro e risorse del regno"),
    "forge_depths": ("Profondità della Forgia", "Polvere da Forgia e Pietre di Riforgia"),
    "ancient_ruins": ("Rovine Antiche", "Un oggetto con tiro migliorato, Essenza Mitica ai tier alti"),
    "monster_hunt": ("Caccia ai Mostri", "XP dell'Eroe e Gettoni Evento"),
    "harvest_caverns": ("Caverne della Raccolta", "Grosso carico di grano, legno, argilla e ferro"),
    "training_grounds": ("Campo di Addestramento", "Truppe gratis dell'unità che scegli"),
}


def main() -> None:
    c = json.load(open(PATH))
    d = c["dungeons"]
    by_key = {x["key"]: x for x in d["catalog"]}
    order = [x["key"] for x in d["catalog"]] + [x["key"] for x in NEW if x["key"] not in by_key]
    for entry in NEW:
        by_key.setdefault(entry["key"], {}).update(entry)
    for key, (name_it, reward_it) in IT.items():
        by_key[key]["name_it"], by_key[key]["reward_it"] = name_it, reward_it
    d["catalog"] = [by_key[k] for k in order]
    d["soft_haul_hours"] = {"base": 1.0, "per_tier": 0.5}
    d["training_recruit_minutes_per_tier"] = 20
    d["training_rule"] = ("Training Grounds only grants units whose castle/research/campaign gates are already met, so it accelerates the army the player "
                          "could already build; the unit is chosen at entry, the quantity is fixed when the run starts and the troops cost no resources "
                          "and take no recruit queue slot. Gold is never paid by Harvest Caverns: that stays the Royal Treasury's reward.")
    c["document"]["version"] = "1.8"
    c["document"]["changelog_v1_8"] = [
        "Dungeons: six instead of four. Harvest Caverns pays (1 + 0.5*tier) hours of soft production; Training Grounds converts 20*tier recruit "
        "minutes into free troops of an unlocked unit chosen at entry.",
        "Dungeons: Italian display name and reward text per dungeon (name_it / reward_it), so the app no longer shows English names and raw formulas.",
    ]
    from app.core.canon import compute_spec_hash
    c["document"]["spec_hash"] = compute_spec_hash(c)
    json.dump(c, open(PATH, "w"), ensure_ascii=False, indent=2)
    json.dump(c, open(MIRROR, "w"), ensure_ascii=False, indent=2)
    cp = os.path.join(ROOT, "app", "core", "canon.py")
    s = open(cp).read()
    s = re.sub(r'REQUIRED_VERSION = "[0-9.]+"', 'REQUIRED_VERSION = "1.8"', s)
    s = re.sub(r'REQUIRED_SPEC_HASH = "[0-9a-f]+"', f'REQUIRED_SPEC_HASH = "{c["document"]["spec_hash"]}"', s)
    open(cp, "w").write(s)
    print("hash:", c["document"]["spec_hash"])


if __name__ == "__main__":
    main()
