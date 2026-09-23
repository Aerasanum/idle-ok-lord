"""Canon v1.9 (idempotent): retention pass - login streak (bonus, milestones, one monthly recovery) and the
"you are wasting it" reminders (energy at max, full warehouse, unused free dungeon entries, Titan attacks, war roster lock)."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PATH = os.path.join(ROOT, "canon", "IDLE_1_v1.1_CANONICAL_SPEC.json")
MIRROR = os.path.join(os.path.dirname(ROOT), "docs", "CANONICAL_SPEC.json")

REMINDERS = [
    "energy_full",
    "warehouse_full",
    "dungeon_entries_expiring",
    "alliance_boss_attacks_left",
    "war_roster_lock_soon",
]


def main() -> None:
    c = json.load(open(PATH))

    nt = c["notifications"]
    nt["push"] = list(dict.fromkeys(nt["push"] + REMINDERS))
    nt["reminders"] = {
        "away_minutes": 30,  # never nag someone who is playing right now
        "stop_after_inactive_days": 7,  # a dormant account is a win-back campaign, not a reminder
        "max_per_player_per_day": 2,
        "evening_hour_utc": 20,  # daily entitlements that expire at 00:00 UTC are recalled in the evening
        "war_roster_lock_minutes_before": 60,
        "rule": "reminders are non-essential pushes: they respect the player's opt-out and always land in the in-game inbox too",
    }

    q = c["quests"]
    q["login_streak"] = {
        "bonus_pct_per_day": 4,
        "bonus_pct_cap": 40,
        "milestones": [
            {"days": 3, "rewards": {"rubies": 5}},
            {"days": 7, "rewards": {"rubies": 10, "forge_dust": 200}},
            {"days": 14, "rewards": {"rubies": 20, "reforge_stone": 3}},
            {"days": 30, "rewards": {"rubies": 50, "mythic_essence": 2}},
        ],
        "top_milestone_repeats_every_days": 30,
        "recovery": {"per_calendar_month": 1, "max_missed_days": 1},
        "rule": ("the streak counts consecutive claimed days: it raises the login calendar Rubies by bonus_pct_per_day per day (capped), pays the "
                 "milestone on the exact day it is reached (the last one repeats every 30 days) and survives one missed day per calendar month"),
    }

    ec = c["economy_controls"]
    ec["free_rubies_from_login_streak_28d"] = 80  # bonus + the 3/7/14-day milestones, only with 28 consecutive days
    ec["free_rubies_expected_28d_from_daily_weekly_login"] = 620 + ec["free_rubies_from_login_streak_28d"]

    c["document"]["version"] = "1.9"
    c["document"]["changelog_v1_9"] = [
        "Login streak: +4% Rubies per consecutive day (cap +40%), milestones at 3/7/14/30 days with the last one repeating, one recovered day per month.",
        "Reminders: energy at max, full warehouse, unused free dungeon entries, unused Titan attacks and war roster about to lock, all non-essential and capped per day.",
    ]
    from app.core.canon import compute_spec_hash
    c["document"]["spec_hash"] = compute_spec_hash(c)
    json.dump(c, open(PATH, "w"), ensure_ascii=False, indent=2)
    json.dump(c, open(MIRROR, "w"), ensure_ascii=False, indent=2)
    cp = os.path.join(ROOT, "app", "core", "canon.py")
    s = open(cp).read()
    s = re.sub(r'REQUIRED_VERSION = "[0-9.]+"', 'REQUIRED_VERSION = "1.9"', s)
    s = re.sub(r'REQUIRED_SPEC_HASH = "[0-9a-f]+"', f'REQUIRED_SPEC_HASH = "{c["document"]["spec_hash"]}"', s)
    open(cp, "w").write(s)
    print("hash:", c["document"]["spec_hash"])


if __name__ == "__main__":
    main()
