"""Update-op builder + quest/codex/stat progression hooks merged into atomic player updates."""
from ..core.canon import canon
from ..core.util import day_key, week_key


class Ops:
    def __init__(self):
        self.sets, self.incs, self.add_to_set, self.pushes, self.unsets = {}, {}, {}, {}, {}

    def set(self, k, v):
        self.sets[k] = v
        return self

    def inc(self, k, v):
        if v:
            self.incs[k] = self.incs.get(k, 0) + v
        return self

    def add(self, k, v):
        self.add_to_set.setdefault(k, {"$each": []})["$each"].append(v)
        return self

    def push(self, k, v, slice_=None):
        entry = self.pushes.setdefault(k, {"$each": []})
        entry["$each"].append(v)
        if slice_:
            entry["$slice"] = slice_
        return self

    def unset(self, k):
        self.unsets[k] = ""
        return self

    def merge(self, other: "Ops"):
        self.sets.update(other.sets)
        for k, v in other.incs.items():
            self.inc(k, v)
        for k, v in other.add_to_set.items():
            self.add_to_set.setdefault(k, {"$each": []})["$each"].extend(v["$each"])
        for k, v in other.pushes.items():
            e = self.pushes.setdefault(k, {"$each": []})
            e["$each"].extend(v["$each"])
            if "$slice" in v:
                e["$slice"] = v["$slice"]
        self.unsets.update(other.unsets)
        return self

    def build(self) -> dict:
        u = {}
        if self.sets:
            u["$set"] = dict(self.sets)
        if self.incs:
            u["$inc"] = dict(self.incs)
        if self.add_to_set:
            u["$addToSet"] = dict(self.add_to_set)
        if self.pushes:
            u["$push"] = dict(self.pushes)
        if self.unsets:
            u["$unset"] = dict(self.unsets)
        return u


def resources_inc(ops: Ops, res: dict):
    for k, v in res.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                ops.inc(f"resources.{kk}", int(vv))
        elif v:
            ops.inc(f"resources.{k}", int(v))
    return ops


# ---- quests -------------------------------------------------------------------------------------------
def _fresh_daily(day: str) -> dict:
    return {"day": day, "progress": {}, "chests_claimed": []}


def _fresh_weekly(week: str) -> dict:
    return {"week": week, "progress": {}, "chests_claimed": []}


def quest_progress(ops: Ops, p: dict, daily_key: str | None = None, weekly_key: str | None = None, amount: float = 1):
    """Increment quest counters; rolls over day/week if needed. Season points are granted when quest points are earned."""
    q = p.get("quests") or {}
    today, week = day_key(), week_key()
    daily = q.get("daily")
    if daily_key:
        if not daily or daily.get("day") != today:
            d = _fresh_daily(today)
            d["progress"][daily_key] = amount
            ops.set("quests.daily", d)
        else:
            ops.inc(f"quests.daily.progress.{daily_key}", amount)
    weekly = q.get("weekly")
    if weekly_key:
        if not weekly or weekly.get("week") != week:
            w = _fresh_weekly(week)
            w["progress"][weekly_key] = amount
            ops.set("quests.weekly", w)
        else:
            ops.inc(f"quests.weekly.progress.{weekly_key}", amount)
    return ops


def quest_points(kind: str, p: dict) -> tuple[int, dict]:
    q = (p.get("quests") or {}).get(kind) or {}
    cur = day_key() if kind == "daily" else week_key()
    if q.get("day" if kind == "daily" else "week") != cur:
        q = {"progress": {}, "chests_claimed": []}
    templates = canon()["quests"][kind]["templates"]
    alts = quest_alternatives(p)
    pts = 0
    detail = {}
    for t in templates:
        prog = q.get("progress", {}).get(t["key"], 0)
        done = prog >= t["target"]
        pts += t["points"] if done else 0
        alt = alts.get(t["key"])
        detail[t["key"]] = {"progress": min(prog, t["target"]), "target": t["target"], "points": t["points"], "done": done,
                            "text": alt["text"] if alt else t.get("text", t["key"]), "alt_active": bool(alt), "alt_when": alt["when"] if alt else None}
    return pts, {"tasks": detail, "chests_claimed": q.get("chests_claimed", [])}


