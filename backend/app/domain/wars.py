"""Async 10v10 territory war on a 19x19 season map + Titan Hunt alliance boss (I13)."""
import statistics
from datetime import timedelta

from ..core import db, ledger
from ..core.canon import canon, units_by_key
from ..core.push import safe_push
from ..core.util import aware, clean, fail, new_id, now, rnd, seeded_rng
from . import formulas as F
from .liveops import season_bounds, season_key
from .player import combat_profile, research_pct
from .progress import Ops, quest_progress, resources_inc
from .social import alliance_alert, membership, role_rank, system_feed

N = 19
NODE_LABEL_IT = {"wilderness": "Terre selvagge", "village": "Villaggio", "town": "Borgo", "mine": "Miniera", "fortress": "Fortezza", "city": "Città", "home_castle": "Castello"}


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
    # v1.5: tell the client up-front why the alliance cannot attack (and which nodes are valid targets) so the UI can explain in Italian
    attack_state: dict = {"can_attack": False, "reason": None, "cooldown_ends_at": None, "attackable_node_ids": []}
    if a:
        aw = canon()["alliance_war"]
        members = await db.alliance_members.count_documents({"alliance_id": a["_id"]})
        last = await db.alliance_wars.find_one({"attacker_id": a["_id"], "declared_at": {"$gte": now() - timedelta(hours=aw["attack_limit_per_alliance_hours"])}}, sort=[("declared_at", -1)])
        mine_active = next((w for w in wars if a["_id"] in (w["attacker_id"], w.get("defender_id"))), None)
        if role_rank(me["role"]) < 2:
            attack_state["reason"] = "officer_required"
        elif a.get("displaced_until") and aware(a["displaced_until"]) > now():
            attack_state["reason"] = "displaced"
        elif members < canon()["alliances"]["minimum_members_to_attack"]:
            attack_state["reason"] = "min_members"
        elif last:
            attack_state["reason"] = "attack_cooldown"
            attack_state["cooldown_ends_at"] = (aware(last["declared_at"]) + timedelta(hours=aw["attack_limit_per_alliance_hours"])).isoformat()
        elif mine_active:
            attack_state["reason"] = "war_active"
            attack_state["active_war_id"] = mine_active["_id"]
        else:
            attack_state["can_attack"] = True
        owned = {n["node_id"] for n in nodes if n["owner_alliance_id"] == a["_id"]}
        contested = {w["node_id"] for w in wars}
        busy = {w["attacker_id"] for w in wars} | {w.get("defender_id") for w in wars}
        attack_state["attackable_node_ids"] = [n["node_id"] for n in nodes if n["owner_alliance_id"] != a["_id"] and n["node_id"] not in contested
                                              and any(nb in owned for nb in neighbors(n["node_id"])) and (not n["owner_alliance_id"] or n["owner_alliance_id"] not in busy)]
        attack_state["members"] = members
        npc_pct = aw["underfilled_defense_npc_fill"]["npc_power_pct_of_alliance_median"]
        attack_state["garrison_lane_power"] = rnd(await _alliance_median(a["_id"], shard_id) * npc_pct / 100)
        attack_state["garrison_pct_of_median"] = npc_pct
    return {
        "shard_id": shard_id, "size": N, "season": {"key": season_key(), "starts_at": start.isoformat(), "ends_at": end.isoformat()},
        "nodes": [{"node_id": n["node_id"], "x": n["x"], "y": n["y"], "type": n["type"], "owner": n["owner_alliance_id"], "bonus": n["bonus"]} for n in nodes],
        "alliances": {k: {"name": v["name"], "tag": v["tag"], "season_points": v.get("season_points", 0), "home_node": v.get("home_node")} for k, v in als.items()},
        "my_alliance_id": a["_id"] if a else None, "my_home": a.get("home_node") if a else None, "attack_state": attack_state,
        "active_wars": [clean(w) for w in wars], "territory_bonus": await territory_bonus(a["_id"] if a else None, shard_id),
        "rules": {**{k: canon()["alliance_war"][k] for k in ("prep_hours", "roster_lock_minutes_before_resolution", "attack_roster_size", "defense_roster_size", "attack_limit_per_alliance_hours", "rewards", "tie_break", "target_rule")},
                  "minimum_members_to_attack": canon()["alliances"]["minimum_members_to_attack"]},
        "leaderboard": [{"alliance_id": x["_id"], "name": x["name"], "tag": x["tag"], "season_points": x.get("season_points", 0)} for x in await db.alliances.find({"shard_id": shard_id}).sort("season_points", -1).limit(20).to_list(20)],
    }


