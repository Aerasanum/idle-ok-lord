"""Alliances, chat and moderation (I12)."""
import re
from datetime import timedelta

from ..core import db
from ..core.canon import canon
from ..core.push import safe_push
from ..core.util import aware, clean, fail, new_id, now
from .progress import Ops, quest_progress

PROFANITY = re.compile(r"\b(fuck|shit|bitch|asshole|cunt|nigg\w*|fag\w*|merda|cazzo|stronz\w*|vaffanculo|puttana|troia|negr[oa])\b", re.I)


def filter_text(t: str) -> str:
    return PROFANITY.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 1), t)


def role_rank(role: str) -> int:
    return {"leader": 3, "officer": 2, "member": 1}.get(role, 0)


async def membership(player_id: str) -> dict | None:
    return await db.alliance_members.find_one({"player_id": player_id})


async def alliance_view(alliance_id: str, viewer_id: str | None = None) -> dict:
    a = await db.alliances.find_one({"_id": alliance_id})
    if not a:
        raise fail(404, "alliance_not_found")
    members = await db.alliance_members.find({"alliance_id": alliance_id}).to_list(40)
    pids = [m["player_id"] for m in members]
    players = {p["_id"]: p for p in await db.players.find({"_id": {"$in": pids}}, {"display_name": 1, "hero.level": 1, "campaign.highest_cleared": 1, "kingdom.castle_level": 1, "last_seen_at": 1, "heraldic_color": 1}).to_list(40)}
    out = clean(a)
    out["members"] = [{"player_id": m["player_id"], "role": m["role"], "joined_at": m["joined_at"].isoformat(), "donated_gold": m.get("donated_gold", 0),
                       "display_name": players.get(m["player_id"], {}).get("display_name", "?"), "hero_level": players.get(m["player_id"], {}).get("hero", {}).get("level", 1),
                       "castle_level": players.get(m["player_id"], {}).get("kingdom", {}).get("castle_level", 1), "highest_cleared": players.get(m["player_id"], {}).get("campaign", {}).get("highest_cleared", 0),
                       "last_seen_at": clean({"t": players.get(m["player_id"], {}).get("last_seen_at")})["t"]} for m in members]
    out["member_count"] = len(members)
    out["member_cap"] = canon()["alliances"]["member_cap"]
    if viewer_id:
        me = next((m for m in members if m["player_id"] == viewer_id), None)
        out["my_role"] = me["role"] if me else None
        if me and role_rank(me["role"]) >= 2:
            out["applications"] = [clean(x) for x in await db.alliance_applications.find({"alliance_id": alliance_id}).to_list(50)]
    return out


async def create_alliance(p: dict, name: str, tag: str, join_mode: str, description: str, language: str) -> dict:
    al = canon()["alliances"]
    if p["kingdom"]["castle_level"] < al["unlock_castle_level"]:
        raise fail(403, "castle_gate", f"Alliances unlock at Castle {al['unlock_castle_level']}")
    if await membership(p["_id"]):
        raise fail(409, "already_member")
    name = name.strip()
    if not (3 <= len(name) <= 20) or not re.match(r"^[\w \-']+$", name):
        raise fail(400, "bad_name")
    tag = tag.strip().upper()
    if not (2 <= len(tag) <= 4) or not tag.isalnum():
        raise fail(400, "bad_tag")
    if join_mode not in al["join_modes"]:
        raise fail(400, "bad_join_mode")
    if await db.alliances.find_one({"name_lower": name.lower()}):
        raise fail(409, "name_taken")
    aid = new_id("al_")
    res = await db.players.update_one({"_id": p["_id"], "resources.gold": {"$gte": al["create_cost_gold"]}, "alliance_id": None},
                                      {"$inc": {"resources.gold": -al["create_cost_gold"], "version": 1}, "$set": {"alliance_id": aid, "updated_at": now()}})
    if res.matched_count == 0:
        raise fail(409, "insufficient_gold", f"Creating an alliance costs {al['create_cost_gold']} Gold")
    doc = {"_id": aid, "name": name, "name_lower": name.lower(), "tag": tag, "join_mode": join_mode, "description": filter_text(description[:200]), "language": language or "it",
           "leader_id": p["_id"], "created_at": now(), "season_points": 0, "war_coins_total": 0, "treasury_gold": 0, "shard_id": None, "home_node": None, "banner": None,
           "lifetime": {"wars_won": 0, "wars_lost": 0, "bosses_killed": 0}, "displaced_until": None}
    await db.alliances.insert_one(doc)
    await db.alliance_members.insert_one({"_id": new_id("am_"), "alliance_id": aid, "player_id": p["_id"], "role": "leader", "joined_at": now(), "donated_gold": 0})
    await system_feed(aid, f"{p['display_name']} founded the alliance {name}.")
    return await alliance_view(aid, p["_id"])


