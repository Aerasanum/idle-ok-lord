"""Async 10v10 territory war on a 19x19 season map + Titan Hunt alliance boss (I13)."""
import statistics
from datetime import timedelta

from ..core import db, ledger
from ..core.canon import canon
from ..core.push import safe_push
from ..core.util import aware, clean, fail, new_id, now, rnd, seeded_rng
from . import formulas as F
from .liveops import season_bounds, season_key
from .player import combat_profile, research_pct
from .progress import Ops, quest_progress, resources_inc
from .social import membership, role_rank, system_feed

N = 19


def xy(node_id: int) -> tuple[int, int]:
    return node_id % N, node_id // N


def neighbors(node_id: int) -> list[int]:
    x, y = xy(node_id)
    out = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < N and 0 <= ny < N:
            out.append(ny * N + nx)
    return out


def generate_map(shard_id: str) -> list[dict]:
    """Deterministic 361-node map honoring canonical node counts; 64 home castles on an 8x8 lattice."""
    types = canon()["alliance_war"]["node_types"]
    rng = seeded_rng("idle1-warmap", shard_id)
    nodes = {}
    homes = []
    for gy in range(8):
        for gx in range(8):
            x, y = 1 + gx * 2 + (1 if gx >= 4 else 0), 1 + gy * 2 + (1 if gy >= 4 else 0)
            homes.append(y * N + x)
    for i, nid in enumerate(homes[: types["home_castle"]["count"]]):
        nodes[nid] = {"type": "home_castle", "home_slot": i}
    rest = [n for n in range(N * N) if n not in nodes]
    rng.shuffle(rest)
    pool = []
    for t in ("city", "fortress", "mine", "town", "village", "wilderness"):
        pool += [t] * types[t]["count"]
    assert len(pool) == len(rest)
    for nid, t in zip(rest, pool):
        nodes[nid] = {"type": t}
    out = []
    for nid in range(N * N):
        x, y = xy(nid)
        out.append({"_id": f"{shard_id}:{nid}", "shard_id": shard_id, "node_id": nid, "x": x, "y": y, "type": nodes[nid]["type"], "home_slot": nodes[nid].get("home_slot"),
                    "owner_alliance_id": None, "bonus": types[nodes[nid]["type"]].get("bonus"), "captured_at": None})
    return out


async def current_shard() -> dict:
    sk = season_key()
    shard = await db.war_shards.find_one({"season_key": sk, "full": {"$ne": True}})
    if not shard:
        shard = {"_id": new_id("shard_"), "season_key": sk, "alliance_ids": [], "created_at": now(), "full": False}
        await db.war_shards.insert_one(shard)
        await db.alliance_map_nodes.insert_many(generate_map(shard["_id"]))
    return shard


async def ensure_alliance_on_map(a: dict) -> dict:
    sk = season_key()
    if a.get("shard_id") and a.get("season_key") == sk and a.get("home_node") is not None:
        return a
    shard = await current_shard()
    mx = canon()["alliance_war"]["alliances_per_shard_max"]
    res = await db.war_shards.update_one({"_id": shard["_id"], f"alliance_ids.{mx - 1}": {"$exists": False}, "alliance_ids": {"$ne": a["_id"]}}, {"$addToSet": {"alliance_ids": a["_id"]}})
    if res.matched_count == 0 and a["_id"] not in shard["alliance_ids"]:
        await db.war_shards.update_one({"_id": shard["_id"]}, {"$set": {"full": True}})
        return await ensure_alliance_on_map(a)
    home = await db.alliance_map_nodes.find_one_and_update({"shard_id": shard["_id"], "type": "home_castle", "owner_alliance_id": None}, {"$set": {"owner_alliance_id": a["_id"], "captured_at": now()}}, sort=[("home_slot", 1)])
    if not home:
        await db.war_shards.update_one({"_id": shard["_id"]}, {"$set": {"full": True}})
        return await ensure_alliance_on_map(a)
    await db.alliances.update_one({"_id": a["_id"]}, {"$set": {"shard_id": shard["_id"], "season_key": sk, "home_node": home["node_id"], "season_points": 0}})
    a.update({"shard_id": shard["_id"], "season_key": sk, "home_node": home["node_id"]})
    return a


