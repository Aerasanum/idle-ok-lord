"""Campaign auto-combat (I03): deterministic server outcome, escrowed rewards, idempotent claim."""
from datetime import timedelta

from ..core import db, ledger
from ..core.canon import canon, region_for_stage
from ..core.util import aware, clean, fail, new_id, now, rnd, seeded_rng
from . import formulas as F
from .gear import materialize_items, stage_drop_plan
from .hero import apply_xp
from .player import combat_profile
from .progress import Ops, codex_add, quest_progress, resources_inc

MAX_STAGE_AHEAD = 1  # you can only attempt the next uncleared stage or any cleared one


def build_timeline(stage: int, kind: str, win: bool, duration: int, kill_rewards: dict, rng) -> dict:
    """Client-side animation plan derived from the authoritative result (cosmetic RNG only)."""
    b = canon()["battle"]
    waves = b["waves_per_stage"]
    region = region_for_stage(min(stage, 200))
    fams = region["enemy_families"]
    out = []
    per_wave = F.monsters_per_wave(stage)
    total_monsters = per_wave * (waves - 1) + (1 + F.boss_minions(stage) if kind == "boss" else per_wave)
    xp_each = kill_rewards["xp"] / max(total_monsters, 1)
    gold_each = kill_rewards["gold"] / max(total_monsters, 1)
    soft_each = kill_rewards["soft"] / max(total_monsters, 1)
    reached = waves if win else max(1, rnd(waves * 0.6))
    for w in range(1, waves + 1):
        is_boss_wave = kind == "boss" and w == waves
        n = (1 + F.boss_minions(stage)) if is_boss_wave else per_wave
        monsters = []
        for i in range(n):
            mtype = "boss" if (is_boss_wave and i == 0) else ("elite" if kind == "elite" else "normal")
            monsters.append({"family": region["region_boss"] if mtype == "boss" else fams[rng.randrange(len(fams))], "type": mtype})
        out.append({
            "wave": w, "monsters": monsters, "cleared": win or w < reached,
            "kill_xp": rnd(xp_each * n), "kill_gold": rnd(gold_each * n), "kill_soft": rnd(soft_each * n),
            "t_start": round(duration * (w - 1) / waves, 2), "t_end": round(duration * w / waves, 2),
        })
    return {"waves": out, "total_monsters": total_monsters, "duration": duration, "region": {"name": region["name"], "region": region["region"], "visual": region["visual"], "boss": region["region_boss"]}}


async def start_attempt(p: dict, stage: int, client_key: str | None = None) -> dict:
    hc = p["campaign"]["highest_cleared"]
    if stage < 1 or stage > hc + MAX_STAGE_AHEAD:
        raise fail(400, "stage_locked", f"Highest cleared stage is {hc}")
    active = p["campaign"].get("active_attempt")
    if active:
        a = await db.battle_attempts.find_one({"_id": active})
        if a and a["status"] == "pending":
            if aware(a["resolves_at"]) > now():
                return {"attempt": clean(a), "reused": True}
            await claim_attempt(p, active)  # auto-settle a resolved but unclaimed attempt
            p = await db.players.find_one({"_id": p["_id"]})
    prof = await combat_profile(p)
    kind = F.stage_kind(stage)
    required = F.enemy_required_power(stage)
    hero_power = prof["hero"]["power"]
    if kind == "boss":
        hero_power = rnd(hero_power * (1 + prof["hero"]["boss_damage_pct"] / 100))
    total = hero_power + prof["army_power"]
    win = total >= required
    first_clear = stage == hc + 1
    duration = F.victory_duration(required, total)
    attempt_id = new_id("att_")
    rng = seeded_rng(attempt_id)
    b = canon()["battle"]
    if first_clear:
        base = F.first_clear_rewards(stage)
        scale = 1.0
    else:
        base = F.repeat_rewards(stage)
        scale = duration / b["repeat_farm_cycle_seconds"]  # keeps the canonical 120s-cycle farm income rate
    gold_mult = 1 + prof["hero"]["gold_find_pct"] / 100
    full = {"xp": base["xp"] * scale, "gold": base["gold"] * scale * gold_mult, "soft": base["soft"] * scale}
    kill_part = {k: v * 0.75 for k, v in full.items()}
    clear_part = {k: v * 0.25 for k, v in full.items()}
    if win:
        rewards = {"xp": rnd(full["xp"]), "gold": rnd(full["gold"]), "soft": rnd(full["soft"])}
        drops = stage_drop_plan(stage, kind, first_clear, prof["hero"]["gear_find_pct"], rng) if win else []
    else:
        # failure: 20% of kill-earned XP/Gold only (no clear bonus, no tile, no boss chest)
        rewards = {"xp": rnd(kill_part["xp"] * 0.2), "gold": rnd(kill_part["gold"] * 0.2), "soft": 0}
        drops = []
    timeline = build_timeline(stage, kind, win, duration, {k: rnd(v) for k, v in kill_part.items()}, rng)
    doc = {
        "_id": attempt_id, "player_id": p["_id"], "stage": stage, "kind": kind, "first_clear": first_clear and win, "win": win,
        "required_power": required, "total_power": total, "hero_power": hero_power, "army_power": prof["army_power"],
        "duration": duration, "rewards": rewards, "clear_bonus": {k: rnd(v) for k, v in clear_part.items()} if win else {"xp": 0, "gold": 0, "soft": 0},
        "drops": drops, "timeline": timeline, "status": "pending", "created_at": now(), "resolves_at": now() + timedelta(seconds=duration),
        "client_key": client_key, "army_deployed": prof["army_deployed"], "formation": dict(p["army"]["formation"]),
    }
    await db.battle_attempts.insert_one(doc)
    await db.players.update_one({"_id": p["_id"]}, {"$set": {"campaign.active_attempt": attempt_id, "campaign.current_stage": stage, "updated_at": now()}, "$inc": {"version": 1}})
    return {"attempt": clean(doc), "reused": False}


