"""Retention pass (v1.9): login streak (bonus, milestones, monthly recovery) and the wasted-entitlement reminders."""
from datetime import timedelta

import pytest

from app.core import db
from app.core.canon import canon
from app.core.util import day_key, new_id, now
from app.domain.liveops import next_milestone, streak_bonus_pct, streak_milestone, streak_state
from app.domain.scheduler import tick_boss_reminders, tick_reminders, tick_war_roster_reminders
from tests.conftest import register

pytestmark = pytest.mark.asyncio


async def test_streak_rules_are_canonical():
    st = canon()["quests"]["login_streak"]
    assert streak_bonus_pct(1) == 0 and streak_bonus_pct(3) == 2 * st["bonus_pct_per_day"]
    assert streak_bonus_pct(100) == st["bonus_pct_cap"]
    assert streak_milestone(7)["rewards"]["rubies"] == 10 and streak_milestone(8) is None
    assert streak_milestone(60) == streak_milestone(30)  # the last milestone repeats every 30 days
    assert next_milestone(5)["days"] == 7 and next_milestone(5)["days_left"] == 2
    assert next_milestone(31)["days"] == 30 and next_milestone(31)["days_left"] == 29

    yesterday, today = "2026-03-10", "2026-03-11"
    fresh = {"cycle_day": 0, "last_claim_day": None}
    assert streak_state(fresh, today)["streak"] == 1
    assert streak_state({"last_claim_day": yesterday, "streak": 4}, today)["streak"] == 5
    # one missed day is recovered once per calendar month, the second miss breaks the streak
    gap = {"last_claim_day": "2026-03-09", "streak": 4}
    rec = streak_state(gap, today)
    assert rec["streak"] == 5 and rec["recovered"] and rec["recovery_left"] == 0
    used = {**gap, "recovery": {"month": "2026-03", "used": 1}}
    assert streak_state(used, today)["streak"] == 1
    assert streak_state({**gap, "recovery": {"month": "2026-02", "used": 1}}, today)["streak"] == 5  # new month, new recovery
    assert streak_state({"last_claim_day": "2026-03-07", "streak": 9}, today)["streak"] == 1  # three days away