async def territory_bonus(alliance_id: str | None, shard_id: str | None) -> dict:
    """Stacked node bonuses with canonical per-type stack caps (+ territory_bonus_cap_pct research is per-player, applied by caller)."""
    if not alliance_id or not shard_id:
        return {}
    types = canon()["alliance_war"]["node_types"]
    out: dict = {}
    counts: dict = {}
    async for n in db.alliance_map_nodes.find({"shard_id": shard_id, "owner_alliance_id": alliance_id}, {"type": 1}):
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    for t, c in counts.items():
        b = types[t].get("bonus")
        if not b:
            continue
        cap = types[t].get("stack_cap_pct")
        for k, v in b.items():
            out[k] = out.get(k, 0) + (min(v * c, cap) if cap else v * c)
    return out


async def map_view(p: dict) -> dict:
    me = await membership(p["_id"])
    a = await db.alliances.find_one({"_id": me["alliance_id"]}) if me else None
    if a and not a.get("disbanded_at"):
        a = await ensure_alliance_on_map(a)
    shard_id = a["shard_id"] if a else (await current_shard())["_id"]
    nodes = await db.alliance_map_nodes.find({"shard_id": shard_id}).sort("node_id", 1).to_list(400)
    owners = {n["owner_alliance_id"] for n in nodes if n["owner_alliance_id"]}
    als = {x["_id"]: x for x in await db.alliances.find({"_id": {"$in": list(owners)}}, {"name": 1, "tag": 1, "season_points": 1, "home_node": 1}).to_list(100)}
    wars = await db.alliance_wars.find({"shard_id": shard_id, "status": {"$in": ["prep", "locked"]}}).to_list(100)
    start, end = season_bounds()
    return {
        "shard_id": shard_id, "size": N, "season": {"key": season_key(), "starts_at": start.isoformat(), "ends_at": end.isoformat()},
        "nodes": [{"node_id": n["node_id"], "x": n["x"], "y": n["y"], "type": n["type"], "owner": n["owner_alliance_id"], "bonus": n["bonus"]} for n in nodes],
        "alliances": {k: {"name": v["name"], "tag": v["tag"], "season_points": v.get("season_points", 0), "home_node": v.get("home_node")} for k, v in als.items()},
        "my_alliance_id": a["_id"] if a else None, "my_home": a.get("home_node") if a else None,
        "active_wars": [clean(w) for w in wars], "territory_bonus": await territory_bonus(a["_id"] if a else None, shard_id),
        "rules": {**{k: canon()["alliance_war"][k] for k in ("prep_hours", "roster_lock_minutes_before_resolution", "attack_roster_size", "defense_roster_size", "attack_limit_per_alliance_hours", "rewards", "tie_break", "target_rule")},
                  "minimum_members_to_attack": canon()["alliances"]["minimum_members_to_attack"]},
        "leaderboard": [{"alliance_id": x["_id"], "name": x["name"], "tag": x["tag"], "season_points": x.get("season_points", 0)} for x in await db.alliances.find({"shard_id": shard_id}).sort("season_points", -1).limit(20).to_list(20)],
    }