async def list_alliances(query: str | None, language: str | None) -> list[dict]:
    flt: dict = {}
    if query:
        flt["name_lower"] = {"$regex": re.escape(query.lower())}
    if language:
        flt["language"] = language
    rows = await db.alliances.find(flt).sort("season_points", -1).limit(50).to_list(50)
    out = []
    for a in rows:
        c = clean(a)
        c["member_count"] = await db.alliance_members.count_documents({"alliance_id": a["_id"]})
        out.append(c)
    return out


async def join(p: dict, alliance_id: str) -> dict:
    a = await db.alliances.find_one({"_id": alliance_id})
    if not a:
        raise fail(404, "alliance_not_found")
    if p["kingdom"]["castle_level"] < canon()["alliances"]["unlock_castle_level"]:
        raise fail(403, "castle_gate")
    if await membership(p["_id"]):
        raise fail(409, "already_member")
    if a["join_mode"] == "invite_only":
        raise fail(403, "invite_only")
    if a["join_mode"] == "application":
        await db.alliance_applications.update_one({"alliance_id": alliance_id, "player_id": p["_id"]}, {"$set": {"display_name": p["display_name"], "created_at": now()}}, upsert=True)
        return {"applied": True}
    return await _add_member(a, p)


async def _add_member(a: dict, p: dict) -> dict:
    count = await db.alliance_members.count_documents({"alliance_id": a["_id"]})
    if count >= canon()["alliances"]["member_cap"]:
        raise fail(409, "alliance_full")
    res = await db.players.update_one({"_id": p["_id"], "alliance_id": None}, {"$set": {"alliance_id": a["_id"], "updated_at": now()}, "$inc": {"version": 1}})
    if res.matched_count == 0:
        raise fail(409, "already_member")
    await db.alliance_members.insert_one({"_id": new_id("am_"), "alliance_id": a["_id"], "player_id": p["_id"], "role": "member", "joined_at": now(), "donated_gold": 0})
    await db.alliance_applications.delete_many({"player_id": p["_id"]})
    await system_feed(a["_id"], f"{p['display_name']} joined the alliance.")
    return {"joined": True, "alliance_id": a["_id"]}


async def decide_application(p: dict, target_id: str, accept: bool) -> dict:
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "officer_required")
    app = await db.alliance_applications.find_one({"alliance_id": me["alliance_id"], "player_id": target_id})
    if not app:
        raise fail(404, "application_not_found")
    if not accept:
        await db.alliance_applications.delete_one({"_id": app["_id"]})
        return {"rejected": True}
    a = await db.alliances.find_one({"_id": me["alliance_id"]})
    tp = await db.players.find_one({"_id": target_id})
    if not tp or tp.get("alliance_id"):
        await db.alliance_applications.delete_one({"_id": app["_id"]})
        raise fail(409, "target_unavailable")
    return await _add_member(a, tp)


async def leave(p: dict) -> dict:
    me = await membership(p["_id"])
    if not me:
        raise fail(404, "not_member")
    count = await db.alliance_members.count_documents({"alliance_id": me["alliance_id"]})
    if me["role"] == "leader" and count > 1:
        raise fail(409, "transfer_leadership_first")
    await db.alliance_members.delete_one({"_id": me["_id"]})
    await db.players.update_one({"_id": p["_id"]}, {"$set": {"alliance_id": None}, "$inc": {"version": 1}})
    if count <= 1:
        await db.alliances.update_one({"_id": me["alliance_id"]}, {"$set": {"disbanded_at": now()}})
    else:
        await system_feed(me["alliance_id"], f"{p['display_name']} left the alliance.")
    return {"left": True}


