"""Canonical runtime loader (I02). Every runtime number is read from the CANONICAL_SPEC (v1.1 frozen baseline + v1.2 live update)."""
import hashlib
import json
import math
from functools import lru_cache

from .config import settings

REQUIRED_VERSION = "1.9"
REQUIRED_SPEC_HASH = "4943e39ef55793705ef711cf4623199c0afcd8a35b5d93d7bdfea6d6d9dc9217"


class CanonError(RuntimeError):
    pass


def compute_spec_hash(data: dict) -> str:
    """sha256 of the canonical JSON with document.spec_hash blanked (sorted keys, compact separators, UTF-8)."""
    d = json.loads(json.dumps(data))
    d["document"]["spec_hash"] = ""
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _load() -> dict:
    with open(settings.CANON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    doc = data.get("document", {})
    if doc.get("version") != REQUIRED_VERSION:
        raise CanonError(f"Canonical version mismatch: {doc.get('version')}")
    if doc.get("spec_hash") != REQUIRED_SPEC_HASH or compute_spec_hash(data) != REQUIRED_SPEC_HASH:
        raise CanonError("Canonical spec_hash mismatch")
    checks = {
        "GEAR_SLOTS": (len(data["gear"]["slots"]), 9),
        "CAMPAIGN_STAGES": (data["battle"]["campaign_stages"], 200),
        "CAMPAIGN_REGIONS": (len(data["battle"]["regions"]), 10),
        "RESEARCH_NODES": (len(data["research"]["nodes"]), 48),
        "UNITS": (len(data["units"]["catalog"]), 13),
        "CASTLE_LEVELS": (len(data["kingdom"]["castle_levels"]), 20),
        "ARMY_VISUAL_MAX_TIER": (max(t["tier"] for t in data["army_visual_progression"]["tiers"]), 8),
        "ALLIANCE_WAR": (data["alliance_war"]["mode"], "asynchronous_10v10"),
    }
    for k, (got, exp) in checks.items():
        if got != exp:
            raise CanonError(f"Canonical check failed {k}: {got} != {exp}")
    return data


@lru_cache(maxsize=1)
def canon() -> dict:
    return _load()


def validation_report() -> dict:
    c = canon()
    return {
        "CANONICAL_SPEC_PARSED": "YES",
        "VERSION": c["document"]["version"],
        "SPEC_HASH": c["document"]["spec_hash"],
        "GEAR_SLOTS": len(c["gear"]["slots"]),
        "CAMPAIGN_STAGES": c["battle"]["campaign_stages"],
        "CAMPAIGN_REGIONS": len(c["battle"]["regions"]),
        "RESEARCH_NODES": len(c["research"]["nodes"]),
        "UNITS": len(c["units"]["catalog"]),
        "CASTLE_LEVELS": len(c["kingdom"]["castle_levels"]),
        "ARMY_VISUAL_MAX_TIER": max(t["tier"] for t in c["army_visual_progression"]["tiers"]),
        "ALLIANCE_WAR": "ASYNC_10V10",
    }


# ---- typed accessors -------------------------------------------------------
def units_by_key() -> dict:
    return {u["key"]: u for u in canon()["units"]["catalog"]}


def buildings_by_key() -> dict:
    return {b["key"]: b for b in canon()["buildings"]}


def research_by_key() -> dict:
    return {n["key"]: n for n in canon()["research"]["nodes"]}


def region_for_stage(stage: int) -> dict:
    for r in canon()["battle"]["regions"]:
        if r["stage_start"] <= stage <= r["stage_end"]:
            return r
    raise CanonError(f"No region for stage {stage}")


def castle_level_row(level: int) -> dict:
    return canon()["kingdom"]["castle_levels"][level - 1]


def kingdom_visual_tier(castle_level: int) -> dict:
    row = castle_level_row(castle_level)
    for t in canon()["kingdom"]["visual_tiers"]:
        if t["tier"] == row["visual_tier"]:
            return t
    raise CanonError("visual tier missing")


def army_visual_tier(stage: int, army_deployed: bool) -> dict:
    tiers = canon()["army_visual_progression"]["tiers"]
    chosen = tiers[0]
    for t in tiers:
        trig = t["trigger"]
        if trig == "stage < 10":
            continue
        need_army = "army deployed" in trig
        threshold = int(trig.split(">=")[1].split()[0])
        if stage >= threshold and (not need_army or army_deployed):
            chosen = t
    if chosen["tier"] >= 1 and not army_deployed and stage >= 10:
        # tiers above 1 still require an army to show; without army the Lord fights alone
        return tiers[0]
    return chosen


def stage_drop_weights(stage: int) -> dict:
    for band in canon()["gear"]["stage_drop_weights"]:
        a, b = band["stages"].split("-")
        if int(a) <= stage <= int(b):
            return band["weights_pct"]
    raise CanonError(f"No drop band for stage {stage}")


def support_formation_slots(castle_level: int) -> int:
    slots = 0
    for row in canon()["kingdom"]["support_formation_slots_by_castle_level"]:
        if castle_level >= row["castle_level"]:
            slots = row["slots"]
    return slots


def ceil(x: float) -> int:
    return int(math.ceil(x))