async def declare(p: dict, node_id: int) -> dict:
    aw = canon()["alliance_war"]
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "officer_required", "Solo il leader e gli ufficiali possono farlo")
    a = await ensure_alliance_on_map(await db.alliances.find_one({"_id": me["alliance_id"]}))
    if a.get("displaced_until") and aware(a["displaced_until"]) > now():
        raise fail(409, "displaced", "L'alleanza si sta ricollocando dopo aver perso il castello: attendi 12 ore")
    if await db.alliance_members.count_documents({"alliance_id": a["_id"]}) < canon()["alliances"]["minimum_members_to_attack"]:
        raise fail(403, "min_members", f"Servono almeno {canon()['alliances']['minimum_members_to_attack']} membri per attaccare")
    last = await db.alliance_wars.find_one({"attacker_id": a["_id"], "declared_at": {"$gte": now() - timedelta(hours=aw["attack_limit_per_alliance_hours"])}})
    if last:
        raise fail(409, "attack_cooldown", "Un solo attacco ogni 24 ore per alleanza")
    if await db.alliance_wars.find_one({"status": {"$in": ["prep", "locked"]}, "$or": [{"attacker_id": a["_id"]}, {"defender_id": a["_id"]}]}):
        raise fail(409, "war_active", "La tua alleanza è già impegnata in una guerra (in preparazione o bloccata)")
    node = await db.alliance_map_nodes.find_one({"shard_id": a["shard_id"], "node_id": node_id})
    if not node:
        raise fail(404, "node_not_found", "Nodo non trovato")
    if node["owner_alliance_id"] == a["_id"]:
        raise fail(400, "own_node", "Questo nodo è già tuo")
    owned = {n["node_id"] for n in await db.alliance_map_nodes.find({"shard_id": a["shard_id"], "owner_alliance_id": a["_id"]}, {"node_id": 1}).to_list(400)}
    if not any(nb in owned for nb in neighbors(node_id)):
        raise fail(400, "not_adjacent", "Puoi attaccare solo nodi adiacenti al tuo territorio")
    if await db.alliance_wars.find_one({"shard_id": a["shard_id"], "node_id": node_id, "status": {"$in": ["prep", "locked"]}}):
        raise fail(409, "node_contested", "Su questo nodo c'è già una guerra in corso")
    defender_id = node["owner_alliance_id"]
    if defender_id and await db.alliance_wars.find_one({"status": {"$in": ["prep", "locked"]}, "$or": [{"attacker_id": defender_id}, {"defender_id": defender_id}]}):
        raise fail(409, "defender_busy", "L'alleanza difensore è già impegnata in un'altra guerra")
    resolves = now() + timedelta(hours=aw["prep_hours"])
    war = {"_id": new_id("war_"), "shard_id": a["shard_id"], "node_id": node_id, "node_type": node["type"], "attacker_id": a["_id"], "defender_id": defender_id, "declared_by": p["_id"],
           "declared_at": now(), "resolves_at": resolves, "lock_at": resolves - timedelta(minutes=aw["roster_lock_minutes_before_resolution"]), "status": "prep",
           "attack_roster": [p["_id"]], "defense_roster": [], "attack_reserve": [], "defense_reserve": [], "result": None, "archived_at": None}  # the declarer books the first slot
    await db.alliance_wars.insert_one(war)
    label = NODE_LABEL_IT.get(node["type"], node["type"])
    await alliance_alert(a["_id"], f"⚔️ {p['display_name']} ha dichiarato guerra al nodo {node_id} ({label}). Prenotatevi: i primi 10 schierano le truppe (1/10 già prenotato).")
    members = [m["player_id"] for m in await db.alliance_members.find({"alliance_id": a["_id"]}).to_list(40)]
    await safe_push(members, {"title": "Alliance War", "message": f"War declared on node {node_id}. Set the roster before lock.", "action_url": "/alliance/war"}, f"war_roster:{war['_id']}")
    if defender_id:
        await alliance_alert(defender_id, f"🛡️ Il nodo {node_id} ({label}) è sotto attacco da [{a['tag']}] {a['name']}! Prenotatevi in difesa: i primi 10 schierano le truppe.")
        dmembers = [m["player_id"] for m in await db.alliance_members.find({"alliance_id": defender_id}).to_list(40)]
        await safe_push(dmembers, {"title": "Alliance War", "message": f"Node {node_id} is under attack. Set the defense roster.", "action_url": "/alliance/war"}, f"war_defend:{war['_id']}")
    return clean(war)