async def manage_member(p: dict, target_id: str, action: str) -> dict:
    me = await membership(p["_id"])
    if not me:
        raise fail(404, "not_member")
    tgt = await db.alliance_members.find_one({"alliance_id": me["alliance_id"], "player_id": target_id})
    if not tgt or tgt["player_id"] == p["_id"]:
        raise fail(404, "target_not_found")
    roles = canon()["alliances"]["roles"]
    if action == "kick":
        if role_rank(me["role"]) < 2 or role_rank(tgt["role"]) >= role_rank(me["role"]):
            raise fail(403, "forbidden")
        await db.alliance_members.delete_one({"_id": tgt["_id"]})
        await db.players.update_one({"_id": target_id}, {"$set": {"alliance_id": None}, "$inc": {"version": 1}})
    elif action == "promote":
        if me["role"] != "leader" or tgt["role"] != "member":
            raise fail(403, "forbidden")
        if await db.alliance_members.count_documents({"alliance_id": me["alliance_id"], "role": "officer"}) >= roles["officers_max"]:
            raise fail(409, "officers_max", f"Massimo {roles['officers_max']} ufficiali per alleanza")
        await db.alliance_members.update_one({"_id": tgt["_id"]}, {"$set": {"role": "officer"}})
    elif action == "demote":
        if me["role"] != "leader" or tgt["role"] != "officer":
            raise fail(403, "forbidden")
        await db.alliance_members.update_one({"_id": tgt["_id"]}, {"$set": {"role": "member"}})
    elif action == "transfer":
        if me["role"] != "leader":
            raise fail(403, "forbidden")
        await db.alliance_members.update_one({"_id": tgt["_id"]}, {"$set": {"role": "leader"}})
        await db.alliance_members.update_one({"_id": me["_id"]}, {"$set": {"role": "officer" if await db.alliance_members.count_documents({"alliance_id": me["alliance_id"], "role": "officer"}) < roles["officers_max"] else "member"}})
        await db.alliances.update_one({"_id": me["alliance_id"]}, {"$set": {"leader_id": target_id}})
    else:
        raise fail(400, "bad_action")
    await system_feed(me["alliance_id"], f"Member update: {action} on {target_id[-6:]}.")
    return {"ok": True, "action": action}


async def update_settings(p: dict, join_mode: str | None, description: str | None, name: str | None = None) -> dict:
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "officer_required", "Solo il leader e gli ufficiali possono modificare l'alleanza")
    sets = {}
    if name is not None:  # rename: leader only, unique, cooldown (canon alliances.rename)
        if me["role"] != "leader":
            raise fail(403, "leader_required", "Solo il leader può rinominare l'alleanza")
        name = name.strip()
        if not (3 <= len(name) <= 20) or not re.match(r"^[\w \-']+$", name):
            raise fail(400, "bad_name", "Nome non valido: 3-20 caratteri, lettere, numeri, spazi, - e '")
        a = await db.alliances.find_one({"_id": me["alliance_id"]})
        cd_days = canon()["alliances"].get("rename", {}).get("cooldown_days", 7)
        if a.get("renamed_at") and aware(a["renamed_at"]) > now() - timedelta(days=cd_days):
            raise fail(409, "rename_cooldown", f"Puoi cambiare nome una volta ogni {cd_days} giorni")
        if name.lower() != a["name_lower"] and await db.alliances.find_one({"name_lower": name.lower(), "disbanded_at": None}):
            raise fail(409, "name_taken", "Nome già usato da un'altra alleanza")
        sets.update({"name": name, "name_lower": name.lower(), "renamed_at": now()})
        await system_feed(me["alliance_id"], f"L'alleanza ora si chiama {name}")
    if join_mode:
        if join_mode not in canon()["alliances"]["join_modes"]:
            raise fail(400, "bad_join_mode")
        sets["join_mode"] = join_mode
    if description is not None:
        sets["description"] = filter_text(description[:200])
    if sets:
        await db.alliances.update_one({"_id": me["alliance_id"]}, {"$set": sets})
    return sets


