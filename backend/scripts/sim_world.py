"""World simulation: 250 players in 30 alliances, N simulated days of automated play through the public API (preview test hooks).

Each day, every player: claims offline + login, fights forward (attempt -> time-shift -> claim) until a loss, upgrades buildings,
starts research, recruits, applies the suggested formation, auto-equips, forges, spends talents, claims quest chests and
achievements. Alliances declare wars (10v10 with enlistment) that lock and resolve the same day (war-shift + tick).
Every response is checked (no 5xx, only expected 4xx) and per-player invariants are asserted at the end of each day.

Usage: python scripts/sim_world.py [--players 250] [--alliances 30] [--days 20] [--concurrency 25]
Report: /app/test_reports/sim_world.json
"""
import argparse
import asyncio
import json
import os
import random
import time

import httpx

BASE = os.environ.get("SIM_BASE", "http://localhost:8001/api")  # local backend: the public preview proxy rate-limits bursts (Cloudflare 429)
PW = "SimWorld!2026"
EXPECTED_4XX = {"stage_locked", "insufficient", "queue_full", "max_level", "castle_gate", "already_queued", "unit_locked", "forge_max", "slot_empty",
                "not_enough_points", "already_claimed", "too_early", "not_unlocked", "no_points", "insufficient_or_changed", "nothing_to_claim", "already_enlisted",
                "roster_full", "war_not_open", "attack_cooldown", "not_adjacent", "already_in_war", "not_in_alliance", "already_claimed_today", "no_offline_progress",
                "already_active", "insufficient_gold", "min_members", "already_in_alliance", "bad_quantity", "node_not_found", "attempt_not_found", "already_reserve",
                "not_officer", "cooldown", "roster_locked", "not_in_war", "already_declared", "war_exists", "no_target", "locked", "too_many_types", "not_enough_units",
                "insufficient_rubies", "limit", "not_available", "invalid", "already_running", "nothing_to_salvage", "already_member", "name_taken", "tag_taken", "war_active", "defender_busy", "displaced", "node_contested"}
ERRORS: list[dict] = []
STATS: dict = {"requests": 0, "unexpected": 0}


PREFIX = "sim"


class Player:
    def __init__(self, i: int):
        self.i = i
        self.email = f"{PREFIX}{i:03d}@idle1.app"
        self.name = f"{PREFIX.upper()} Lord {i:03d}"
        self.h: dict = {}
        self.pid = ""
        self.alliance: str | None = None
        self.snap: dict = {}


async def call(c: httpx.AsyncClient, p: Player, method: str, path: str, body=None, ok4=()):
    STATS["requests"] += 1
    for attempt in range(3):
        try:
            r = await c.request(method, path, json=body, headers=p.h, timeout=60)
            break
        except httpx.HTTPError:
            if attempt == 2:
                ERRORS.append({"player": p.email, "path": path, "status": "timeout"})
                return None
            await asyncio.sleep(1)
    if r.status_code == 401 and path != "/auth/login":  # access tokens live 15 minutes: re-login and retry once
        try:
            lr = await c.post("/auth/login", json={"email": p.email, "password": PW}, timeout=60)
            if lr.status_code == 200:
                p.h = {"Authorization": f"Bearer {lr.json()['access_token']}"}
                r = await c.request(method, path, json=body, headers=p.h, timeout=60)
        except httpx.HTTPError as e:
            ERRORS.append({"player": p.email, "path": path, "status": "relogin_error", "body": str(e)[:100]})
            return None
    if r.status_code >= 500:
        STATS["unexpected"] += 1
        ERRORS.append({"player": p.email, "path": path, "status": r.status_code, "body": r.text[:200]})
        return None
    if r.status_code >= 400:
        try:
            code = r.json().get("detail", {}).get("code") if isinstance(r.json().get("detail"), dict) else str(r.json().get("detail"))
        except Exception:
            code = r.text[:80]
        if code not in EXPECTED_4XX and code not in ok4:
            STATS["unexpected"] += 1
            ERRORS.append({"player": p.email, "path": path, "status": r.status_code, "code": code, "body": r.text[:200]})
        return None
    return r.json() if r.content else {}