async def _war_side(p: dict, war_id: str) -> tuple[dict, dict, str, int]:
    """(membership, war, roster field, roster size) for a player of one of the two alliances; war must be open (prep, before lock)."""
    aw = canon()["alliance_war"]
    me = await membership(p["_id"])
    if not me:
        raise fail(403, "not_in_alliance", "Non sei in un'alleanza")
    w = await db.alliance_wars.find_one({"_id": war_id})
    if not w or w["status"] != "prep":
        raise fail(409, "war_not_open", "La guerra non è più in preparazione")
    if aware(w["lock_at"]) <= now():
        raise fail(409, "roster_locked", "Schieramento bloccato: mancano meno di 30 minuti alla risoluzione")
    side = "attack_roster" if w["attacker_id"] == me["alliance_id"] else "defense_roster" if w.get("defender_id") == me["alliance_id"] else None
    if not side:
        raise fail(403, "not_in_war", "La tua alleanza non partecipa a questa guerra")
    return me, w, side, aw["attack_roster_size"] if side == "attack_roster" else aw["defense_roster_size"]


async def enlist(p: dict, war_id: str) -> dict:
    """First come, first served: a member books one of the 10 slots of their alliance's side (atomic size check + $addToSet).
    When the roster is full the member joins the RESERVE queue and is promoted automatically if someone withdraws."""
    me, w, side, size = await _war_side(p, war_id)
    reserve = side.replace("roster", "reserve")
    if p["_id"] in w[side]:
        raise fail(409, "already_enlisted", "Sei già schierato")
    if p["_id"] in w.get(reserve, []):
        raise fail(409, "already_reserve", "Sei già in riserva")
    res = await db.alliance_wars.update_one({"_id": war_id, "status": "prep", side: {"$ne": p["_id"]}, "$expr": {"$lt": [{"$size": f"${side}"}, size]}}, {"$addToSet": {side: p["_id"]}})
    if res.matched_count == 0:
        await db.alliance_wars.update_one({"_id": war_id, "status": "prep"}, {"$addToSet": {reserve: p["_id"]}})
        w = await db.alliance_wars.find_one({"_id": war_id})
        pos = w[reserve].index(p["_id"]) + 1
        await alliance_alert(me["alliance_id"], f"⏳ {p['display_name']} è in riserva n.{pos} per il nodo {w['node_id']}: entra in campo se qualcuno si ritira.")
        return {"war_id": war_id, side: w[side], reserve: w[reserve], "enlisted": False, "reserve": True, "reserve_position": pos}
    w = await db.alliance_wars.find_one({"_id": war_id})
    n = len(w[side])
    await alliance_alert(me["alliance_id"], f"{'⚔️' if side == 'attack_roster' else '🛡️'} {p['display_name']} si è prenotato per il nodo {w['node_id']} ({n}/{size}){' · roster completo!' if n >= size else ''}")
    return {"war_id": war_id, side: w[side], reserve: w.get(reserve, []), "enlisted": True, "reserve": False}