async def donate(p: dict, gold: int) -> dict:
    me = await membership(p["_id"])
    if not me:
        raise fail(404, "not_member")
    if gold < 100:
        raise fail(400, "min_donation", "Minimum donation is 100 Gold")
    ops = Ops()
    ops.inc("resources.gold", -gold).inc("version", 1)
    quest_progress(ops, p, "alliance_action")
    res = await db.players.update_one({"_id": p["_id"], "resources.gold": {"$gte": gold}}, ops.build())
    if res.matched_count == 0:
        raise fail(409, "insufficient_gold")
    await db.alliances.update_one({"_id": me["alliance_id"]}, {"$inc": {"treasury_gold": gold}})
    await db.alliance_members.update_one({"_id": me["_id"]}, {"$inc": {"donated_gold": gold}})
    return {"donated": gold}


async def transfer_inactive_leaders() -> int:
    days = canon()["alliances"]["leader_inactivity_days_before_transfer"]
    cutoff = now() - timedelta(days=days)
    n = 0
    async for a in db.alliances.find({"disbanded_at": {"$exists": False}}):
        leader = await db.players.find_one({"_id": a["leader_id"]}, {"last_seen_at": 1})
        if not leader or (aware(leader.get("last_seen_at")) or cutoff) > cutoff:
            continue
        cands = await db.alliance_members.find({"alliance_id": a["_id"], "player_id": {"$ne": a["leader_id"]}}).to_list(40)
        if not cands:
            continue
        seen = {x["_id"]: aware(x.get("last_seen_at")) for x in await db.players.find({"_id": {"$in": [c["player_id"] for c in cands]}}, {"last_seen_at": 1}).to_list(40)}
        cands.sort(key=lambda c: (-role_rank(c["role"]), -(seen.get(c["player_id"]) or cutoff).timestamp()))
        new_leader = cands[0]
        await db.alliance_members.update_one({"alliance_id": a["_id"], "player_id": a["leader_id"]}, {"$set": {"role": "member"}})
        await db.alliance_members.update_one({"_id": new_leader["_id"]}, {"$set": {"role": "leader"}})
        await db.alliances.update_one({"_id": a["_id"]}, {"$set": {"leader_id": new_leader["player_id"]}})
        await system_feed(a["_id"], "Leadership transferred due to leader inactivity.")
        n += 1
    return n


# ---- chat ---------------------------------------------------------------------------------------------------
async def system_feed(alliance_id: str, text: str) -> None:
    await db.chat_messages.insert_one({"_id": new_id("msg_"), "channel": f"system:{alliance_id}", "player_id": None, "display_name": "System", "text": text, "created_at": now(), "system": True})


async def alliance_alert(alliance_id: str, text: str, kind: str = "war") -> None:
    """Live alert: posted both in the read-only feed and inside the alliance chat channel (system message)."""
    await system_feed(alliance_id, text)
    await db.chat_messages.insert_one({"_id": new_id("msg_"), "channel": f"alliance:{alliance_id}", "player_id": None, "display_name": "Araldo di guerra", "text": text, "created_at": now(), "system": True, "kind": kind})


async def channel_allowed(p: dict, channel: str) -> None:
    kind, _, ident = channel.partition(":")
    if kind == "global":
        return
    me = await membership(p["_id"])
    if kind in ("alliance", "system"):
        if not me or me["alliance_id"] != ident:
            raise fail(403, "not_member")
        return
    if kind == "war":
        w = await db.alliance_wars.find_one({"_id": ident})
        if not w or not me or me["alliance_id"] not in (w["attacker_id"], w.get("defender_id")):
            raise fail(403, "not_in_war")
        if w.get("archived_at") and aware(w["archived_at"]) <= now():
            raise fail(410, "war_chat_archived")
        return
    raise fail(400, "bad_channel")


