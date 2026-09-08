"""Canon v1.6 (idempotent): Infirmary — 40% of the troops lost in an Alliance War return after 8 hours."""
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
    c["alliance_war"]["casualties"]["infirmary"] = {
        "return_pct": 40,
        "hours": 8,
        "rule": "per unit type: returned = floor(lost * 0.40); the survivors are credited automatically 8 hours after the war resolves (lazy settlement on the next load), "
                "the formation is not changed. Applied per war and player; recorded in army.infirmary. The other 60% is lost for good",
    }
    c["alliance_war"]["casualties"]["application"] += ". Infirmary: 40% of the fallen return after 8h (alliance_war.casualties.infirmary)"
    c["document"]["version"] = "1.6"
    c["document"]["changelog_v1_6"] = ["Alliance War: Infirmary returns 40% of the fallen troops 8 hours after the war (net permanent loss = 60% of the casualties)."]
    from app.core.canon import compute_spec_hash
    c["document"]["spec_hash"] = compute_spec_hash(c)
    json.dump(c, open(PATH, "w"), ensure_ascii=False, indent=2)
    json.dump(c, open(MIRROR, "w"), ensure_ascii=False, indent=2)
    cp = os.path.join(ROOT, "app", "core", "canon.py")
    s = open(cp).read()
    s = re.sub(r'REQUIRED_VERSION = "[0-9.]+"', 'REQUIRED_VERSION = "1.6"', s)
    s = re.sub(r'REQUIRED_SPEC_HASH = "[0-9a-f]+"', f'REQUIRED_SPEC_HASH = "{c["document"]["spec_hash"]}"', s)
    open(cp, "w").write(s)
    print("hash:", c["document"]["spec_hash"])


if __name__ == "__main__":
    main()