async def claim_attempt(p: dict, attempt_id: str) -> dict:
    a = await db.battle_attempts.find_one({"_id": attempt_id, "player_id": p["_id"]})
    if not a:
        raise fail(404, "attempt_not_found")
    if aware(a["resolves_at"]) > now():
        raise fail(425, "too_early", "Battle still in progress on the server")
    key = f"battle:{attempt_id}"
    for _ in range(3):
        p = await db.players.find_one({"_id": p["_id"]})
        ops = Ops()
        r = a["rewards"]
        level, xp, gained = apply_xp(p["hero"]["level"], p["hero"]["xp"], r["xp"])
        ops.set("hero.level", level).set("hero.xp", xp)
        resources_inc(ops, {"gold": r["gold"], **F.split_soft(r["soft"])})
        ops.inc("stats.kills", a["timeline"]["total_monsters"] if a["win"] else rnd(a["timeline"]["total_monsters"] * 0.6))
        region = region_for_stage(min(a["stage"], 200))
        codex_add(ops, "regions", region["name"])
        for fam in {m["family"] for w in a["timeline"]["waves"] for m in w["monsters"] if m["type"] != "boss"}:
            codex_add(ops, "monster_families", fam)
        summary = None
        new_highest = p["campaign"]["highest_cleared"]
        if a["win"]:
            if a["kind"] == "boss":
                codex_add(ops, "bosses", region["region_boss"])
            if a["stage"] > new_highest:
                new_highest = a["stage"]
                ops.set("campaign.highest_cleared", new_highest)
                ops.set("domain.owned", F.domain_tiles_for_stage(new_highest))
                ops.set("campaign.current_stage", min(new_highest + 1, 10**6))
            quest_progress(ops, p, "clear_stages", "clear_stages")
            if a["drops"]:
                summary = await materialize_items(p, key, [(rar, a["stage"], f"stage_{a['stage']}") for rar in a["drops"]], seeded_rng(key), ops)
        if p["campaign"].get("active_attempt") == attempt_id:
            ops.set("campaign.active_attempt", None)
        ops.push("recent_attempts", {"id": attempt_id, "stage": a["stage"], "win": a["win"], "at": now()}, -20)
        result = {"attempt_id": attempt_id, "stage": a["stage"], "win": a["win"], "first_clear": a["first_clear"], "rewards": {**r, "soft_split": F.split_soft(r["soft"])},
                  "levels_gained": gained, "hero_level": level, "highest_cleared": new_highest, "domain_tiles": F.domain_tiles_for_stage(new_highest), "gear": summary}
        try:
            res, applied = await ledger.apply_to_player(key, p["_id"], "battle_claim", ops.build(), result, extra_filter={"version": p["version"]})
            if applied:
                await db.battle_attempts.update_one({"_id": attempt_id}, {"$set": {"status": "claimed", "claimed_at": now()}})
            return res
        except Exception as e:  # guard failed due to a concurrent version bump -> retry with fresh state
            if getattr(e, "status_code", None) == 409:
                continue
            raise
    raise fail(409, "retry", "Concurrent update, retry")


def stage_preview(stage: int) -> dict:
    kind = F.stage_kind(stage)
    fc = F.first_clear_rewards(stage)
    return {
        "stage": stage, "kind": kind, "enemy_power": F.enemy_power(stage), "required_power": F.enemy_required_power(stage),
        "first_clear": fc, "repeat": {k: rnd(v) for k, v in F.repeat_rewards(stage).items()}, "region": F.region_info(stage),
        "item_level": F.item_level_for_stage(stage), "monsters_per_wave": F.monsters_per_wave(stage),
        "drop_weights": F.unlocked_drop_weights(min(stage, 200)),
    }