async def withdraw(p: dict, war_id: str) -> dict:
    """Leave the roster (the first reserve is promoted automatically) or leave the reserve queue."""
    me, w, side, size = await _war_side(p, war_id)
    reserve = side.replace("roster", "reserve")
    if p["_id"] in w.get(reserve, []):
        await db.alliance_wars.update_one({"_id": war_id}, {"$pull": {reserve: p["_id"]}})
        w = await db.alliance_wars.find_one({"_id": war_id})
        return {"war_id": war_id, side: w[side], reserve: w.get(reserve, []), "enlisted": False, "reserve": False}
    if p["_id"] not in w[side]:
        raise fail(409, "not_enlisted", "Non sei arruolato in questa guerra")
    await db.alliance_wars.update_one({"_id": war_id, "status": "prep"}, {"$pull": {side: p["_id"]}})
    promoted = None
    for cand in w.get(reserve, []):
        # promote the first reserve still available; atomic guard keeps the roster within `size`
        r = await db.alliance_wars.update_one({"_id": war_id, "status": "prep", side: {"$ne": cand}, "$expr": {"$lt": [{"$size": f"${side}"}, size]}}, {"$addToSet": {side: cand}, "$pull": {reserve: cand}})
        if r.matched_count:
            promoted = cand
            break
    w = await db.alliance_wars.find_one({"_id": war_id})
    msg = f"↩️ {p['display_name']} si è ritirato dal roster del nodo {w['node_id']} ({len(w[side])}/{size})."
    if promoted:
        pl = await db.players.find_one({"_id": promoted}, {"display_name": 1})
        msg += f" ⬆️ {pl['display_name'] if pl else 'Una riserva'} entra in campo dalla riserva!"
    else:
        msg += " Posto libero!"
    await alliance_alert(me["alliance_id"], msg)
    return {"war_id": war_id, side: w[side], reserve: w.get(reserve, []), "enlisted": False, "reserve": False, "promoted": promoted}


async def set_roster(p: dict, war_id: str, player_ids: list[str]) -> dict:
    aw = canon()["alliance_war"]
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "officer_required", "Solo il leader e gli ufficiali possono farlo")
    w = await db.alliance_wars.find_one({"_id": war_id})
    if not w or w["status"] != "prep":
        raise fail(409, "war_not_open", "La guerra non è più in preparazione")
    if aware(w["lock_at"]) <= now():
        raise fail(409, "roster_locked", "Schieramento bloccato: mancano meno di 30 minuti alla risoluzione")
    side = "attack_roster" if w["attacker_id"] == me["alliance_id"] else "defense_roster" if w.get("defender_id") == me["alliance_id"] else None
    if not side:
        raise fail(403, "not_in_war", "La tua alleanza non partecipa a questa guerra")
    size = aw["attack_roster_size"] if side == "attack_roster" else aw["defense_roster_size"]
    ids = list(dict.fromkeys(player_ids))
    if len(ids) > size:
        raise fail(400, "roster_size", f"Max {size} players")
    members = {m["player_id"] for m in await db.alliance_members.find({"alliance_id": me["alliance_id"]}).to_list(40)}
    if any(i not in members for i in ids):
        raise fail(400, "not_members", "Alcuni giocatori scelti non sono membri dell'alleanza")
    await db.alliance_wars.update_one({"_id": war_id, "status": "prep"}, {"$set": {side: ids}})
    await alliance_alert(me["alliance_id"], f"📜 {p['display_name']} ha salvato il roster di {'attacco' if side == 'attack_roster' else 'difesa'} per il nodo {w['node_id']}: {len(ids)}/{size} guerrieri.")
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
        "army_per_unit": prof["army_per_unit"], "army_class_mix": F.army_class_mix(p["army"]["formation"]), "roster_pct": roster_pct,
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
    if len(w["attack_roster"]) == 0:
        await db.alliance_wars.update_one({"_id": w["_id"]}, {"$set": {"status": "cancelled", "result": {"reason": "empty_attack_roster"}, "resolved_at": now(), "archived_at": now() + timedelta(hours=24)}})
        await alliance_alert(w["attacker_id"], f"❌ Guerra sul nodo {w['node_id']} annullata: nessun guerriero prenotato per l'attacco.")
        return None
    attackers = [s for s in [await _player_snapshot(pid, w["shard_id"], w["attacker_id"]) for pid in w["attack_roster"]] if s]
    # an under-filled attack is allowed but disadvantaged: every missing attacker is an empty lane that is lost automatically
    while len(attackers) < aw["attack_roster_size"]:
        attackers.append({"player_id": None, "display_name": "Corsia vuota", "npc": True, "empty": True, "war_power": 0, "total_power": 0, "defense_pct": 0})
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
    for aid in filter(None, (w["attacker_id"], w.get("defender_id"))):
        await alliance_alert(aid, f"🔒 Roster bloccato per il nodo {w['node_id']}: schieramenti congelati, risoluzione tra {aw['roster_lock_minutes_before_resolution']} minuti.")
    return snap


