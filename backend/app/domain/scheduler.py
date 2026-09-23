"""Background scheduler: timer completion pushes/inbox, event ending, offline chest full, wasted-entitlement reminders,
war lock/resolve, leader inactivity."""
import asyncio
import logging
from datetime import datetime, timedelta

from ..core import db
from ..core.canon import canon
from ..core.push import safe_push
from ..core.util import aware, day_key, new_id, now
from .liveops import current_event, energy_now
from .player import SOFT, production_per_hour, settle, warehouse_capacity
from .social import transfer_inactive_leaders
from .wars import tick_wars

logger = logging.getLogger("idle1.scheduler")
TICK_SECONDS = 30
BUILDING_NAMES = None
REMINDER_KINDS = ["energy_full", "warehouse_full", "dungeon_entries_expiring", "alliance_boss_attacks_left", "war_roster_lock_soon"]
RES_IT = {"grain": "Grano", "wood": "Legno", "clay": "Argilla", "iron": "Ferro", "gold": "Oro"}


async def notify(player_id: str, kind: str, title: str, message: str, action_url: str | None = None, essential: bool = False, idem: str | None = None) -> bool:
    p = await db.players.find_one({"_id": player_id}, {"settings": 1})
    if not p:
        return False
    if idem and await db.notifications.find_one({"idem": idem}, {"_id": 1}):
        return False
    await db.notifications.insert_one({"_id": new_id("n_"), "player_id": player_id, "kind": kind, "title": title, "message": message, "action_url": action_url, "created_at": now(), "read": False, "idem": idem})
    if essential or (p.get("settings") or {}).get("push_nonessential", True):
        await safe_push([player_id], {"title": title, "message": message, **({"action_url": action_url} if action_url else {})}, idem)
    return True


async def tick_timers() -> int:
    t = now()
    n = 0
    names = {b["key"]: b["name"] for b in canon()["buildings"]}
    rnames = {r["key"]: r["name"] for r in canon()["research"]["nodes"]}
    unames = {u["key"]: u["name"] for u in canon()["units"]["catalog"]}
    async for p in db.players.find({"kingdom.queue_next_end": {"$lte": t}, "deleted_at": {"$exists": False}}):
        done = []
        for qname in ("construction_queue", "recruit_queue", "research_queue"):
            for item in p["kingdom"].get(qname, []):
                if aware(item["ends_at"]) <= t:
                    done.append((qname, item))
        await settle(p)
        for qname, item in done:
            if qname == "construction_queue":
                await notify(p["_id"], "construction_complete", "Costruzione completata", f"{names.get(item['building'], item['building'])} è salito al livello {item['target_level']}.", "/(tabs)/kingdom", idem=f"timer:{item['id']}")
            elif qname == "research_queue":
                await notify(p["_id"], "research_complete", "Ricerca completata", f"{rnames.get(item['node'], item['node'])} livello {item['target_level']} è pronta.", "/kingdom/research", idem=f"timer:{item['id']}")
            else:
                await notify(p["_id"], "recruitment_complete", "Reclutamento completato", f"{item['quantity']} {unames.get(item['unit'], item['unit'])} sono entrate nel tuo esercito.", "/(tabs)/army", idem=f"timer:{item['id']}")
            n += 1
    return n


async def tick_offline_full() -> int:
    mx = canon()["offline"]["max_hours"]
    n = 0
    async for p in db.players.find({"offline.pending_hours": {"$gte": mx}, "offline.full_notified": {"$ne": True}}):
        await notify(p["_id"], "offline_chest_full", "Cassa offline piena", f"La cassa offline da {mx} ore è piena: riscuotila per ricominciare ad accumulare.", "/offline", idem=f"chestfull:{p['_id']}:{p['offline'].get('chest_from')}")
        await db.players.update_one({"_id": p["_id"]}, {"$set": {"offline.full_notified": True}})
        n += 1
    return n


async def tick_event_ending() -> int:
    ev = current_event()
    ends = aware(__import__("datetime").datetime.fromisoformat(ev["ends_at"]))
    if not (timedelta(0) < ends - now() <= timedelta(hours=6)):
        return 0
    n = 0
    async for p in db.players.find({"events.event_key": ev["key"], "events.ending_notified": {"$ne": ev["key"]}, "deleted_at": {"$exists": False}}):
        await notify(p["_id"], "event_ending", "L'evento sta per finire", f"{ev['archetype']} finisce tra meno di 6 ore: riscuoti i premi del tracciato.", "/events", idem=f"evend:{p['_id']}:{ev['key']}")
        await db.players.update_one({"_id": p["_id"]}, {"$set": {"events.ending_notified": ev["key"]}})
        n += 1
    return n


async def _reminders_sent_today(player_id: str) -> int:
    midnight = now().replace(hour=0, minute=0, second=0, microsecond=0)
    return await db.notifications.count_documents({"player_id": player_id, "kind": {"$in": REMINDER_KINDS}, "created_at": {"$gte": midnight}})