async def declare(p: dict, node_id: int) -> dict:
    aw = canon()["alliance_war"]
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "officer_required")
    a = await ensure_alliance_on_map(await db.alliances.find_one({"_id": me["alliance_id"]}))
    if a.get("displaced_until") and aware(a["displaced_until"]) > now():
        raise fail(409, "displaced", "Alliance is relocating after losing its home castle")
    if await db.alliance_members.count_documents({"alliance_id": a["_id"]}) < canon()["alliances"]["minimum_members_to_attack"]:
        raise fail(403, "min_members", f"Need {canon()['alliances']['minimum_members_to_attack']} members to attack")
    last = await db.alliance_wars.find_one({"attacker_id": a["_id"], "declared_at": {"$gte": now() - timedelta(hours=aw["attack_limit_per_alliance_hours"])}})
    if last:
        raise fail(409, "attack_cooldown", "One attack per 24h per alliance")
    if await db.alliance_wars.find_one({"status": {"$in": ["prep", "locked"]}, "$or": [{"attacker_id": a["_id"]}, {"defender_id": a["_id"]}]}):
        raise fail(409, "war_active", "Alliance already involved in an active war")
    node = await db.alliance_map_nodes.find_one({"shard_id": a["shard_id"], "node_id": node_id})
    if not node:
        raise fail(404, "node_not_found")
    if node["owner_alliance_id"] == a["_id"]:
        raise fail(400, "own_node")
    owned = {n["node_id"] for n in await db.alliance_map_nodes.find({"shard_id": a["shard_id"], "owner_alliance_id": a["_id"]}, {"node_id": 1}).to_list(400)}
    if not any(nb in owned for nb in neighbors(node_id)):
        raise fail(400, "not_adjacent", "Target must be adjacent to owned territory")
    if await db.alliance_wars.find_one({"shard_id": a["shard_id"], "node_id": node_id, "status": {"$in": ["prep", "locked"]}}):
        raise fail(409, "node_contested")
    defender_id = node["owner_alliance_id"]
    if defender_id and await db.alliance_wars.find_one({"status": {"$in": ["prep", "locked"]}, "$or": [{"attacker_id": defender_id}, {"defender_id": defender_id}]}):
        raise fail(409, "defender_busy", "Defender already in an active war")
    resolves = now() + timedelta(hours=aw["prep_hours"])
    war = {"_id": new_id("war_"), "shard_id": a["shard_id"], "node_id": node_id, "node_type": node["type"], "attacker_id": a["_id"], "defender_id": defender_id, "declared_by": p["_id"],
           "declared_at": now(), "resolves_at": resolves, "lock_at": resolves - timedelta(minutes=aw["roster_lock_minutes_before_resolution"]), "status": "prep",
           "attack_roster": [], "defense_roster": [], "result": None, "archived_at": None}
    await db.alliance_wars.insert_one(war)
    await system_feed(a["_id"], f"War declared on node {node_id} ({node['type']}). Roster needed!")
    members = [m["player_id"] for m in await db.alliance_members.find({"alliance_id": a["_id"]}).to_list(40)]
    await safe_push(members, {"title": "Alliance War", "message": f"War declared on node {node_id}. Set the roster before lock.", "action_url": "/alliance/war"}, f"war_roster:{war['_id']}")
    if defender_id:
        await system_feed(defender_id, f"Your node {node_id} is under attack! Set the defense roster.")
        dmembers = [m["player_id"] for m in await db.alliance_members.find({"alliance_id": defender_id}).to_list(40)]
        await safe_push(dmembers, {"title": "Alliance War", "message": f"Node {node_id} is under attack. Set the defense roster.", "action_url": "/alliance/war"}, f"war_defend:{war['_id']}")
    return clean(war)


async def set_roster(p: dict, war_id: str, player_ids: list[str]) -> dict:
    aw = canon()["alliance_war"]
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "officer_required")
    w = await db.alliance_wars.find_one({"_id": war_id})
    if not w or w["status"] != "prep":
        raise fail(409, "war_not_open")
    if aware(w["lock_at"]) <= now():
        raise fail(409, "roster_locked")
    side = "attack_roster" if w["attacker_id"] == me["alliance_id"] else "defense_roster" if w.get("defender_id") == me["alliance_id"] else None
    if not side:
        raise fail(403, "not_in_war")
    size = aw["attack_roster_size"] if side == "attack_roster" else aw["defense_roster_size"]
    ids = list(dict.fromkeys(player_ids))
    if len(ids) > size:
        raise fail(400, "roster_size", f"Max {size} players")
    members = {m["player_id"] for m in await db.alliance_members.find({"alliance_id": me["alliance_id"]}).to_list(40)}
    if any(i not in members for i in ids):
        raise fail(400, "not_members")
    await db.alliance_wars.update_one({"_id": war_id, "status": "prep"}, {"$set": {side: ids}})
    return {"war_id": war_id, side: ids}


async def _player_snapshot(pid: str, shard_id: str, alliance_id: str | None) -> dict:
    p = await db.players.find_one({"_id": pid})
    if not p:
        return None
    tb = await territory_bonus(alliance_id, shard_id)
    prof = await combat_profile(p, tb)
    roster_pct = research_pct(p["research"], "war_roster_power_pct")
    items = await db.gear_items.find({"_id": {"$in": [v for v in p["equipped"].values() if v]}}).to_list(20)
    return {
        "player_id": pid, "display_name": p["display_name"], "hero_level": p["hero"]["level"],
        "equipped_gear_and_affixes": [{"slot": i["slot"], "rarity": i["rarity"], "item_level": i["item_level"], "stats": i["stats"], "affixes": i["affixes"]} for i in items],
        "forge_levels": p["forge"], "talents": p["hero"]["talents"], "deployed_army": p["army"]["formation"], "research": p["research"], "territory_bonuses": tb,
        "hero_power": prof["hero"]["power"], "army_power": prof["army_power"], "total_power": prof["total_power"],
        "war_power": rnd(prof["total_power"] * (1 + roster_pct / 100)),
        "defense_pct": research_pct(p["research"], "wall_defense_pct") + research_pct(p["research"], "war_defense_pct"),
        "fortress_attack_pct": research_pct(p["research"], "fortress_attack_pct"),
    }