# ---- quest alternatives (canon v1.5 quests.fallback_rule) ---------------------------------------------------
def forge_all_max(p: dict) -> bool:
    g = canon()["gear"]
    return all(p.get("forge", {}).get(s, 0) >= g["forge"]["max_level_per_slot"] for s in g["slots"])


def research_all_max(p: dict) -> bool:
    return all(p.get("research", {}).get(n["key"], 0) >= n["max_level"] for n in canon()["research"]["nodes"])


def buildings_all_max(p: dict) -> bool:
    b = p.get("kingdom", {}).get("buildings", {})
    return all(b.get(x["key"], 0) >= x["max_level"] for x in canon()["buildings"])


def _condition(when: str, p: dict) -> bool:
    if when == "all_forge_slots_at_max":
        return forge_all_max(p)
    if when == "all_research_at_max":
        return research_all_max(p)
    if when == "all_research_and_buildings_at_max":
        return research_all_max(p) and buildings_all_max(p)
    return False


def quest_alternatives(p: dict) -> dict:
    """template key -> active alternative ({when, text, counts}) when the base objective is permanently impossible; last matching wins."""
    out = {}
    for kind in ("daily", "weekly"):
        for t in canon()["quests"][kind]["templates"]:
            for alt in t.get("alternatives", []):
                if _condition(alt["when"], p):
                    out[t["key"]] = alt
    return out


def alt_quest_progress(ops: Ops, p: dict, when: str, amount: float = 1) -> Ops:
    """Credit every task whose active alternative is `when` (e.g. a reforge counts as a forge upgrade when the Forge is maxed)."""
    for kind, key_field in (("daily", "daily_key"), ("weekly", "weekly_key")):
        for t in canon()["quests"][kind]["templates"]:
            alts = t.get("alternatives", [])
            active = next((a for a in reversed(alts) if _condition(a["when"], p)), None)
            if active and active["when"] == when:
                quest_progress(ops, p, **{key_field: t["key"]}, amount=amount)
    return ops


# ---- codex / stats ------------------------------------------------------------------------------------
def codex_add(ops: Ops, track: str, entry: str):
    return ops.add(f"codex.{track}", entry)


def codex_totals() -> dict:
    c = canon()
    return {
        "regions": [r["name"] for r in c["battle"]["regions"]],
        "monster_families": [f for r in c["battle"]["regions"] for f in r["enemy_families"]],
        "bosses": [r["region_boss"] for r in c["battle"]["regions"]],
        "units": [u["key"] for u in c["units"]["catalog"]],
        "gear_rarities": list(c["gear"]["rarity_order"]),
    }


def codex_completion_pct(p: dict) -> float:
    totals = codex_totals()
    total = sum(len(v) for v in totals.values())
    have = sum(len(set(p.get("codex", {}).get(k, [])) & set(v)) for k, v in totals.items())
    return round(100 * have / total, 2)


def achievement_metrics(p: dict) -> dict:
    s = p.get("stats", {})
    return {
        "campaign_stage_reached": p["campaign"]["highest_cleared"],
        "hero_level_reached": p["hero"]["level"],
        "legendary_or_higher_items_found": s.get("legendary_or_higher_items_found", 0),
        "castle_level_reached": p["kingdom"]["castle_level"],
        "units_recruited_total": s.get("units_recruited_total", 0),
        "domain_tiles_owned": p["domain"]["owned"],
        "event_deployments_completed": s.get("event_deployments_completed", 0),
        "alliance_war_lanes_or_boss_attacks": s.get("alliance_war_lanes_or_boss_attacks", 0),
    }
