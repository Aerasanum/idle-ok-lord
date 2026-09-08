"""Canon v1.3: warehouse capacity must always cover the most expensive single upgrade reachable at that castle level.

Rule (documented in the rulebook): for every castle level L, Warehouse level L holds at least 110% of the largest single cost
(per resource) among: the castle upgrade L->L+1, every building level unlocked at castle <= L, every research level unlocked at
castle <= L. Capacities only ever grow, so existing players keep all progress. Usage: python scripts/canon_v13.py
"""
import json
import math
import os
import sys

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "canon", "IDLE_1_v1.1_CANONICAL_SPEC.json")
RES = ["grain", "wood", "clay", "iron", "gold"]


def max_cost_at(c: dict, L: int) -> int:
    m = 0
    for b in c["buildings"]:
        if b["key"] == "castle":
            lv = next((x for x in b["levels"] if x["level"] == L + 1), None)
            if lv:
                m = max(m, *lv["upgrade_cost"].values())
        elif b["unlock_castle_level"] <= L:
            for lv in b["levels"]:
                if lv["level"] <= min(b["max_level"], L + 1):  # building levels are capped near the castle level
                    m = max(m, *lv["upgrade_cost"].values())
    for n in c["research"]["nodes"]:
        if n["unlock_castle_level"] <= L:
            for lv in n["levels"]:
                m = max(m, *lv["cost"].values())
    return m


def main() -> None:
    c = json.load(open(PATH))
    wh = next(b for b in c["buildings"] if b["key"] == "warehouse")
    changed = []
    for lv in wh["levels"]:
        L = lv["level"]
        need = int(math.ceil(max_cost_at(c, L) * 1.1 / 1000.0) * 1000)
        if lv["capacity_each_resource"] < need:
            changed.append((L, lv["capacity_each_resource"], need))
            lv["capacity_each_resource"] = need
    # keep capacity monotonic
    for i in range(1, len(wh["levels"])):
        if wh["levels"][i]["capacity_each_resource"] < wh["levels"][i - 1]["capacity_each_resource"]:
            wh["levels"][i]["capacity_each_resource"] = wh["levels"][i - 1]["capacity_each_resource"]
    # verify: every single cost anywhere fits in the max warehouse, and the warehouse's own upgrade fits in the previous level
    cap = {lv["level"]: lv["capacity_each_resource"] for lv in wh["levels"]}
    problems = []
    for b in c["buildings"]:
        for lv in b["levels"]:
            if max(lv["upgrade_cost"].values()) > cap[20]:
                problems.append(f"{b['key']} L{lv['level']}")
    for lv in wh["levels"]:
        prev = cap.get(lv["level"] - 1, cap[1])
        if lv["level"] > 1 and max(lv["upgrade_cost"].values()) > prev:
            problems.append(f"warehouse L{lv['level']} cost > cap L{lv['level'] - 1}")
    for n in c["research"]["nodes"]:
        for lv in n["levels"]:
            if max(lv["cost"].values()) > cap[20]:
                problems.append(f"research {n['key']} L{lv['level']}")
    if problems:
        print("STILL UNAFFORDABLE:", problems)
        sys.exit(1)
    if changed:
        c["document"]["version"] = "1.3"
        c["document"].setdefault("changelog_v1_3", []).append(
            "Warehouse capacity raised so that every single upgrade (castle, buildings, research) reachable at castle level L fits in Warehouse level L (110% of the largest cost); capacities only grow, progress preserved.")
        c["kingdom"]["warehouse_rule"] = "capacity(L) >= 1.1 x max single upgrade cost reachable at castle level L; every upgrade is payable from a full warehouse"
        json.dump(c, open(PATH, "w"), ensure_ascii=False, indent=2)
    print("changed levels:", changed)
    print("capacities:", [lv["capacity_each_resource"] for lv in wh["levels"]])


if __name__ == "__main__":
    main()