async def _claim_again(client, h, pid: str, login: dict):
    """Replay the daily claim as if a new day started: the ledger key is per day, so it has to go too."""
    key = f"login:{pid}:{day_key()}"
    await db.ledgers.delete_one({"_id": key})
    await db.players.update_one({"_id": pid}, {"$set": {"quests.login": login}, "$pull": {"recent_ledger_keys": key}})
    r = await client.post("/quests/login/claim", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def test_login_streak_pays_bonus_milestone_and_recovery(client):
    u = await register(client)
    h, pid = u["headers"], u["player_id"]
    today = day_key()
    yesterday = day_key(now() - timedelta(days=1))

    first = (await client.post("/quests/login/claim", headers=h)).json()
    assert first["streak"] == 1 and first["bonus_pct"] == 0 and first["rubies"] == first["base_rubies"]

    # a seventh consecutive day: +24% on the calendar Rubies plus the 7-day milestone
    seventh = await _claim_again(client, h, pid, {"cycle_day": 6, "last_claim_day": yesterday, "streak": 6, "best_streak": 6})
    assert seventh["streak"] == 7 and seventh["bonus_pct"] == 24
    assert seventh["rubies"] == round(seventh["base_rubies"] * 1.24)
    assert seventh["milestone"]["days"] == 7 and seventh["granted"]["forge_dust"] == 200
    assert seventh["granted"]["rubies"] == seventh["rubies"] + 10

    # one missed day: the streak survives on the monthly recovery
    back = await _claim_again(client, h, pid, {"cycle_day": 0, "last_claim_day": day_key(now() - timedelta(days=2)), "streak": 7, "best_streak": 7})
    assert back["streak"] == 8 and back["recovered"] is True

    view = (await client.get("/quests", headers=h)).json()["login"]
    assert view["streak"] == 8 and view["best_streak"] == 8 and view["claimed_today"] is True
    assert view["recovery_left"] == 0 and view["next_milestone"]["days"] == 14 and view["next_milestone"]["days_left"] == 6

    # a second miss in the same month starts over
    broken = await _claim_again(client, h, pid, {"cycle_day": 0, "last_claim_day": day_key(now() - timedelta(days=2)), "streak": 8, "best_streak": 8,
                                                 "recovery": {"month": today[:7], "used": 1}})
    assert broken["streak"] == 1 and broken["recovered"] is False and broken["best_streak"] == 8


async def _kinds(pid: str) -> list[str]:
    return [n["kind"] for n in await db.notifications.find({"player_id": pid}).sort("created_at", 1).to_list(20)]


async def test_reminders_fire_only_when_away_and_stay_capped(client):
    u = await register(client)
    h, pid = u["headers"], u["player_id"]
    away = {"last_seen_at": now() - timedelta(hours=2)}

    # playing right now: no nagging, even with a full warehouse
    await db.players.update_one({"_id": pid}, {"$set": {"resources.grain": 10 ** 9, "last_seen_at": now()}})
    await tick_reminders()
    assert await _kinds(pid) == []

    # away with the warehouse overflowing (energy spent, so the energy reminder stays quiet)
    await db.players.update_one({"_id": pid}, {"$set": {**away, "events.energy": 0, "events.energy_at": now()}})
    await tick_reminders()
    await tick_reminders()  # same day: the reminder is not repeated
    assert await _kinds(pid) == ["warehouse_full"]

    # energy back at max is a second, different reminder
    await db.players.update_one({"_id": pid}, {"$set": {**away, "campaign.highest_cleared": 5, "events.energy": canon()["events"]["energy"]["max"], "events.energy_at": now()}})
    await tick_reminders()
    assert await _kinds(pid) == ["warehouse_full", "energy_full"]

    # the daily cap stops the third one
    await db.players.update_one({"_id": pid}, {"$set": {**away, "campaign.highest_cleared": 40, "stats.dungeon_runs": 3}})
    with _evening():
        await tick_reminders()
    assert await _kinds(pid) == ["warehouse_full", "energy_full"]

    n = (await client.get("/notifications", headers=h)).json()
    assert n["unread"] == 2 and n["notifications"][0]["action_url"]


class _evening:
    """The evening reminders only run after 20:00 UTC; tests cannot wait for the clock."""

    def __enter__(self):
        self.r = canon()["notifications"]["reminders"]
        self.hour = self.r["evening_hour_utc"]
        self.r["evening_hour_utc"] = 0

    def __exit__(self, *exc):
        self.r["evening_hour_utc"] = self.hour


async def test_dungeon_entries_and_boss_attacks_are_recalled_in_the_evening(client):
    u = await register(client)
    pid = u["player_id"]
    await db.players.update_one({"_id": pid}, {"$set": {"last_seen_at": now() - timedelta(hours=2), "campaign.highest_cleared": 40, "stats.dungeon_runs": 3,
                                                        "events.energy": 0, "events.energy_at": now()}})
    with _evening():
        await tick_reminders()
    assert await _kinds(pid) == ["dungeon_entries_expiring"]

    ab = canon()["events"]["alliance_boss"]
    aid = new_id("a_")
    await db.alliance_members.insert_one({"_id": new_id("am_"), "alliance_id": aid, "player_id": pid, "role": "member", "joined_at": now()})
    await db.alliance_boss_runs.insert_one({"_id": new_id("boss_"), "alliance_id": aid, "tier": 1, "hp": 40, "hp_max": 100, "status": "active",
                                            "started_at": now(), "ends_at": now() + timedelta(hours=10), "attacks": {}, "participants": []})
    with _evening():
        await tick_boss_reminders()
        await tick_boss_reminders()  # idempotent per day
    kinds = await _kinds(pid)
    assert kinds.count("alliance_boss_attacks_left") == 1
    msg = [n for n in await db.notifications.find({"player_id": pid}).to_list(20) if n["kind"] == "alliance_boss_attacks_left"][0]
    assert "40%" in msg["message"] and str(ab["free_attacks_per_day"]) in msg["message"]


async def test_war_roster_reminder_only_reaches_who_is_not_enlisted(client):
    enlisted = await register(client)
    missing = await register(client)
    aid = new_id("a_")
    for pl in (enlisted, missing):
        await db.alliance_members.insert_one({"_id": new_id("am_"), "alliance_id": aid, "player_id": pl["player_id"], "role": "member", "joined_at": now()})
    war = {"_id": new_id("w_"), "status": "prep", "attacker_id": aid, "defender_id": None, "node_id": 77, "node_type": "wilderness",
           "attack_roster": [enlisted["player_id"]], "attack_reserve": [], "defense_roster": [], "defense_reserve": [],
           "declared_at": now(), "lock_at": now() + timedelta(minutes=30), "resolves_at": now() + timedelta(hours=1)}
    await db.alliance_wars.insert_one(war)

    await tick_war_roster_reminders()
    await tick_war_roster_reminders()  # one reminder per war, not one per pass
    assert await _kinds(missing["player_id"]) == ["war_roster_lock_soon"]
    assert await _kinds(enlisted["player_id"]) == []

    # a full roster needs nobody else
    await db.alliance_wars.update_one({"_id": war["_id"]}, {"$set": {"attack_roster": [f"p_{i}" for i in range(canon()["alliance_war"]["attack_roster_size"])]}})
    await db.notifications.delete_many({"player_id": missing["player_id"]})
    await tick_war_roster_reminders()
    assert await _kinds(missing["player_id"]) == []
