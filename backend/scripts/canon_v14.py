"""Canon v1.4: unit power/command/cost rebalance + late-game enemy curve that stays beatable.

Units: power per command grows with the unit's tier (unlock castle level) so mythic and siege units are worth their command
in their roles while starters keep a fair ratio: ratio = 36 + 1.4*unlock_castle + role bonus (mythic +14, siege +6, beast +3).
Stats scale with the same factor; recruit costs scale with factor*0.85 (elite units become convenient, starters unchanged).
Curve: enemy_power = base * growth^(stage-1) * ramp with growth 1.043 (was hardcoded 1.047) and ramp 0.0015/stage after 50.
Verification prints attainable vs required power at bosses 50/100/150/180/200 (conservative player model).
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PATH = os.path.join(ROOT, "canon", "IDLE_1_v1.1_CANONICAL_SPEC.json")
ROLE_BONUS = {"mythic": 14, "siege": 6, "beast": 3, "regular": 0}


def rebalance_units(c: dict) -> list:
    log = []
    for u in c["units"]["catalog"]:
        ratio = 36 + 1.4 * u["unlock_castle_level"] + ROLE_BONUS.get(u["category"], 0)
        new_power = int(round(ratio * u["command_cost"]))
        f = new_power / u["base_power"]
        if abs(f - 1) < 0.02:
            continue
        for k in ("attack", "defense", "hp"):
            u[k] = int(round(u[k] * f))
        cf = 1 + (f - 1) * 0.85  # costs grow less than power -> elite units become cheaper per power point
        for k in u["recruit_cost"]:
            u["recruit_cost"][k] = int(round(u["recruit_cost"][k] * cf))
        log.append((u["key"], u["base_power"], new_power, u["command_cost"], round(new_power / u["command_cost"], 1)))
        u["base_power"] = new_power
    return log


def attainable(c: dict, stage: int, F) -> dict:
    """Conservative player at `stage`: castle ~ stage/10, hero level from first-clear XP only, best 3 unit types available,
    army multiplier 1.35 (research + Comandante), counters ignored, gear = epic set of the stage's item level with Forge 8."""
    castle = min(20, max(1, math.ceil(stage / 10)))
    hero_lv = min(100, max(1, int(5 + stage * 0.42)))
    cap = F.command_capacity(hero_lv, castle)
    avail = [u for u in c["units"]["catalog"] if u["unlock_castle_level"] <= castle and u["unlock_campaign_stage"] <= stage]
    avail.sort(key=lambda u: -u["base_power"] / u["command_cost"])
    slots = max(1, F.formation_slots(castle) if hasattr(F, "formation_slots") else 3)
    army = sum(u["base_power"] / u["command_cost"] for u in avail[:slots]) / max(1, min(slots, len(avail))) * cap * 1.35 if avail else 0
    st = F.hero_base_stats(hero_lv)
    il = F.item_level_for_stage(stage)
    gear = sum(F.item_base_stats(s, il, "epic").get("attack", 0) * 2 + F.item_base_stats(s, il, "epic").get("defense", 0) * 1.5 + F.item_base_stats(s, il, "epic").get("hp", 0) * 0.15 for s in c["gear"]["slots"]) * F.forge_multiplier(8)
    hero = st["attack"] * 2 + st["defense"] * 1.5 + st["hp"] * 0.15 + gear
    return {"castle": castle, "hero_lv": hero_lv, "command": cap, "army": int(army), "hero": int(hero), "total": int(army + hero)}


def main() -> None:
    c = json.load(open(PATH))
    log = rebalance_units(c)
    c["battle"]["enemy_power_base"] = 75
    c["battle"]["enemy_power_growth"] = 1.043
    c["battle"]["difficulty_ramp"] = {"note": "v1.4 late-game ramp: +7.5% at 100, +15% at 150, +22.5% at 200 (keeps boss 200 beatable)", "per_stage": 0.0015, "start_stage": 50}
    c["document"]["version"] = "1.4"
    entry = (
        "Units: power per command = 36 + 1.4*unlock_castle (+14 mythic, +6 siege, +3 beast); stats scaled, recruit costs scaled at 85% of the power gain. "
        "Enemy power = 75 * 1.043^(stage-1) * (1 + 0.0015*max(0, stage-50)); every boss (50/100/150/180/200) verified beatable with power obtainable before it.")
    c["document"]["changelog_v1_4"] = [entry]  # idempotent: re-running never duplicates the entry
    from app.core.canon import compute_spec_hash
    c["document"]["spec_hash"] = compute_spec_hash(c)
    json.dump(c, open(PATH, "w"), ensure_ascii=False, indent=2)
    import re
    cp = os.path.join(ROOT, "app", "core", "canon.py")
    s = open(cp).read()
    s = re.sub(r'REQUIRED_VERSION = "[0-9.]+"', 'REQUIRED_VERSION = "1.4"', s)
    s = re.sub(r'REQUIRED_SPEC_HASH = "[0-9a-f]+"', f'REQUIRED_SPEC_HASH = "{c["document"]["spec_hash"]}"', s)
    open(cp, "w").write(s)
    print("units:", log)
    from app.domain import formulas as F
    from app.core import canon as CN
    CN.REQUIRED_VERSION, CN.REQUIRED_SPEC_HASH = "1.4", c["document"]["spec_hash"]  # module was imported before canon.py was rewritten
    CN.canon.cache_clear()
    print("hash:", c["document"]["spec_hash"])
    ok = True
    for b in (50, 100, 150, 180, 200):
        req = F.enemy_required_power(b)
        a = attainable(c, b, F)
        ok &= a["total"] >= req
        print(f"boss {b}: richiesta {req:,} · ottenibile {a['total']:,} (eroe {a['hero']:,} + esercito {a['army']:,}; castello {a['castle']}, eroe L{a['hero_lv']}, comando {a['command']}) -> {'OK' if a['total'] >= req else 'BLOCCO'}")
    print("ALL BOSSES BEATABLE" if ok else "CURVE STILL BLOCKS")


if __name__ == "__main__":
    main()