async def _player_reminder(p: dict, r: dict, t: datetime) -> bool:
    """At most one reminder per player per pass, strongest first: nobody wants three pushes in a row."""
    pid = p["_id"]
    today = day_key(t)
    evening = t.hour >= r["evening_hour_utc"]
    d = canon()["dungeons"]
    if evening and p["campaign"]["highest_cleared"] >= d["unlock_stage"] and p.get("stats", {}).get("dungeon_runs"):
        dg = p.get("dungeons") or {}
        entries = dg.get("entries", {}) if dg.get("day") == today else {}
        left = sum(max(0, d["free_entries_per_dungeon_per_day"] - entries.get(c["key"], {}).get("free", 0)) for c in d["catalog"])
        if left:
            return await notify(pid, "dungeon_entries_expiring", "Ingressi dungeon in scadenza",
                                f"Hai ancora {left} ingressi gratuiti nei dungeon: si azzerano a mezzanotte UTC.", "/events/dungeons", idem=f"dungeons:{pid}:{today}")
    mx = canon()["events"]["energy"]["max"]
    if p["campaign"]["highest_cleared"] >= 1 and energy_now(p)[0] >= mx:
        return await notify(pid, "energy_full", "Energia al massimo",
                            f"Hai {mx}/{mx} di energia: finché resta piena non ne rigeneri altra. Spendila in una spedizione dell'evento.",
                            "/events/weekly", idem=f"energy:{pid}:{today}")
    cap = warehouse_capacity(p)
    prod = production_per_hour(p)
    full = [k for k in SOFT if p["resources"].get(k, 0) >= cap and prod.get(k, 0) > 0]
    if full:
        names = ", ".join(RES_IT.get(k, k) for k in full)
        return await notify(pid, "warehouse_full", "Magazzino pieno",
                            f"{names}: il magazzino è al limite e la produzione va persa. Spendi o potenzia il Magazzino.", "/(tabs)/kingdom", idem=f"warehouse:{pid}:{today}")
    return False


async def tick_reminders() -> int:
    """Nudges about entitlements the player is wasting. Never while they are playing, never for a dormant account."""
    r = canon()["notifications"]["reminders"]
    t = now()
    flt = {"last_seen_at": {"$lt": t - timedelta(minutes=r["away_minutes"]), "$gt": t - timedelta(days=r["stop_after_inactive_days"])}, "deleted_at": {"$exists": False}}
    n = 0
    async for p in db.players.find(flt):
        if await _reminders_sent_today(p["_id"]) >= r["max_per_player_per_day"]:
            continue
        if await _player_reminder(p, r, t):
            n += 1
    return n


async def tick_boss_reminders() -> int:
    """Free Titan attacks are lost at 00:00 UTC and the whole alliance pays for it."""
    r = canon()["notifications"]["reminders"]
    t = now()
    if t.hour < r["evening_hour_utc"]:
        return 0
    ab = canon()["events"]["alliance_boss"]
    today, n = day_key(t), 0
    async for run in db.alliance_boss_runs.find({"status": "active", "ends_at": {"$gt": t}}):
        left_pct = round(100 * run["hp"] / run["hp_max"])
        for m in await db.alliance_members.find({"alliance_id": run["alliance_id"]}).to_list(40):
            used = (run.get("attacks", {}).get(m["player_id"], {}).get(today, {}) or {}).get("free", 0)
            if used >= ab["free_attacks_per_day"]:
                continue
            if await notify(m["player_id"], "alliance_boss_attacks_left", "Attacchi al Titano non usati",
                            f"Il Titano è ancora al {left_pct}% e ti restano {ab['free_attacks_per_day'] - used} attacchi gratuiti oggi.",
                            "/alliance/boss", idem=f"boss:{run['_id']}:{m['player_id']}:{today}"):
                n += 1
    return n


async def tick_war_roster_reminders() -> int:
    """The roster locks 30 minutes before resolution: a member who forgets to enlist cannot be replaced."""
    aw = canon()["alliance_war"]
    r = canon()["notifications"]["reminders"]
    t = now()
    n = 0
    async for w in db.alliance_wars.find({"status": "prep", "lock_at": {"$gt": t, "$lte": t + timedelta(minutes=r["war_roster_lock_minutes_before"])}}):
        for aid, side, size in ((w["attacker_id"], "attack_roster", aw["attack_roster_size"]), (w.get("defender_id"), "defense_roster", aw["defense_roster_size"])):
            if not aid or len(w.get(side, [])) >= size:
                continue  # a full roster needs nobody else
            booked = set(w.get(side, []) + w.get(side.replace("roster", "reserve"), []))
            minutes = max(1, round((aware(w["lock_at"]) - t).total_seconds() / 60))
            for m in await db.alliance_members.find({"alliance_id": aid}).to_list(40):
                if m["player_id"] in booked:
                    continue
                verb = "attacca" if side == "attack_roster" else "difende"
                if await notify(m["player_id"], "war_roster_lock_soon", "Lo schieramento si blocca",
                                f"La tua alleanza {verb} il nodo {w['node_id']}: {len(w.get(side, []))}/{size} prenotati e lo schieramento si chiude tra {minutes} minuti.",
                                "/alliance/war", idem=f"warlock:{w['_id']}:{m['player_id']}"):
                    n += 1
    return n


async def tick_once() -> dict:
    out = {}
    for name, fn in (("timers", tick_timers), ("offline_full", tick_offline_full), ("event_ending", tick_event_ending), ("wars", tick_wars),
                     ("war_roster", tick_war_roster_reminders), ("boss_reminders", tick_boss_reminders), ("reminders", tick_reminders),
                     ("leaders", transfer_inactive_leaders)):
        try:
            out[name] = await fn()
        except Exception as e:  # scheduler must survive individual failures
            logger.exception("scheduler %s failed: %s", name, e)
            out[name] = f"error: {e}"
    return out


async def run_forever() -> None:
    while True:
        await tick_once()
        await asyncio.sleep(TICK_SECONDS)