async def _alliance_median(alliance_id: str, shard_id: str) -> float:
    pids = [m["player_id"] for m in await db.alliance_members.find({"alliance_id": alliance_id}).to_list(40)]
    powers = []
    for pid in pids:
        s = await _player_snapshot(pid, shard_id, alliance_id)
        if s:
            powers.append(s["war_power"])
    return statistics.median(powers) if powers else 1.0


async def lock_war(w: dict) -> dict | None:
    """Freeze the complete combat snapshot at roster lock. Immutable afterwards (unique war_id)."""
    aw = canon()["alliance_war"]
    claimed = await db.alliance_wars.update_one({"_id": w["_id"], "status": "prep"}, {"$set": {"status": "locking"}})
    if claimed.modified_count == 0:
        return None
    w = await db.alliance_wars.find_one({"_id": w["_id"]})
    if len(w["attack_roster"]) < aw["attack_roster_size"]:
        await db.alliance_wars.update_one({"_id": w["_id"]}, {"$set": {"status": "cancelled", "result": {"reason": "underfilled_attack_roster"}, "resolved_at": now(), "archived_at": now() + timedelta(hours=24)}})
        await system_feed(w["attacker_id"], f"War on node {w['node_id']} cancelled: attack roster underfilled (10 required).")
        return None
    attackers = [s for s in [await _player_snapshot(pid, w["shard_id"], w["attacker_id"]) for pid in w["attack_roster"]] if s]
    defenders = [s for s in [await _player_snapshot(pid, w["shard_id"], w["defender_id"]) for pid in w["defense_roster"]] if s] if w.get("defender_id") else []
    npc_pct = aw["underfilled_defense_npc_fill"]["npc_power_pct_of_alliance_median"]
    median = await _alliance_median(w["defender_id"] or w["attacker_id"], w["shard_id"])
    while len(defenders) < aw["defense_roster_size"]:
        defenders.append({"player_id": None, "display_name": "Garrison" if not w.get("defender_id") else "NPC Defender", "npc": True, "war_power": rnd(median * npc_pct / 100), "defense_pct": 0, "total_power": rnd(median * npc_pct / 100)})
    # defender fortress adjacency bonus
    fort_adj = 0.0
    if w.get("defender_id"):
        adj = await db.alliance_map_nodes.find({"shard_id": w["shard_id"], "node_id": {"$in": neighbors(w["node_id"])}, "owner_alliance_id": w["defender_id"], "type": "fortress"}).to_list(4)
        fort_adj = min(len(adj) * aw["node_types"]["fortress"]["bonus"]["adjacent_defense_power_pct"], aw["node_types"]["fortress"]["stack_cap_pct"])
    snap = {"_id": new_id("snap_"), "war_id": w["_id"], "locked_at": now(), "attackers": attackers, "defenders": defenders, "defender_fortress_adjacent_pct": fort_adj, "node_type": w["node_type"],
            "variance_range": aw["seeded_variance_range"], "seed": w["_id"]}
    await db.war_snapshots.insert_one(snap)
    await db.alliance_wars.update_one({"_id": w["_id"]}, {"$set": {"status": "locked", "locked_at": now(), "snapshot_id": snap["_id"]}})
    return snap