def lane_power(s: dict, opp: dict) -> tuple[float, float]:
    """(power, counter %) of one roster entry against its lane opponent: army re-evaluated with v1.2 unit counters vs the opponent's
    deployed class mix. NPC entries and snapshots without army detail keep their frozen war_power."""
    if s.get("npc") or "army_per_unit" not in s:
        return float(s["war_power"]), 0.0
    mix = None if opp.get("npc") else opp.get("army_class_mix")
    base_army = sum(s["army_per_unit"].values())
    army = sum(v * (1 + F.unit_counter_pct(k, mix) / 100) for k, v in s["army_per_unit"].items())
    pct = (army / base_army - 1) * 100 if base_army else 0.0
    return (s["hero_power"] + army) * (1 + s.get("roster_pct", 0) / 100), pct


def lane_casualties(entry: dict, won: bool, own_pow: float, opp_pow: float, is_defender: bool) -> dict | None:
    """Canon v1.5 alliance_war.casualties: permanent losses of the deployed troops of one lane duel.
    rate = 0.05 + 0.20*r (winner) or 0.30 + 0.30*(1-r) (loser), r = min/max of the final lane powers; x0.85 for defenders;
    x category multiplier; lost = min(floor(deployed*rate), deployed). NPC/empty entries have nothing to lose."""
    cw = canon()["alliance_war"].get("casualties")
    if not cw or not cw.get("enabled") or entry.get("npc") or not entry.get("player_id"):
        return None
    r = min(own_pow, opp_pow) / max(own_pow, opp_pow, 1e-9)
    rate = (0.05 + 0.20 * r) if won else (0.30 + 0.30 * (1 - r))
    if is_defender:
        rate *= cw["defender_multiplier"]
    units = units_by_key()
    out = {}
    for k, q in (entry.get("deployed_army") or {}).items():
        q = int(q or 0)
        if k in units and q > 0:
            uk = rate * cw["category_multiplier"].get(units[k]["category"], 1.0)
            lost = min(int(q * uk), q)
            out[k] = {"deployed": q, "lost": lost, "survived": q - lost, "rate_pct": round(uk * 100, 1)}
    return {"player_id": entry["player_id"], "won": won, "ratio": round(r, 3), "rate_pct": round(rate * 100, 1), "units": out,
            "deployed_total": sum(v["deployed"] for v in out.values()), "lost_total": sum(v["lost"] for v in out.values())}


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
        a_base, a_cpct = lane_power(a, d)
        d_base, d_cpct = lane_power(d, a)
        a_pow = a_base * (1 + (a.get("fortress_attack_pct", 0) if snap["node_type"] == "fortress" else 0) / 100) * rng.uniform(lo, hi)
        d_pow = d_base * (1 + (d.get("defense_pct", 0) + snap.get("defender_fortress_adjacent_pct", 0)) / 100) * rng.uniform(lo, hi)
        win = a_pow >= d_pow
        margin = (a_pow - d_pow) / max(a_pow, d_pow, 1)
        margins += margin
        a_pts += 1 if win else 0
        d_pts += 0 if win else 1
        # v1.5 casualties: nobody fights (or loses troops) against an empty lane
        a_cas = lane_casualties(a, win, a_pow, d_pow, False) if not d.get("empty") else None
        d_cas = lane_casualties(d, not win, d_pow, a_pow, True) if not a.get("empty") else None
        lanes.append({"lane": i + 1, "attacker": a.get("display_name"), "attacker_id": a.get("player_id"), "defender": d.get("display_name"), "defender_id": d.get("player_id"),
                      "attacker_level": a.get("hero_level"), "defender_level": d.get("hero_level"), "attacker_npc": bool(a.get("npc")), "defender_npc": bool(d.get("npc")),
                      "attacker_power": rnd(a_pow), "defender_power": rnd(d_pow), "attacker_counter_pct": round(a_cpct, 1), "defender_counter_pct": round(d_cpct, 1),
                      "attacker_wins": win, "margin": round(margin, 4), "attacker_casualties": a_cas, "defender_casualties": d_cas})
    attacker_won = a_pts > d_pts or (a_pts == d_pts and margins > 0)
    return {"lanes": lanes, "attacker_points": a_pts, "defender_points": d_pts, "margin_sum": round(margins, 4), "attacker_won": attacker_won, "tie_break_used": a_pts == d_pts}


