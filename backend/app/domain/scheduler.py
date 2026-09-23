"""Background scheduler: timer completion pushes/inbox, event ending, offline chest full, war lock/resolve, leader inactivity."""
import asyncio
import logging
from datetime import timedelta

from ..core import db
from ..core.canon import canon
from ..core.push import safe_push
from ..core.util import aware, new_id, now
from .liveops import current_event
from .player import settle
from .social import transfer_inactive_leaders
from .wars import tick_wars

logger = logging.getLogger("idle1.scheduler")
TICK_SECONDS = 30
BUILDING_NAMES = None


async def notify(player_id: str, kind: str, title: str, message: str, action_url: str | None = None, essential: bool = False, idem: str | None = None) -> None:
    p = await db.players.find_one({"_id": player_id}, {"settings": 1})
    if not p:
        return
    if idem and await db.notifications.find_one({"idem": idem}, {"_id": 1}):
        return
    await db.notifications.insert_one({"_id": new_id("n_"), "player_id": player_id, "kind": kind, "title": title, "message": message, "action_url": action_url, "created_at": now(), "read": False, "idem": idem})
    if essential or (p.get("settings") or {}).get("push_nonessential", True):
        await safe_push([player_id], {"title": title, "message": message, **({"action_url": action_url} if action_url else {})}, idem)


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


async def tick_once() -> dict:
    out = {}
    for name, fn in (("timers", tick_timers), ("offline_full", tick_offline_full), ("event_ending", tick_event_ending), ("wars", tick_wars), ("leaders", transfer_inactive_leaders)):
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