def resolve_lanes(snap: dict) -> dict:
    aw = canon()["alliance_war"]
    lo, hi = aw["seeded_variance_range"]
    att = sorted(snap["attackers"], key=lambda s: -s["war_power"])
    dfd = sorted(snap["defenders"], key=lambda s: -s["war_power"])
    lanes = []
    a_pts = d_pts = 0
    margins = 0.0
    for i in range(aw["attack_roster_size"]):
        rng = seeded_rng(snap["seed"], "lane", i)
        a, d = att[i], dfd[i]
        a_pow = a["war_power"] * (1 + (a.get("fortress_attack_pct", 0) if snap["node_type"] == "fortress" else 0) / 100) * rng.uniform(lo, hi)
        d_pow = d["war_power"] * (1 + (d.get("defense_pct", 0) + snap.get("defender_fortress_adjacent_pct", 0)) / 100) * rng.uniform(lo, hi)
        win = a_pow >= d_pow
        margin = (a_pow - d_pow) / max(a_pow, d_pow, 1)
        margins += margin
        a_pts += 1 if win else 0
        d_pts += 0 if win else 1
        lanes.append({"lane": i + 1, "attacker": a.get("display_name"), "attacker_id": a.get("player_id"), "defender": d.get("display_name"), "defender_id": d.get("player_id"),
                      "attacker_power": rnd(a_pow), "defender_power": rnd(d_pow), "attacker_wins": win, "margin": round(margin, 4)})
    attacker_won = a_pts > d_pts or (a_pts == d_pts and margins > 0)
    return {"lanes": lanes, "attacker_points": a_pts, "defender_points": d_pts, "margin_sum": round(margins, 4), "attacker_won": attacker_won, "tie_break_used": a_pts == d_pts}


async def resolve_war(w: dict) -> dict | None:
    aw = canon()["alliance_war"]
    claimed = await db.alliance_wars.update_one({"_id": w["_id"], "status": "locked"}, {"$set": {"status": "resolving"}})
    if claimed.modified_count == 0:
        return None
    snap = await db.war_snapshots.find_one({"war_id": w["_id"]})
    result = resolve_lanes(snap)
    captured = False
    if result["attacker_won"]:
        res = await db.alliance_map_nodes.update_one({"shard_id": w["shard_id"], "node_id": w["node_id"], "owner_alliance_id": w.get("defender_id")}, {"$set": {"owner_alliance_id": w["attacker_id"], "captured_at": now()}})
        captured = res.modified_count == 1
        if captured and w["node_type"] == "home_castle" and w.get("defender_id"):
            await db.alliances.update_one({"_id": w["defender_id"]}, {"$set": {"home_node": None, "displaced_until": now() + timedelta(hours=12)}})
    winner, loser = (w["attacker_id"], w.get("defender_id")) if result["attacker_won"] else (w.get("defender_id"), w["attacker_id"])
    rw = aw["rewards"]
    if winner:
        await db.alliances.update_one({"_id": winner}, {"$inc": {"season_points": rw["winner_season_points"], "lifetime.wars_won": 1}})
    if loser:
        await db.alliances.update_one({"_id": loser}, {"$inc": {"season_points": rw["loser_season_points"], "lifetime.wars_lost": 1}})
    for side, players in (("attacker", snap["attackers"]), ("defender", snap["defenders"])):
        won = (side == "attacker") == result["attacker_won"]
        for s in players:
            if not s.get("player_id"):
                continue
            coins = rw["participant_war_coins"] + (rw["winner_bonus_war_coins"] if won else 0)
            ops = Ops()
            resources_inc(ops, {"war_coins": coins})
            ops.inc("stats.alliance_war_lanes_or_boss_attacks", 1)
            pl = await db.players.find_one({"_id": s["player_id"]})
            if pl:
                quest_progress(ops, pl, None, "alliance_war_or_boss")
                await ledger.apply_to_player(f"war:{w['_id']}:{s['player_id']}", s["player_id"], "war_reward", ops.build(), {"war_coins": coins, "won": won})
    result.update({"captured": captured, "winner_alliance_id": winner, "resolved_at": now().isoformat()})
    await db.alliance_wars.update_one({"_id": w["_id"]}, {"$set": {"status": "resolved", "result": result, "resolved_at": now(), "archived_at": now() + timedelta(hours=24)}})
    for aid in filter(None, (w["attacker_id"], w.get("defender_id"))):
        await system_feed(aid, f"War on node {w['node_id']} resolved: {'attacker' if result['attacker_won'] else 'defender'} won {result['attacker_points']}-{result['defender_points']}.")
        members = [m["player_id"] for m in await db.alliance_members.find({"alliance_id": aid}).to_list(40)]
        await safe_push(members, {"title": "Alliance War result", "message": f"Node {w['node_id']}: {result['attacker_points']}-{result['defender_points']}", "action_url": "/alliance/war"}, f"war_result:{w['_id']}:{aid}")
    return result