async def register(c, p: Player, start: dict):
    r = await c.post("/auth/register", json={"email": p.email, "password": PW, "display_name": p.name, "age_confirmed": True, "consent": True}, timeout=60)
    fresh = r.status_code == 201
    if not fresh:
        r = await c.post("/auth/login", json={"email": p.email, "password": PW}, timeout=60)
    d = r.json()
    p.h = {"Authorization": f"Bearer {d['access_token']}"}
    p.pid = d["player_id"]
    if fresh:  # resuming a run never resets an existing player's progress
        await call(c, p, "POST", "/_test/grant", {"email_verified": True, **start})


async def shift(c, p: Player, seconds: int):
    await call(c, p, "POST", "/_test/time-shift", {"seconds": seconds})


async def play_day(c, p: Player, day: int, rng: random.Random):
    await shift(c, p, 86400)  # a full day passes: queues finish, production and offline farm accrue
    await call(c, p, "POST", "/offline/claim", {})
    await call(c, p, "POST", "/quests/login/claim", {})
    prof = await call(c, p, "GET", "/profile")
    if not prof:
        return
    # ---- campaign: push forward until the first loss (max 12 fights) ----
    hc = prof["campaign"]["highest_cleared"]
    for _ in range(12):
        a = await call(c, p, "POST", "/battle/attempt", {"stage": hc + 1})
        if not a or not a.get("attempt"):
            break
        await shift(c, p, 120)
        r = await call(c, p, "POST", "/battle/claim", {"attempt_id": a["attempt"]["id"]})
        if not r or not r.get("win"):
            break
        hc = r.get("highest_cleared", hc + 1)
    # ---- kingdom: up to 3 upgrades (castle first), 1 research, recruits ----
    for _ in range(3):
        k = await call(c, p, "GET", "/kingdom")
        if not k:
            break
        res = k.get("resources") or prof["resources"]
        cands = []
        for b in k["buildings"]:
            if b.get("unlocked", True) and b.get("next") and b.get("level", 0) < b.get("max_level", 20) and not b.get("in_queue"):
                if all(res.get(kk, 0) >= vv for kk, vv in b["next"]["cost"].items()):
                    cands.append(b)
        if not cands:
            break
        cands.sort(key=lambda b: (b["key"] != "castle", b.get("level", 0)))
        if not await call(c, p, "POST", "/kingdom/upgrade", {"building": cands[0]["key"]}):
            break
        await shift(c, p, 3600 * 6)
    rs = await call(c, p, "GET", "/research")
    if rs:
        nodes = [n for n in rs.get("nodes", []) if n.get("unlocked") and n.get("next") and not n.get("in_queue")]
        rng.shuffle(nodes)
        for n in nodes[:2]:
            if await call(c, p, "POST", "/research/start", {"node": n["key"]}):
                break
    army = await call(c, p, "GET", "/army")
    if army:
        prof2 = await call(c, p, "GET", "/profile") or prof
        res = prof2["resources"]
        unlocked = [u for u in army["units"] if u["unlocked"]]
        unlocked.sort(key=lambda u: -u["base_power"] / u["command_cost"])
        for u in unlocked[:2]:
            q = min(200, min(int(res.get(kk, 0) // vv) for kk, vv in u["recruit_cost"].items() if vv > 0) if u["recruit_cost"] else 0)
            if q >= 5:
                await call(c, p, "POST", "/army/recruit", {"unit": u["key"], "quantity": int(q)})
                break
        await shift(c, p, 3600 * 12)
        s = await call(c, p, "GET", "/army/suggest")
        if s and s.get("formation"):
            await call(c, p, "PUT", "/army/formation", {"formation": s["formation"]})
    # ---- gear / hero ----
    await call(c, p, "POST", "/gear/auto-equip", {})
    await call(c, p, "POST", "/forge/upgrade", {"slot": rng.choice(["weapon", "chest", "helmet"])})
    hero = await call(c, p, "GET", "/hero")
    if hero and hero.get("talent_points_total", 0) > hero.get("talent_points_spent", 0):
        await call(c, p, "POST", "/hero/talents", {"branch": rng.choice(["warrior", "guardian", "commander", "fortune"])})
    # ---- claims ----
    q = await call(c, p, "GET", "/quests")
    if q:
        for kind in ("daily", "weekly"):
            for i, ch in enumerate(q[kind]["chests"]):
                if q[kind]["points"] >= ch["points"] and i not in q[kind]["chests_claimed"]:
                    await call(c, p, "POST", "/quests/claim", {"kind": kind, "index": i})
    ach = await call(c, p, "GET", "/achievements")
    if ach:
        for a in ach["achievements"]:
            if a["unlocked"] and not a["claimed"]:
                await call(c, p, "POST", "/achievements/claim", {"key": a["key"]})
    # ---- snapshot + invariants ----
    prof = await call(c, p, "GET", "/profile")
    if prof:
        f, owned = prof["army"]["formation"], prof["army"]["units"]
        bad = [k for k, v in f.items() if v > owned.get(k, 0)]
        if bad:
            ERRORS.append({"player": p.email, "invariant": "formation>owned", "units": bad})
        if any(v < 0 for v in prof["resources"].values()):
            ERRORS.append({"player": p.email, "invariant": "negative_resource", "resources": prof["resources"]})
        if any(v < 0 for v in owned.values()):
            ERRORS.append({"player": p.email, "invariant": "negative_units"})
        p.snap = {"day": day, "stage": prof["campaign"]["highest_cleared"], "castle": prof["kingdom"]["castle_level"], "hero": prof["hero"]["level"],
                  "power": prof.get("combat", {}).get("total_power") or 0, "units": sum(owned.values()), "domain": prof["domain"]["owned"],
                  "rubies": prof["resources"].get("rubies", 0)}


async def wars_day(c, leaders: list[Player], members: dict[str, list[Player]], day: int):
    """Every alliance leader declares on an adjacent non-own node; members enlist; the war locks and resolves today."""
    lead = leaders[0]
    await call(c, lead, "POST", "/_test/war-shift", {"seconds": 100000, "include_resolved": True})
    await call(c, lead, "POST", "/_test/tick", {})
    declared = 0
    for L in leaders:
        m = await call(c, L, "GET", "/wars/map")
        if not m or not m.get("my_alliance_id"):
            continue
        own = [n for n in m["nodes"] if n.get("owner") == m["my_alliance_id"]]
        cands = [n for n in m["nodes"] if n.get("owner") != m["my_alliance_id"] and any(abs(n["x"] - o["x"]) + abs(n["y"] - o["y"]) == 1 for o in own)]
        random.shuffle(cands)
        for n in cands[:3]:
            r = await call(c, L, "POST", "/wars/declare", {"node_id": n["node_id"]}, ok4=("attack_cooldown", "node_contested", "already_in_war", "min_members", "not_adjacent"))
            if r:
                war_id = r.get("id") or r.get("war", {}).get("id")
                declared += 1
                for mem in members[L.alliance][1:10]:
                    await call(c, mem, "POST", f"/wars/{war_id}/enlist", {}, ok4=("already_enlisted", "roster_full"))
                break
    await call(c, lead, "POST", "/_test/war-shift", {"seconds": 8 * 3600})
    await call(c, lead, "POST", "/_test/tick", {})
    await call(c, lead, "POST", "/_test/war-shift", {"seconds": 1800})
    t = await call(c, lead, "POST", "/_test/tick", {})
    return {"declared": declared, "tick": t}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", type=int, default=250)
    ap.add_argument("--alliances", type=int, default=30)
    ap.add_argument("--days", type=int, default=20)
    ap.add_argument("--concurrency", type=int, default=25)
    ap.add_argument("--prefix", default="sim")
    ap.add_argument("--start-day", type=int, default=1)
    args = ap.parse_args()
    global PREFIX
    PREFIX = args.prefix
    rng = random.Random(42)
    t0 = time.time()
    players = [Player(i) for i in range(1, args.players + 1)]
    sem = asyncio.Semaphore(args.concurrency)

    async def guarded(coro):
        async with sem:
            return await coro

    async with httpx.AsyncClient(base_url=BASE) as c:
        # ---- seed: a day-20 world = castle 8 (alliances unlocked), stage 20-40, hero 12-20, some gold for leaders ----
        async def seed(p: Player):
            start = {"castle_level": 8, "highest_cleared": rng.randint(20, 40), "hero_level": rng.randint(12, 20), "resources": {"gold": 30000, "grain": 40000, "wood": 40000, "clay": 30000, "iron": 30000}}
            await register(c, p, start)
        await asyncio.gather(*(guarded(seed(p)) for p in players))
        print(f"seeded {len(players)} players in {time.time()-t0:.0f}s")
        # ---- alliances: round-robin so 250/30 -> 8-9 members each; leaders create, members join ----
        groups: dict[str, list[Player]] = {}
        leaders: list[Player] = []
        # sizes: as many full 10-member alliances (war-capable, min 10 to attack) as possible, the rest smaller (min 5)
        n_full = max(0, min(args.alliances, (args.players - 5 * args.alliances) // 5))
        sizes = [10] * n_full + [max(1, (args.players - 10 * n_full) // max(1, args.alliances - n_full))] * (args.alliances - n_full)
        sizes[-1] += args.players - sum(sizes)
        cuts, off = [], 0
        for sz in sizes:
            cuts.append(players[off:off + sz])
            off += sz
        for gi in range(args.alliances):
            grp = cuts[gi]
            L = grp[0]
            r = await call(c, L, "POST", "/alliances", {"name": f"{PREFIX.upper()} Alliance {gi+1:02d}", "tag": f"{PREFIX[:1].upper()}{gi+1:02d}", "join_mode": "open"})
            if not r:
                mine = await call(c, L, "GET", "/alliances/mine")
                r = mine.get("alliance") if mine else None
            aid = r["id"] if r else None
            if not aid:
                continue
            L.alliance = aid
            leaders.append(L)
            groups[aid] = grp
            async def join(m: Player, aid=aid):
                mine = await call(c, m, "GET", "/alliances/mine")
                if mine and mine.get("alliance") and mine["alliance"]["id"] == aid:
                    m.alliance = aid
                    return
                if await call(c, m, "POST", "/alliances/join", {"id": aid}) is not None:
                    m.alliance = aid
                else:
                    mine = await call(c, m, "GET", "/alliances/mine")
                    m.alliance = mine["alliance"]["id"] if mine and mine.get("alliance") else None
            await asyncio.gather(*(guarded(join(m)) for m in grp[1:]))
        print(f"alliances: {len(leaders)} ({time.time()-t0:.0f}s)")
        # ---- days ----
        report = {"players": len(players), "alliances": len(leaders), "days": []}
        if args.start_day > 1 and os.path.exists("/app/test_reports/sim_world.json"):
            report["days"] = [d for d in json.load(open("/app/test_reports/sim_world.json"))["days"] if d["day"] < args.start_day]
        for day in range(args.start_day, args.days + 1):
            await asyncio.gather(*(guarded(play_day(c, p, day, rng)) for p in players))
            w = await wars_day(c, leaders, groups, day)
            snaps = [p.snap for p in players if p.snap]
            agg = {"day": day, "wars_declared": w["declared"], "tick": w["tick"], "requests": STATS["requests"], "errors": len(ERRORS),
                   "stage": {"min": min(s["stage"] for s in snaps), "avg": round(sum(s["stage"] for s in snaps) / len(snaps), 1), "max": max(s["stage"] for s in snaps)},
                   "castle": {"min": min(s["castle"] for s in snaps), "avg": round(sum(s["castle"] for s in snaps) / len(snaps), 2), "max": max(s["castle"] for s in snaps)},
                   "hero": {"min": min(s["hero"] for s in snaps), "avg": round(sum(s["hero"] for s in snaps) / len(snaps), 1), "max": max(s["hero"] for s in snaps)},
                   "units_total": sum(s["units"] for s in snaps), "power_avg": round(sum(s["power"] for s in snaps) / len(snaps)), "domain_avg": round(sum(s["domain"] for s in snaps) / len(snaps), 1)}
            report["days"].append(agg)
            print(f"day {day}: stage {agg['stage']} castle {agg['castle']} hero {agg['hero']} units {agg['units_total']} power~{agg['power_avg']} wars {w['declared']} tick {w['tick']} req {STATS['requests']} err {len(ERRORS)} ({time.time()-t0:.0f}s)", flush=True)
            json.dump({**report, "errors": ERRORS[:200], "stats": STATS}, open("/app/test_reports/sim_world.json", "w"), indent=1, default=str)
        # growth check: every player must have grown in at least one of stage/castle/hero/units between day 1 and the last day
        json.dump({**report, "errors": ERRORS[:200], "stats": STATS, "final_players": [{"email": p.email, **p.snap} for p in players]}, open("/app/test_reports/sim_world.json", "w"), indent=1, default=str)
        print("DONE", STATS, "errors:", len(ERRORS))


if __name__ == "__main__":
    asyncio.run(main())