async def apply_casualties(war_id: str, result: dict) -> dict:
    """Deduct the lane casualties from each player's army exactly once (ledger key war_losses:<war>:<player>), never above the
    deployed or currently owned quantities; clamp the formation to the survivors. The war snapshot is never touched."""
    summary: dict = {}
    for lane in result["lanes"]:
        for side in ("attacker", "defender"):
            cas = lane.get(f"{side}_casualties")
            if not cas:
                continue
            pid = cas["player_id"]
            pl = await db.players.find_one({"_id": pid}, {"army": 1})
            if not pl:
                continue
            ops = Ops()
            applied = {}
            for k, v in cas["units"].items():
                owned = int(pl["army"]["units"].get(k, 0))
                lost = max(0, min(v["lost"], owned))
                applied[k] = {**v, "lost": lost, "survived": v["deployed"] - lost}
                if lost > 0:
                    ops.inc(f"army.units.{k}", -lost)
                    if pl["army"]["formation"].get(k, 0) > owned - lost:
                        if owned - lost > 0:
                            ops.set(f"army.formation.{k}", owned - lost)
                        else:
                            ops.unset(f"army.formation.{k}")
            entry = {**cas, "side": side, "lane": lane["lane"], "units": applied, "lost_total": sum(v["lost"] for v in applied.values())}
            inf = canon()["alliance_war"]["casualties"].get("infirmary")
            if inf:  # v1.6 Infirmary: a share of the fallen comes back after `hours`
                back = {k: int(v["lost"] * inf["return_pct"] / 100) for k, v in applied.items() if int(v["lost"] * inf["return_pct"] / 100) > 0}
                entry["infirmary"] = {"units": back, "total": sum(back.values()), "ready_at": (now() + timedelta(hours=inf["hours"])).isoformat()}
                if back:
                    ops.push("army.infirmary", {"war_id": war_id, "units": back, "ready_at": now() + timedelta(hours=inf["hours"])})
            await ledger.apply_to_player(f"war_losses:{war_id}:{pid}", pid, "war_losses", ops.build(), entry)
            summary[pid] = entry
    return summary


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
    result["casualties"] = await apply_casualties(w["_id"], result)
    result.update({"captured": captured, "winner_alliance_id": winner, "resolved_at": now().isoformat()})
    await db.alliance_wars.update_one({"_id": w["_id"]}, {"$set": {"status": "resolved", "result": result, "resolved_at": now(), "archived_at": now() + timedelta(hours=24)}})
    for aid in filter(None, (w["attacker_id"], w.get("defender_id"))):
        mine_won = (aid == w["attacker_id"]) == result["attacker_won"]
        side = "attacker" if aid == w["attacker_id"] else "defender"
        cas = [c for c in result["casualties"].values() if c["side"] == side]
        lost = sum(c["lost_total"] for c in cas)
        dep = sum(c["deployed_total"] for c in cas)
        await alliance_alert(aid, f"{'🏆 VITTORIA' if mine_won else '💀 SCONFITTA'} sul nodo {w['node_id']}: {'attaccante' if result['attacker_won'] else 'difensore'} vince {result['attacker_points']}-{result['defender_points']}"
                             f"{' · nodo conquistato' if captured else ''}{' · spareggio sui margini' if result['tie_break_used'] else ''}."
                             f"{f' ⚰ Perdite: {lost:,} unità cadute su {dep:,} schierate ({dep - lost:,} superstiti).'.replace(',', '.') if dep else ''}")
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
        raise fail(404, "war_not_found", "Guerra non trovata")
    snap = await db.war_snapshots.find_one({"war_id": war_id}) if w.get("snapshot_id") else None
    names = {}
    for aid in filter(None, (w["attacker_id"], w.get("defender_id"))):
        a = await db.alliances.find_one({"_id": aid}, {"name": 1, "tag": 1})
        names[aid] = {"name": a["name"], "tag": a["tag"]} if a else None
    roster_players = {}
    me = await membership(p["_id"])
    my_aid = me["alliance_id"] if me else None
    my_side = "attack" if my_aid and my_aid == w["attacker_id"] else "defense" if my_aid and my_aid == w.get("defender_id") else None
    mine_ids = set(w[f"{my_side}_roster"] + w.get(f"{my_side}_reserve", [])) if my_side else set()
    for pid in w["attack_roster"] + w["defense_roster"] + w.get("attack_reserve", []) + w.get("defense_reserve", []):
        pl = await db.players.find_one({"_id": pid}, {"display_name": 1, "hero.level": 1})
        if pl:
            roster_players[pid] = {"display_name": pl["display_name"], "hero_level": pl["hero"]["level"]}
            if pid in mine_ids:  # war power is shown ONLY for the requester's own team, never for the enemy
                snap_p = await _player_snapshot(pid, w["shard_id"], my_aid)
                roster_players[pid]["war_power"] = snap_p["war_power"] if snap_p else 0
    team_power = sum(roster_players[pid].get("war_power", 0) for pid in (w[f"{my_side}_roster"] if my_side else []) if pid in roster_players)
    cas = (w.get("result") or {}).get("casualties") or {}
    my_team = [c for c in cas.values() if my_side and c["side"] == ("attacker" if my_side == "attack" else "defender")]
    team_casualties = {"deployed": sum(c["deployed_total"] for c in my_team), "lost": sum(c["lost_total"] for c in my_team),
                       "players": [{"player_id": c["player_id"], "display_name": roster_players.get(c["player_id"], {}).get("display_name"), "lane": c["lane"], "won": c["won"],
                                    "rate_pct": c["rate_pct"], "deployed": c["deployed_total"], "lost": c["lost_total"]} for c in sorted(my_team, key=lambda c: c["lane"])]} if my_team else None
    return {"war": clean(w), "alliances": names, "roster_players": roster_players, "my_side": my_side, "team_power": team_power, "snapshot": clean(snap) if snap else None,
            "my_casualties": cas.get(p["_id"]), "team_casualties": team_casualties, "server_time": now().isoformat()}