async def tick_wars() -> dict:
    t = now()
    locked = resolved = 0
    async for w in db.alliance_wars.find({"status": "prep", "lock_at": {"$lte": t}}):
        if await lock_war(w):
            locked += 1
    async for w in db.alliance_wars.find({"status": "locked", "resolves_at": {"$lte": t}}):
        if await resolve_war(w):
            resolved += 1
    async for a in db.alliances.find({"home_node": None, "displaced_until": {"$lte": t}, "shard_id": {"$ne": None}}):
        node = await db.alliance_map_nodes.find_one_and_update({"shard_id": a["shard_id"], "type": "wilderness", "owner_alliance_id": None}, {"$set": {"owner_alliance_id": a["_id"], "type": "home_castle", "captured_at": t}})
        if node:
            await db.alliances.update_one({"_id": a["_id"]}, {"$set": {"home_node": node["node_id"], "displaced_until": None}})
            await system_feed(a["_id"], f"Relocated to a new home castle at node {node['node_id']}.")
    return {"locked": locked, "resolved": resolved}


async def war_detail(p: dict, war_id: str) -> dict:
    w = await db.alliance_wars.find_one({"_id": war_id})
    if not w:
        raise fail(404, "war_not_found")
    snap = await db.war_snapshots.find_one({"war_id": war_id}) if w.get("snapshot_id") else None
    names = {}
    for aid in filter(None, (w["attacker_id"], w.get("defender_id"))):
        a = await db.alliances.find_one({"_id": aid}, {"name": 1, "tag": 1})
        names[aid] = {"name": a["name"], "tag": a["tag"]} if a else None
    roster_players = {}
    for pid in w["attack_roster"] + w["defense_roster"]:
        pl = await db.players.find_one({"_id": pid}, {"display_name": 1, "hero.level": 1})
        if pl:
            roster_players[pid] = {"display_name": pl["display_name"], "hero_level": pl["hero"]["level"]}
    return {"war": clean(w), "alliances": names, "roster_players": roster_players, "snapshot": clean(snap) if snap else None, "server_time": now().isoformat()}


async def list_wars(p: dict) -> dict:
    me = await membership(p["_id"])
    if not me:
        return {"wars": [], "alliance_id": None}
    rows = await db.alliance_wars.find({"$or": [{"attacker_id": me["alliance_id"]}, {"defender_id": me["alliance_id"]}]}).sort("declared_at", -1).limit(20).to_list(20)
    return {"wars": [clean(w) for w in rows], "alliance_id": me["alliance_id"], "server_time": now().isoformat()}


# ---- Titan Hunt --------------------------------------------------------------------------------------------------
async def boss_view(p: dict) -> dict:
    me = await membership(p["_id"])
    if not me:
        return {"run": None, "alliance_id": None}
    ab = canon()["events"]["alliance_boss"]
    run = await db.alliance_boss_runs.find_one({"alliance_id": me["alliance_id"], "status": {"$in": ["active", "killed"]}}, sort=[("started_at", -1)])
    if run and run["status"] == "active" and aware(run["ends_at"]) <= now():
        await db.alliance_boss_runs.update_one({"_id": run["_id"], "status": "active"}, {"$set": {"status": "expired"}})
        run["status"] = "expired"
    today = now().strftime("%Y-%m-%d")
    mine = (run or {}).get("attacks", {}).get(p["_id"], {}) if run else {}
    my_today = mine.get(today, {"free": 0, "paid": 0})
    return {"alliance_id": me["alliance_id"], "my_role": me["role"], "rules": {k: ab[k] for k in ("name", "duration_hours", "free_attacks_per_day", "extra_attack_rubies", "paid_extra_attacks_cap_per_day", "tier_range", "alliance_kill_chest_thresholds_pct", "personal_attack_reward", "kill_reward_per_participant")},
            "run": clean(run) if run else None, "my_attacks_today": my_today, "my_damage": mine.get("damage", 0), "server_time": now().isoformat(),
            "tier_hp": {t: F.boss_hp(t) for t in range(ab["tier_range"][0], ab["tier_range"][1] + 1)}}


