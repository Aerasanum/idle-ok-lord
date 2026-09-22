"""LiveOps (I11): weekly event + energy + track, six idle dungeons, daily/weekly quests, login calendar,
achievements, codex, season pass. Derived distributions are marked DERIVED in the traceability matrix."""
from datetime import datetime, timedelta, timezone

from ..core import db, ledger
from ..core.canon import canon
from ..core.util import aware, clean, day_key, fail, new_id, now, rnd, seeded_rng, week_key, week_start
from . import formulas as F
from .gear import materialize_items, roll_rarity
from .hero import apply_xp
from .kingdom import unit_gates
from .player import production_per_hour, research_pct
from .progress import Ops, achievement_metrics, codex_completion_pct, codex_totals, quest_points, quest_progress, resources_inc

EPOCH_MONDAY = datetime(2026, 1, 5, tzinfo=timezone.utc)
LOGIN_RUBIES = [3, 3, 4, 4, 5, 6, 10]  # DERIVED: sums to canonical 35/cycle; day 7 = 10 Rubies + boosted gear roll


# ---- weekly event ----------------------------------------------------------------------------------------
def current_event() -> dict:
    ev = canon()["events"]
    start = week_start()
    idx = ((start - EPOCH_MONDAY).days // 7) % len(ev["archetypes"])
    return {"key": start.strftime("%Y-%m-%d"), "archetype": ev["archetypes"][idx], "archetype_index": idx, "starts_at": start.isoformat(), "ends_at": (start + timedelta(days=ev["cycle_days"])).isoformat()}


def energy_now(p: dict) -> tuple[int, datetime]:
    ev = canon()["events"]["energy"]
    e = p["events"]
    cur, at = e.get("energy", ev["max"]), aware(e.get("energy_at")) or now()
    if cur >= ev["max"]:
        return cur, now()
    ticks = int((now() - at).total_seconds() // (ev["regen_minutes_per_point"] * 60))
    if ticks <= 0:
        return cur, at
    new = min(ev["max"], cur + ticks)
    return new, at + timedelta(minutes=ticks * ev["regen_minutes_per_point"]) if new < ev["max"] else now()


def _track_rewards(tier: int, highest_stage: int) -> dict:
    """DERIVED per-tier amounts from canonical patterns/totals (free 40 Rubies, premium +80 Rubies, milestone gear)."""
    et = canon()["events"]["event_track"]
    base = F.event_deploy_rewards(max(1, highest_stage), 1.0)
    free, prem = {}, {}
    if tier % 5 == 0:
        free["rubies"] = et["free_rubies_total_if_completed"] // (et["tiers"] // 5)
        prem["rubies"] = et["premium_bonus_rubies_total_if_completed"] // (et["tiers"] // 5)
        prem["gear_min_rarity"] = et["premium_guaranteed_gear_milestones"].get(str(tier))
    elif tier % 2 == 1:
        free["gold"] = base["gold"] * 2
        free["soft_hours"] = 0.5
    else:
        free["forge_dust"] = 30 + tier * 3
    prem["forge_dust"] = 25 + tier * 2
    if tier % 2 == 0:
        prem["reforge_stone"] = 1
    return {"free": free, "premium": prem}


async def event_view(p: dict) -> dict:
    ev = canon()["events"]
    cur = current_event()
    e = p["events"]
    energy, _ = energy_now(p)
    reset = e.get("event_key") != cur["key"]
    points = 0 if reset else e.get("track_points", 0)
    tier_reached = min(ev["event_track"]["tiers"], points // ev["event_track"]["points_per_tier"])
    deployments = await db.event_deployments.find({"player_id": p["_id"], "status": {"$in": ["running", "done"]}}).to_list(10)
    ent = await db.entitlements.find_one({"player_id": p["_id"], "entitlement": "event_pass"})
    pass_active = bool(ent and aware(ent.get("expires_at")) and aware(ent["expires_at"]) > now())
    today = day_key()
    return {
        "event": cur, "energy": energy, "energy_max": ev["energy"]["max"], "regen_minutes": ev["energy"]["regen_minutes_per_point"],
        "deployments_catalog": ev["deployments"], "refill": ev["energy_refill"], "paid_refills_today": (e.get("paid_refills") or {}).get(today, 0),
        "track": {"points": points, "points_per_tier": ev["event_track"]["points_per_tier"], "tiers": ev["event_track"]["tiers"], "tier_reached": tier_reached,
                  "claimed_free": [] if reset else e.get("claimed_free", []), "claimed_premium": [] if reset else e.get("claimed_premium", []),
                  "rewards": {t: _track_rewards(t, p["campaign"]["highest_cleared"]) for t in range(1, ev["event_track"]["tiers"] + 1)}},
        "event_pass_active": pass_active, "event_pass_sku": ev["event_pass"]["sku"], "booster": ev["pve_booster"], "booster_until": clean({"t": e.get("booster_until")})["t"],
        "active_deployments": [clean(d) for d in deployments], "instant_finish_rule": ev["instant_finish_rubies"],
    }


async def deploy(p: dict, index: int) -> dict:
    ev = canon()["events"]
    if index < 0 or index >= len(ev["deployments"]):
        raise fail(400, "bad_deployment")
    d = ev["deployments"][index]
    energy, at = energy_now(p)
    if energy < d["energy"]:
        raise fail(409, "no_energy", f"Need {d['energy']} Energy")
    running = await db.event_deployments.count_documents({"player_id": p["_id"], "status": "running"})
    if running >= 1:
        raise fail(409, "deployment_running", "A deployment is already running")
    speed = research_pct(p["research"], "event_deploy_speed_pct")
    minutes = d["duration_minutes"] * (1 - speed / 100)
    cur = current_event()
    hs = max(1, p["campaign"]["highest_cleared"])
    rew = F.event_deploy_rewards(hs, d["reward_multiplier"])
    booster = aware(p["events"].get("booster_until"))
    if booster and booster > now():
        rew["event_tokens"] = rnd(rew["event_tokens"] * (1 + ev["pve_booster"]["event_token_reward_pct"] / 100))
    res = await db.players.update_one({"_id": p["_id"], "version": p["version"]}, {"$set": {"events.energy": energy - d["energy"], "events.energy_at": at, "updated_at": now()}, "$inc": {"version": 1}})
    if res.matched_count == 0:
        raise fail(409, "state_changed")
    doc = {"_id": new_id("dep_"), "player_id": p["_id"], "event_key": cur["key"], "index": index, "energy": d["energy"], "multiplier": d["reward_multiplier"],
           "rewards": rew, "started_at": now(), "ends_at": now() + timedelta(minutes=minutes), "status": "running", "highest_stage": hs}
    await db.event_deployments.insert_one(doc)
    return clean(doc)


async def instant_finish(p: dict, deployment_id: str) -> dict:
    d = await db.event_deployments.find_one({"_id": deployment_id, "player_id": p["_id"], "status": "running"})
    if not d:
        raise fail(404, "deployment_not_found")
    remaining = max(0.0, (aware(d["ends_at"]) - now()).total_seconds() / 60)
    cost = F.speedup_rubies(remaining)
    res = await db.players.update_one({"_id": p["_id"], "resources.rubies": {"$gte": cost}}, {"$inc": {"resources.rubies": -cost, "version": 1}, "$set": {"updated_at": now()}})
    if res.matched_count == 0:
        raise fail(409, "insufficient_rubies", f"Instant finish costs {cost} Rubies")
    await db.event_deployments.update_one({"_id": deployment_id}, {"$set": {"ends_at": now() - timedelta(seconds=1), "instant": True}})
    return {"rubies_spent": cost}


async def claim_deployment(p: dict, deployment_id: str) -> dict:
    d = await db.event_deployments.find_one({"_id": deployment_id, "player_id": p["_id"]})
    if not d:
        raise fail(404, "deployment_not_found")
    if aware(d["ends_at"]) > now():
        raise fail(425, "too_early")
    key = f"evdep:{deployment_id}"
    rng = seeded_rng(key)
    ops = Ops()
    rew = d["rewards"]
    prod = production_per_hour(p)
    soft = {k: int(v * rew["soft_hours"]) for k, v in prod.items() if k != "gold"}
    resources_inc(ops, {"event_tokens": rew["event_tokens"], "gold": rew["gold"], **soft})
    cur = current_event()
    if p["events"].get("event_key") != cur["key"]:
        ops.set("events.event_key", cur["key"]).set("events.track_points", rew["event_tokens"]).set("events.claimed_free", []).set("events.claimed_premium", [])
    else:
        ops.inc("events.track_points", rew["event_tokens"])
    gear = None
    if rng.random() * 100 < rew["gear_roll_pct"]:
        gear = await materialize_items(p, key, [(roll_rarity(d["highest_stage"], rng), d["highest_stage"], "event")], rng, ops)
    ops.inc("stats.event_deployments_completed", 1)
    quest_progress(ops, p, "event_deployment", "event_deployments")
    result = {"deployment_id": deployment_id, "event_tokens": rew["event_tokens"], "gold": rew["gold"], "soft": soft, "gear": gear}
    res, applied = await ledger.apply_to_player(key, p["_id"], "event_claim", ops.build(), result)
    if applied:
        await db.event_deployments.update_one({"_id": deployment_id}, {"$set": {"status": "claimed", "claimed_at": now()}})
    return res


async def refill_energy(p: dict) -> dict:
    ev = canon()["events"]["energy_refill"]
    today = day_key()
    used = (p["events"].get("paid_refills") or {}).get(today, 0)
    if used >= ev["paid_refill_daily_cap"]:
        raise fail(409, "refill_cap", f"Max {ev['paid_refill_daily_cap']} paid refills per day")
    energy, at = energy_now(p)
    new = min(canon()["events"]["energy"]["max"], energy + ev["energy_points"])
    res = await db.players.update_one({"_id": p["_id"], "version": p["version"], "resources.rubies": {"$gte": ev["rubies"]}},
                                      {"$inc": {"resources.rubies": -ev["rubies"], "version": 1, f"events.paid_refills.{today}": 1}, "$set": {"events.energy": new, "events.energy_at": at, "updated_at": now()}})
    if res.matched_count == 0:
        raise fail(409, "insufficient_rubies", f"Refill costs {ev['rubies']} Rubies")
    return {"energy": new, "rubies_spent": ev["rubies"], "paid_refills_today": used + 1}


async def buy_booster(p: dict) -> dict:
    b = canon()["events"]["pve_booster"]
    until = now() + timedelta(hours=b["duration_hours"])
    res = await db.players.update_one({"_id": p["_id"], "resources.rubies": {"$gte": b["rubies"]}}, {"$inc": {"resources.rubies": -b["rubies"], "version": 1}, "$set": {"events.booster_until": until, "updated_at": now()}})
    if res.matched_count == 0:
        raise fail(409, "insufficient_rubies")
    return {"booster_until": until.isoformat(), "rubies_spent": b["rubies"]}


async def claim_track(p: dict, tier: int, premium: bool) -> dict:
    ev = canon()["events"]["event_track"]
    view = await event_view(p)
    if tier < 1 or tier > ev["tiers"] or tier > view["track"]["tier_reached"]:
        raise fail(403, "tier_locked")
    lst = "claimed_premium" if premium else "claimed_free"
    if tier in view["track"][lst]:
        raise fail(409, "already_claimed")
    if premium and not view["event_pass_active"]:
        raise fail(403, "event_pass_required")
    rew = _track_rewards(tier, p["campaign"]["highest_cleared"])["premium" if premium else "free"]
    key = f"evtrack:{p['_id']}:{view['event']['key']}:{tier}:{'p' if premium else 'f'}"
    rng = seeded_rng(key)
    ops = Ops()
    prod = production_per_hour(p)
    grant = {k: v for k, v in rew.items() if k in ("rubies", "gold", "forge_dust", "reforge_stone")}
    if rew.get("soft_hours"):
        grant.update({k: int(v * rew["soft_hours"]) for k, v in prod.items() if k != "gold"})
    resources_inc(ops, grant)
    gear = None
    if premium and tier % 5 == 0:
        hs = max(1, p["campaign"]["highest_cleared"])
        gear = await materialize_items(p, key, [(roll_rarity(hs, rng, rew.get("gear_min_rarity"), 2), hs, "event_pass")], rng, ops)
    ops.add(f"events.{lst}", tier)
    if p["events"].get("event_key") != view["event"]["key"]:
        ops.set("events.event_key", view["event"]["key"]).set("events.track_points", 0)
    result = {"tier": tier, "premium": premium, "granted": grant, "gear": gear}
    res, _ = await ledger.apply_to_player(key, p["_id"], "event_track_claim", ops.build(), result)
    return res


# ---- dungeons --------------------------------------------------------------------------------------------
def dungeon_max_tier(p: dict) -> int:
    hc = p["campaign"]["highest_cleared"]
    return sum(1 for s in canon()["dungeons"]["tier_unlock_stages"] if hc >= s)


def training_unit_options(p: dict) -> list[dict]:
    """Units the player has already unlocked, strongest first: the Training Grounds accelerates the army they could already recruit."""
    opts = [{"key": u["key"], "name": u["name"], "base_power": u["base_power"], "recruit_minutes_each": u["recruit_time_minutes_each"]}
            for u in canon()["units"]["catalog"] if all(unit_gates(p, u).values())]
    return sorted(opts, key=lambda u: -u["base_power"])


async def dungeons_view(p: dict) -> dict:
    d = canon()["dungeons"]
    today = day_key()
    entries = p["dungeons"].get("entries", {}) if p["dungeons"].get("day") == today else {}
    runs = await db.dungeon_runs.find({"player_id": p["_id"], "status": "running"}).to_list(None)
    out = []
    for c in d["catalog"]:
        e = entries.get(c["key"], {"free": 0, "paid": 0})
        extra = {"unit_options": training_unit_options(p)} if c["key"] == "training_grounds" else {}
        out.append({**c, **extra, "free_used": e.get("free", 0), "paid_used": e.get("paid", 0), "free_left": max(0, d["free_entries_per_dungeon_per_day"] - e.get("free", 0)),
                    "paid_left": max(0, d["paid_extra_entry_cap_per_dungeon_per_day"] - e.get("paid", 0))})
    return {"unlocked": p["campaign"]["highest_cleared"] >= d["unlock_stage"], "unlock_stage": d["unlock_stage"], "max_tier": dungeon_max_tier(p), "tiers": d["tiers"],
            "tier_unlock_stages": d["tier_unlock_stages"], "run_minutes": d["run_duration_minutes"], "paid_entry_rubies": d["paid_extra_entry_rubies"], "dungeons": out,
            "active_runs": [clean(r) for r in runs], "daily_reset": d["daily_reset"],
            "training_recruit_minutes_per_tier": d["training_recruit_minutes_per_tier"]}


async def start_dungeon(p: dict, key: str, tier: int, unit: str | None = None) -> dict:
    d = canon()["dungeons"]
    cat = next((c for c in d["catalog"] if c["key"] == key), None)
    if not cat:
        raise fail(404, "dungeon_not_found")
    if p["campaign"]["highest_cleared"] < d["unlock_stage"]:
        raise fail(403, "dungeons_locked", f"Dungeons unlock at stage {d['unlock_stage']}")
    if tier < 1 or tier > dungeon_max_tier(p):
        raise fail(403, "tier_locked")
    if key == "training_grounds":
        opts = training_unit_options(p)
        if not opts:
            raise fail(403, "no_unit_unlocked", "No unit unlocked yet")
        unit = unit or opts[0]["key"]
        if unit not in {o["key"] for o in opts}:
            raise fail(403, "unit_locked", f"{unit} is not unlocked yet")
    else:
        unit = None
    if await db.dungeon_runs.count_documents({"player_id": p["_id"], "status": "running"}):
        raise fail(409, "run_active", "A dungeon run is already in progress")
    today = day_key()
    same_day = p["dungeons"].get("day") == today
    e = (p["dungeons"].get("entries", {}) if same_day else {}).get(key, {"free": 0, "paid": 0})
    paid = False
    if e.get("free", 0) < d["free_entries_per_dungeon_per_day"]:
        field = f"dungeons.entries.{key}.free"
    elif e.get("paid", 0) < d["paid_extra_entry_cap_per_dungeon_per_day"]:
        field = f"dungeons.entries.{key}.paid"
        paid = True
    else:
        raise fail(409, "no_entries", "No entries left today")
    flt = {"_id": p["_id"], "version": p["version"]}
    upd: dict = {"$inc": {"version": 1}, "$set": {"updated_at": now()}}
    if paid:
        flt["resources.rubies"] = {"$gte": d["paid_extra_entry_rubies"]}
        upd["$inc"]["resources.rubies"] = -d["paid_extra_entry_rubies"]
    if same_day:
        upd["$inc"][field] = 1
    else:
        entries = {key: {"free": 1 if not paid else 0, "paid": 1 if paid else 0}}
        upd["$set"]["dungeons"] = {"day": today, "entries": entries}
    res = await db.players.update_one(flt, upd)
    if res.matched_count == 0:
        raise fail(409, "insufficient_or_changed")
    prod = production_per_hour(p)
    rewards = F.dungeon_rewards(key, tier, p["campaign"]["highest_cleared"], prod, unit)
    run = {"_id": new_id("run_"), "player_id": p["_id"], "dungeon": key, "tier": tier, "paid": paid, "rewards": rewards, "started_at": now(),
           "ends_at": now() + timedelta(minutes=d["run_duration_minutes"]), "status": "running", "highest_stage": p["campaign"]["highest_cleared"]}
    await db.dungeon_runs.insert_one(run)
    return clean(run)


async def claim_dungeon(p: dict, run_id: str) -> dict:
    r = await db.dungeon_runs.find_one({"_id": run_id, "player_id": p["_id"]})
    if not r:
        raise fail(404, "run_not_found")
    if aware(r["ends_at"]) > now():
        raise fail(425, "too_early")
    key = f"dungeon:{run_id}"
    rng = seeded_rng(key)
    ops = Ops()
    rew = r["rewards"]
    grant = {k: v for k, v in rew.items() if k in ("gold", "forge_dust", "reforge_stone", "mythic_essence", "event_tokens")}
    if "soft" in rew:
        grant.update(rew["soft"])
    resources_inc(ops, grant)
    gained = 0
    if rew.get("xp"):
        level, xp, gained = apply_xp(p["hero"]["level"], p["hero"]["xp"], rew["xp"])
        ops.set("hero.level", level).set("hero.xp", xp)
    gear = None
    if rew.get("gear_rolls"):
        hs = max(1, r["highest_stage"])
        gear = await materialize_items(p, key, [(roll_rarity(hs, rng, None, rew["rarity_rolls"]), hs, r["dungeon"]) for _ in range(rew["gear_rolls"])], rng, ops)
    units = rew.get("units") or {}
    for u, qty in units.items():
        ops.inc(f"army.units.{u}", int(qty))
        ops.add("codex.units", u)
    ops.inc("stats.dungeon_runs", 1)
    quest_progress(ops, p, "run_dungeon", "dungeon_runs")
    result = {"run_id": run_id, "dungeon": r["dungeon"], "tier": r["tier"], "granted": grant, "units": units, "xp": rew.get("xp", 0), "levels_gained": gained, "gear": gear}
    res, applied = await ledger.apply_to_player(key, p["_id"], "dungeon_claim", ops.build(), result)
    if applied:
        await db.dungeon_runs.update_one({"_id": run_id}, {"$set": {"status": "claimed", "claimed_at": now()}})
    return res


async def speedup_dungeon(p: dict, run_id: str) -> dict:
    r = await db.dungeon_runs.find_one({"_id": run_id, "player_id": p["_id"], "status": "running"})
    if not r:
        raise fail(404, "run_not_found")
    cost = F.speedup_rubies(max(0.0, (aware(r["ends_at"]) - now()).total_seconds() / 60))
    res = await db.players.update_one({"_id": p["_id"], "resources.rubies": {"$gte": cost}}, {"$inc": {"resources.rubies": -cost, "version": 1}})
    if res.matched_count == 0:
        raise fail(409, "insufficient_rubies", f"Costs {cost} Rubies")
    await db.dungeon_runs.update_one({"_id": run_id}, {"$set": {"ends_at": now() - timedelta(seconds=1)}})
    return {"rubies_spent": cost}


# ---- quests / login ---------------------------------------------------------------------------------------
def quests_view(p: dict) -> dict:
    q = canon()["quests"]
    dp, dd = quest_points("daily", p)
    wp, wd = quest_points("weekly", p)
    login = p["quests"].get("login", {"cycle_day": 0, "last_claim_day": None})

    def templates(kind: str) -> list:  # v1.5: text of the active alternative replaces the base text
        return [{**t, "text": dd["tasks"][t["key"]]["text"] if kind == "daily" else wd["tasks"][t["key"]]["text"],
                 "alt_active": (dd if kind == "daily" else wd)["tasks"][t["key"]]["alt_active"]} for t in q[kind]["templates"]]

    return {
        "daily": {"points": dp, "chests": q["daily"]["point_chests"], "templates": templates("daily"), **dd, "resets": "00:00 UTC"},
        "weekly": {"points": wp, "chests": q["weekly"]["point_chests"], "templates": templates("weekly"), **wd},
        "login": {"cycle_days": q["login_calendar"]["cycle_days"], "cycle_day": login.get("cycle_day", 0), "claimed_today": login.get("last_claim_day") == day_key(),
                  "rewards": LOGIN_RUBIES, "day_7": q["login_calendar"]["day_7_reward"], "rubies_total": q["login_calendar"]["rubies_total_per_cycle"]},
        "season": season_view(p),
    }


async def claim_quest_chest(p: dict, kind: str, index: int) -> dict:
    q = canon()["quests"][kind]
    chests = q["point_chests"]
    if index < 0 or index >= len(chests):
        raise fail(400, "bad_chest")
    pts, detail = quest_points(kind, p)
    if pts < chests[index]["points"]:
        raise fail(403, "not_enough_points")
    if index in detail["chests_claimed"]:
        raise fail(409, "already_claimed")
    period = day_key() if kind == "daily" else week_key()
    key = f"quest:{p['_id']}:{kind}:{period}:{index}"
    ops = Ops()
    grant = {k: v for k, v in chests[index].items() if k != "points"}
    resources_inc(ops, grant)
    state = p["quests"].get(kind) or {}
    if state.get("day" if kind == "daily" else "week") != period:
        fresh = {"day" if kind == "daily" else "week": period, "progress": {}, "chests_claimed": [index]}
        ops.set(f"quests.{kind}", fresh)
    else:
        ops.add(f"quests.{kind}.chests_claimed", index)
    prev = chests[index - 1]["points"] if index else 0
    sp = (chests[index]["points"] - prev) * (canon()["monetization"]["season_pass"]["season_points_per_daily_quest_point"] if kind == "daily" else canon()["monetization"]["season_pass"]["season_points_per_weekly_quest_point"])
    _season_points_ops(ops, p, sp)
    result = {"kind": kind, "index": index, "granted": grant, "season_points": sp}
    res, _ = await ledger.apply_to_player(key, p["_id"], "quest_chest", ops.build(), result)
    return res


async def claim_login(p: dict) -> dict:
    login = p["quests"].get("login", {"cycle_day": 0, "last_claim_day": None})
    today = day_key()
    if login.get("last_claim_day") == today:
        raise fail(409, "already_claimed")
    day = (login.get("cycle_day", 0) % 7) + 1
    key = f"login:{p['_id']}:{today}"
    rng = seeded_rng(key)
    ops = Ops()
    resources_inc(ops, {"rubies": LOGIN_RUBIES[day - 1]})
    gear = None
    if day == 7 and p["campaign"]["highest_cleared"] >= 1:
        hs = p["campaign"]["highest_cleared"]
        gear = await materialize_items(p, key, [(roll_rarity(hs, rng, None, 2), hs, "login_day7")], rng, ops)
    ops.set("quests.login", {"cycle_day": day, "last_claim_day": today})
    result = {"day": day, "rubies": LOGIN_RUBIES[day - 1], "gear": gear}
    res, _ = await ledger.apply_to_player(key, p["_id"], "login_claim", ops.build(), result, extra_filter={"quests.login.last_claim_day": {"$ne": today}})
    return res


# ---- achievements / codex ------------------------------------------------------------------------------------
ACH_METRIC_IT = {
    "campaign_stage_reached": ("Conquistatore", "Supera lo stage {t} della Campagna", "stage superati", "Supera ancora {d} stage"),
    "hero_level_reached": ("Veterano", "Porta il Lord al livello {t}", "livello del Lord", "Ti mancano {d} livelli del Lord"),
    "legendary_or_higher_items_found": ("Cercatore di reliquie", "Trova {t} oggetti Leggendari o superiori", "oggetti Leggendari+ trovati", "Trova ancora {d} oggetti Leggendari o superiori"),
    "castle_level_reached": ("Signore del Castello", "Porta il Castello al livello {t}", "livello del Castello", "Ti mancano {d} livelli di Castello"),
    "units_recruited_total": ("Reclutatore", "Recluta {t} unità in totale", "unità reclutate", "Recluta ancora {d} unità"),
    "domain_tiles_owned": ("Signore del Dominio", "Possiedi {t} caselle del Dominio", "caselle possedute", "Ti mancano {d} caselle (una ogni 2 stage pari dal 4)"),
    "event_deployments_completed": ("Esploratore", "Completa {t} spedizioni evento", "spedizioni completate", "Completa ancora {d} spedizioni evento"),
    "alliance_war_lanes_or_boss_attacks": ("Fratello d'armi", "Combatti {t} corsie di guerra o attacchi al Titano", "corsie/attacchi", "Ancora {d} corsie di guerra o attacchi al Titano"),
}
ACH_CATEGORY_IT = {"campaign": "Campagna", "hero": "Eroe", "gear": "Equipaggiamento", "kingdom": "Regno", "army": "Esercito", "domain": "Dominio", "events": "Eventi", "alliance": "Alleanza"}


def achievements_view(p: dict) -> dict:
    m = achievement_metrics(p)
    out = []
    by_metric: dict = {}
    for a in canon()["achievements"]["catalog"]:
        by_metric.setdefault(a["metric"], []).append(a)
    for a in canon()["achievements"]["catalog"]:
        val = m[a["metric"]]
        tier = by_metric[a["metric"]].index(a) + 1
        title_base, desc, unit, missing = ACH_METRIC_IT[a["metric"]]
        unlocked = val >= a["threshold"]
        claimed = a["key"] in p.get("achievements_claimed", [])
        t = f"{a['threshold']:,}".replace(",", ".")
        d = f"{max(0, a['threshold'] - val):,}".replace(",", ".")
        status = (f"Riscattata: +{a['rubies']} Rubini" if claimed else f"Completata! Ritira {a['rubies']} Rubini" if unlocked else missing.format(d=d) + f" per ottenere {a['rubies']} Rubini")
        out.append({**a, "value": val, "unlocked": unlocked, "claimed": claimed, "title": f"{title_base} {'I' * tier if tier <= 3 else ['IV', 'V', 'VI', 'VII'][tier - 4]}",
                    "description": desc.format(t=t), "unit_label": unit, "status": status, "category_label": ACH_CATEGORY_IT.get(a["category"], a["category"])})
    return {"achievements": out, "total_rubies": canon()["achievements"]["total_rubies_across_all"], "categories": canon()["achievements"]["categories"], "category_labels": ACH_CATEGORY_IT}


async def claim_achievement(p: dict, key: str) -> dict:
    a = next((x for x in canon()["achievements"]["catalog"] if x["key"] == key), None)
    if not a:
        raise fail(404, "achievement_not_found")
    if achievement_metrics(p)[a["metric"]] < a["threshold"]:
        raise fail(403, "not_unlocked")
    if key in p.get("achievements_claimed", []):
        raise fail(409, "already_claimed")
    ops = Ops()
    resources_inc(ops, {"rubies": a["rubies"]})
    ops.add("achievements_claimed", key)
    res, _ = await ledger.apply_to_player(f"ach:{p['_id']}:{key}", p["_id"], "achievement", ops.build(), {"key": key, "rubies": a["rubies"]}, extra_filter={"achievements_claimed": {"$ne": key}})
    return res


def codex_view(p: dict) -> dict:
    totals = codex_totals()
    have = p.get("codex", {})
    pct = codex_completion_pct(p)
    return {"tracks": {k: {"entries": v, "discovered": sorted(set(have.get(k, [])) & set(v))} for k, v in totals.items()}, "completion_pct": pct,
            "milestones": [{**m, "claimed": m["pct"] in p.get("codex_milestones_claimed", []), "unlocked": pct >= m["pct"]} for m in canon()["codex"]["completion_milestones_pct"]]}


async def claim_codex(p: dict, pct: int) -> dict:
    m = next((x for x in canon()["codex"]["completion_milestones_pct"] if x["pct"] == pct), None)
    if not m:
        raise fail(404, "milestone_not_found")
    if codex_completion_pct(p) < pct:
        raise fail(403, "not_unlocked")
    if pct in p.get("codex_milestones_claimed", []):
        raise fail(409, "already_claimed")
    ops = Ops()
    resources_inc(ops, {"rubies": m["rubies"]})
    ops.add("codex_milestones_claimed", pct)
    res, _ = await ledger.apply_to_player(f"codex:{p['_id']}:{pct}", p["_id"], "codex", ops.build(), {"pct": pct, "rubies": m["rubies"]}, extra_filter={"codex_milestones_claimed": {"$ne": pct}})
    return res


# ---- season pass --------------------------------------------------------------------------------------------
def season_key() -> str:
    sp = canon()["monetization"]["season_pass"]
    idx = (now() - EPOCH_MONDAY).days // sp["duration_days"]
    return f"S{idx}"


def season_bounds() -> tuple[datetime, datetime]:
    sp = canon()["monetization"]["season_pass"]
    idx = (now() - EPOCH_MONDAY).days // sp["duration_days"]
    start = EPOCH_MONDAY + timedelta(days=idx * sp["duration_days"])
    return start, start + timedelta(days=sp["duration_days"])


def season_level_rewards(level: int) -> dict:
    """DERIVED from canonical totals: free 150 Rubies (5/level); premium 500 Rubies (16/level + 20 at 30),
    2500 Forge Dust, 25 Reforge Stones, 8 Mythic Essence, 3 cosmetics at levels 10/20/30."""
    sp = canon()["monetization"]["season_pass"]
    free = {"rubies": sp["free_track_total_rubies"] // sp["levels"]}
    prem = {"rubies": 16 + (20 if level == sp["levels"] else 0), "forge_dust": 83 + (10 if level == sp["levels"] else 0)}
    if level % 6 == 0:
        prem["reforge_stone"] = 5
    if level in (4, 8, 12, 16, 20, 24, 28, 30):
        prem["mythic_essence"] = 1
    cos = {10: "profile_frame:season", 20: "alliance_banner:season", 30: "hero_cloak:season"}
    if level in cos:
        prem["cosmetic"] = cos[level]
    return {"free": free, "premium": prem}


def _season_points_ops(ops: Ops, p: dict, pts: int):
    sk = season_key()
    if p["season"].get("season_key") != sk:
        ops.set("season", {"points": pts, "claimed_free": [], "claimed_premium": [], "season_key": sk})
    else:
        ops.inc("season.points", pts)


def season_view(p: dict) -> dict:
    sp = canon()["monetization"]["season_pass"]
    sk = season_key()
    s = p["season"] if p["season"].get("season_key") == sk else {"points": 0, "claimed_free": [], "claimed_premium": []}
    start, end = season_bounds()
    return {"season_key": sk, "starts_at": start.isoformat(), "ends_at": end.isoformat(), "points": s["points"], "points_per_level": sp["points_per_level"], "levels": sp["levels"],
            "level_reached": min(sp["levels"], s["points"] // sp["points_per_level"]), "claimed_free": s.get("claimed_free", []), "claimed_premium": s.get("claimed_premium", []),
            "rewards": {l: season_level_rewards(l) for l in range(1, sp["levels"] + 1)}, "sku": sp["sku"]}


async def claim_season(p: dict, level: int, premium: bool) -> dict:
    v = season_view(p)
    if level < 1 or level > v["levels"] or level > v["level_reached"]:
        raise fail(403, "level_locked")
    lst = "claimed_premium" if premium else "claimed_free"
    if level in v[lst]:
        raise fail(409, "already_claimed")
    if premium:
        ent = await db.entitlements.find_one({"player_id": p["_id"], "entitlement": "season_pass"})
        if not (ent and aware(ent.get("expires_at")) and aware(ent["expires_at"]) > now()):
            raise fail(403, "season_pass_required")
    rew = season_level_rewards(level)["premium" if premium else "free"]
    ops = Ops()
    resources_inc(ops, {k: v2 for k, v2 in rew.items() if k != "cosmetic"})
    if rew.get("cosmetic"):
        ops.add("cosmetics.owned", rew["cosmetic"])
    if p["season"].get("season_key") != v["season_key"]:
        ops.set("season", {"points": 0, "claimed_free": [level] if not premium else [], "claimed_premium": [level] if premium else [], "season_key": v["season_key"]})
    else:
        ops.add(f"season.{lst}", level)
    key = f"season:{p['_id']}:{v['season_key']}:{level}:{'p' if premium else 'f'}"
    res, _ = await ledger.apply_to_player(key, p["_id"], "season_claim", ops.build(), {"level": level, "premium": premium, "granted": rew})
    return res