async def list_wars(p: dict) -> dict:
    me = await membership(p["_id"])
    if not me:
        return {"wars": [], "alliance_id": None}
    rows = await db.alliance_wars.find({"$or": [{"attacker_id": me["alliance_id"]}, {"defender_id": me["alliance_id"]}]}).sort("declared_at", -1).limit(20).to_list(20)
    return {"wars": [clean(w) for w in rows], "alliance_id": me["alliance_id"], "server_time": now().isoformat()}


# ---- Titan Hunt --------------------------------------------------------------------------------------------------
def titan_family(tier: int) -> str:
    """The Titan of tier t is the region boss of region t (canon regions 1..10)."""
    regions = canon()["battle"]["regions"]
    return regions[max(0, min(len(regions) - 1, tier - 1))]["region_boss"]


async def boss_leaderboard(run: dict | None) -> list[dict]:
    if not run:
        return []
    attacks = run.get("attacks", {})
    rows = [(pid, v.get("damage", 0)) for pid, v in attacks.items()]
    names = {p["_id"]: p for p in await db.players.find({"_id": {"$in": [pid for pid, _ in rows]}}, {"display_name": 1, "hero.level": 1}).to_list(60)}
    out = sorted(({"player_id": pid, "display_name": names.get(pid, {}).get("display_name", "?"), "hero_level": names.get(pid, {}).get("hero", {}).get("level"), "damage": dmg,
                   "attacks": sum(d.get("free", 0) + d.get("paid", 0) for k, d in attacks[pid].items() if k != "damage")} for pid, dmg in rows), key=lambda x: -x["damage"])
    for i, r in enumerate(out):
        r["rank"] = i + 1
        r["share_pct"] = round(100 * r["damage"] / max(1, run["hp_max"] - max(0, run["hp"])), 1) if run["hp_max"] > max(0, run["hp"]) else 0.0
    return out


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
            "titan_family": titan_family(run["tier"]) if run else None, "tier_families": {t: titan_family(t) for t in range(ab["tier_range"][0], ab["tier_range"][1] + 1)},
            "leaderboard": await boss_leaderboard(run), "my_player_id": p["_id"],
            "tier_hp": {t: F.boss_hp(t) for t in range(ab["tier_range"][0], ab["tier_range"][1] + 1)}}