async def start_boss(p: dict, tier: int) -> dict:
    ab = canon()["events"]["alliance_boss"]
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "officer_required")
    if not (ab["tier_range"][0] <= tier <= ab["tier_range"][1]):
        raise fail(400, "bad_tier")
    if await db.alliance_boss_runs.find_one({"alliance_id": me["alliance_id"], "status": "active", "ends_at": {"$gt": now()}}):
        raise fail(409, "boss_active")
    run = {"_id": new_id("boss_"), "alliance_id": me["alliance_id"], "tier": tier, "hp_max": F.boss_hp(tier), "hp": F.boss_hp(tier), "started_at": now(), "ends_at": now() + timedelta(hours=ab["duration_hours"]),
           "status": "active", "attacks": {}, "thresholds_hit": [], "participants": []}
    await db.alliance_boss_runs.insert_one(run)
    await system_feed(me["alliance_id"], f"Titan Hunt tier {tier} has begun! 48 hours to bring it down.")
    return clean(run)


async def attack_boss(p: dict) -> dict:
    ab = canon()["events"]["alliance_boss"]
    me = await membership(p["_id"])
    if not me:
        raise fail(404, "not_member")
    run = await db.alliance_boss_runs.find_one({"alliance_id": me["alliance_id"], "status": "active", "ends_at": {"$gt": now()}})
    if not run:
        raise fail(404, "no_active_boss")
    today = now().strftime("%Y-%m-%d")
    mine = {"free": 0, "paid": 0, **run.get("attacks", {}).get(p["_id"], {}).get(today, {})}
    paid = False
    if mine["free"] < ab["free_attacks_per_day"]:
        field = f"attacks.{p['_id']}.{today}.free"
    elif mine["paid"] < ab["paid_extra_attacks_cap_per_day"]:
        field = f"attacks.{p['_id']}.{today}.paid"
        paid = True
    else:
        raise fail(409, "no_attacks_left")
    prof = await combat_profile(p)
    dmg = F.boss_attack_damage(prof["total_power"])
    attack_id = new_id("batk_")
    ops = Ops()
    if paid:
        ops.inc("resources.rubies", -ab["extra_attack_rubies"])
    resources_inc(ops, ab["personal_attack_reward"])
    ops.inc("stats.alliance_war_lanes_or_boss_attacks", 1)
    quest_progress(ops, p, "alliance_action", "alliance_war_or_boss")
    flt = {"resources.rubies": {"$gte": ab["extra_attack_rubies"]}} if paid else None
    await ledger.apply_to_player(f"bossatk:{attack_id}", p["_id"], "boss_attack", ops.build(), {"damage": dmg, "paid": paid}, extra_filter=flt)
    upd = await db.alliance_boss_runs.find_one_and_update(
        {"_id": run["_id"], "status": "active"},
        {"$inc": {"hp": -dmg, field: 1, f"attacks.{p['_id']}.damage": dmg}, "$addToSet": {"participants": p["_id"]}, "$push": {"log": {"$each": [{"player_id": p["_id"], "name": p["display_name"], "damage": dmg, "at": now()}], "$slice": -50}}},
        return_document=True,
    )
    if not upd:
        raise fail(409, "boss_changed")
    dealt = upd["hp_max"] - max(upd["hp"], 0)
    pct = 100 * dealt / upd["hp_max"]
    hit = [t for t in ab["alliance_kill_chest_thresholds_pct"] if pct >= t and t not in upd.get("thresholds_hit", [])]
    if hit:
        await db.alliance_boss_runs.update_one({"_id": run["_id"]}, {"$addToSet": {"thresholds_hit": {"$each": hit}}})
    killed = False
    if upd["hp"] <= 0:
        k = await db.alliance_boss_runs.update_one({"_id": run["_id"], "status": "active"}, {"$set": {"status": "killed", "killed_at": now()}})
        if k.modified_count:
            killed = True
            await db.alliances.update_one({"_id": me["alliance_id"]}, {"$inc": {"lifetime.bosses_killed": 1}})
            for pid in upd["participants"]:
                o = Ops()
                resources_inc(o, ab["kill_reward_per_participant"])
                await ledger.apply_to_player(f"bosskill:{run['_id']}:{pid}", pid, "boss_kill", o.build(), ab["kill_reward_per_participant"])
            await system_feed(me["alliance_id"], f"The Titan (tier {run['tier']}) has been slain! Kill rewards delivered to {len(upd['participants'])} hunters.")
    return {"damage": dmg, "paid": paid, "boss_hp": max(upd["hp"], 0), "boss_hp_max": upd["hp_max"], "progress_pct": round(min(100, pct), 2), "thresholds_hit": sorted(set(upd.get("thresholds_hit", []) + hit)), "killed": killed,
            "personal_reward": ab["personal_attack_reward"]}