async def post_message(p: dict, channel: str, text: str) -> dict:
    ch = canon()["chat"]
    text = text.strip()
    if not text or len(text) > ch["max_message_chars"]:
        raise fail(400, "bad_text", f"1-{ch['max_message_chars']} characters")
    await channel_allowed(p, channel)
    if channel.startswith("system:"):
        raise fail(403, "read_only")
    since = now() - timedelta(seconds=ch["rate_limit"]["window_seconds"])
    if await db.chat_messages.count_documents({"player_id": p["_id"], "created_at": {"$gte": since}}) >= ch["rate_limit"]["messages"]:
        raise fail(429, "chat_rate_limit", "Slow down")
    mute = await db.reports_blocks.find_one({"kind": "mute", "target_id": p["_id"], "channel": channel, "until": {"$gt": now()}})
    if mute:
        raise fail(403, "muted", "You are muted in this channel")
    doc = {"_id": new_id("msg_"), "channel": channel, "player_id": p["_id"], "display_name": p["display_name"], "text": filter_text(text), "created_at": now(), "reports": 0}
    await db.chat_messages.insert_one(doc)
    return clean(doc)


async def list_messages(p: dict, channel: str, before: str | None, limit: int = 50) -> list[dict]:
    await channel_allowed(p, channel)
    blocked = {b["target_id"] for b in await db.reports_blocks.find({"player_id": p["_id"], "kind": "block"}).to_list(500)}
    flt: dict = {"channel": channel, "deleted_at": {"$exists": False}, "hidden": {"$ne": True}}
    if before:
        flt["created_at"] = {"$lt": aware(__import__("datetime").datetime.fromisoformat(before))}
    rows = await db.chat_messages.find(flt).sort("created_at", -1).limit(min(limit, 100)).to_list(100)
    return [clean(m) for m in reversed(rows) if m.get("player_id") not in blocked]


async def moderate(p: dict, action: str, target_id: str | None, message_id: str | None, channel: str | None, minutes: int | None, reason: str | None) -> dict:
    if action == "block":
        if not target_id or target_id == p["_id"]:
            raise fail(400, "bad_target")
        await db.reports_blocks.update_one({"player_id": p["_id"], "kind": "block", "target_id": target_id}, {"$set": {"created_at": now()}}, upsert=True)
        return {"blocked": target_id}
    if action == "unblock":
        await db.reports_blocks.delete_one({"player_id": p["_id"], "kind": "block", "target_id": target_id})
        return {"unblocked": target_id}
    if action == "report":
        if not message_id:
            raise fail(400, "message_required")
        m = await db.chat_messages.find_one({"_id": message_id})
        if not m:
            raise fail(404, "message_not_found")
        r = await db.reports_blocks.update_one({"player_id": p["_id"], "kind": "report", "target_id": message_id}, {"$setOnInsert": {"reason": (reason or "")[:200], "reported_player": m.get("player_id"), "created_at": now()}}, upsert=True)
        if r.upserted_id:
            upd = await db.chat_messages.find_one_and_update({"_id": message_id}, {"$inc": {"reports": 1}}, return_document=True)
            if upd and upd.get("reports", 0) >= 3:
                await db.chat_messages.update_one({"_id": message_id}, {"$set": {"hidden": True}})
        return {"reported": message_id}
    me = await membership(p["_id"])
    if not me or role_rank(me["role"]) < 2:
        raise fail(403, "moderator_required")
    if action == "delete":
        m = await db.chat_messages.find_one({"_id": message_id})
        if not m or not m["channel"].endswith(me["alliance_id"]) and not m["channel"].startswith("war:"):
            raise fail(403, "forbidden")
        await db.chat_messages.update_one({"_id": message_id}, {"$set": {"deleted_at": now(), "deleted_by": p["_id"]}})
        return {"deleted": message_id}
    if action == "mute":
        tgt = await db.alliance_members.find_one({"alliance_id": me["alliance_id"], "player_id": target_id})
        if not tgt or role_rank(tgt["role"]) >= role_rank(me["role"]):
            raise fail(403, "forbidden")
        until = now() + timedelta(minutes=max(1, min(minutes or 60, 7 * 24 * 60)))
        await db.reports_blocks.update_one({"player_id": p["_id"], "kind": "mute", "target_id": target_id, "channel": channel or f"alliance:{me['alliance_id']}"}, {"$set": {"until": until, "created_at": now()}}, upsert=True)
        return {"muted": target_id, "until": until.isoformat()}
    raise fail(400, "bad_action")