async def start_boss(p: dict, tier: int) -> dict:
    ab = canon()["events"]["alliance_boss"]
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "officer_required", "Solo il leader e gli ufficiali possono farlo")
    if not (ab["tier_range"][0] <= tier <= ab["tier_range"][1]):
        raise fail(400, "bad_tier", "Livello del Titano non valido")
    if await db.alliance_boss_runs.find_one({"alliance_id": me["alliance_id"], "status": "active", "ends_at": {"$gt": now()}}):
        raise fail(409, "boss_active", "C'è già una caccia al Titano attiva")
    run = {"_id": new_id("boss_"), "alliance_id": me["alliance_id"], "tier": tier, "hp_max": F.boss_hp(tier), "hp": F.boss_hp(tier), "started_at": now(), "ends_at": now() + timedelta(hours=ab["duration_hours"]),
           "status": "active", "attacks": {}, "thresholds_hit": [], "participants": []}
    await db.alliance_boss_runs.insert_one(run)
    await alliance_alert(me["alliance_id"], f"🐲 {p['display_name']} ha iniziato la Titan Hunt tier {tier}: {titan_family(tier)} ({F.boss_hp(tier):,} HP). 48 ore per abbatterlo!", kind="titan")
    return clean(run)


async def attack_boss(p: dict) -> dict:
    ab = canon()["events"]["alliance_boss"]
    me = await membership(p["_id"])
    if not me:
        raise fail(404, "not_member")
    run = await db.alliance_boss_runs.find_one({"alliance_id": me["alliance_id"], "status": "active", "ends_at": {"$gt": now()}})
    if not run:
        raise fail(404, "no_active_boss", "Nessuna caccia al Titano attiva")
    today = now().strftime("%Y-%m-%d")
    mine = {"free": 0, "paid": 0, **run.get("attacks", {}).get(p["_id"], {}).get(today, {})}
    paid = False
    if mine["free"] < ab["free_attacks_per_day"]:
        field = f"attacks.{p['_id']}.{today}.free"
    elif mine["paid"] < ab["paid_extra_attacks_cap_per_day"]:
        field = f"attacks.{p['_id']}.{today}.paid"
        paid = True
    else:
        raise fail(409, "no_attacks_left", "Hai esaurito gli attacchi di oggi")
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
            await alliance_alert(me["alliance_id"], f"🏆 Il Titano (tier {run['tier']}, {titan_family(run['tier'])}) è stato abbattuto da {p['display_name']}! Ricompense consegnate a {len(upd['participants'])} cacciatori.", kind="titan")
    return {"damage": dmg, "paid": paid, "boss_hp": max(upd["hp"], 0), "boss_hp_max": upd["hp_max"], "progress_pct": round(min(100, pct), 2), "thresholds_hit": sorted(set(upd.get("thresholds_hit", []) + hit)), "killed": killed,
            "personal_reward": ab["personal_attack_reward"], "titan_family": titan_family(run["tier"])}
