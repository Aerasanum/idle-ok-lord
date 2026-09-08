"""Canon v1.7 (idempotent): alliance roles = 1 leader + max 2 officers (only these 3 can declare war / manage rosters);
alliance rename rule (leader only, 7-day cooldown); neutral garrison power made explicit."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PATH = os.path.join(ROOT, "canon", "IDLE_1_v1.1_CANONICAL_SPEC.json")
MIRROR = os.path.join(os.path.dirname(ROOT), "docs", "CANONICAL_SPEC.json")


def main() -> None:
    c = json.load(open(PATH))
    al = c["alliances"]
    al["roles"] = {"leader": 1, "officers_max": 2, "member": al["member_cap"] - 3}
    al["war_powers"] = "only the leader and the (max 2) officers can declare war, edit the war roster, change settings and manage members; every member can enlist"
    al["rename"] = {"who": "leader only", "cooldown_days": 7, "name_rule": "3-20 chars, letters/digits/space/-/', unique among active alliances", "tag": "fixed at creation"}
    c["alliance_war"]["underfilled_defense_npc_fill"]["neutral_garrison"] = (
        "a node without an owner is defended by 10 NPC 'Garrison' lanes, each with war_power = round(70% of the ATTACKING alliance's median member war power): "
        "the garrison scales with the attacker so it is never trivial nor impossible; it is shown in the node sheet before declaring (attack_state.garrison_lane_power)")
    c["document"]["version"] = "1.7"
    c["document"]["changelog_v1_7"] = ["Alliances: 1 leader + max 2 officers hold war powers; rename (leader, 7-day cooldown); neutral garrison power documented and shown in-app."]
    from app.core.canon import compute_spec_hash
    c["document"]["spec_hash"] = compute_spec_hash(c)
    json.dump(c, open(PATH, "w"), ensure_ascii=False, indent=2)
    json.dump(c, open(MIRROR, "w"), ensure_ascii=False, indent=2)
    cp = os.path.join(ROOT, "app", "core", "canon.py")
    s = open(cp).read()
    s = re.sub(r'REQUIRED_VERSION = "[0-9.]+"', 'REQUIRED_VERSION = "1.7"', s)
    s = re.sub(r'REQUIRED_SPEC_HASH = "[0-9a-f]+"', f'REQUIRED_SPEC_HASH = "{c["document"]["spec_hash"]}"', s)
    open(cp, "w").write(s)
    print("hash:", c["document"]["spec_hash"])


if __name__ == "__main__":
    main()
