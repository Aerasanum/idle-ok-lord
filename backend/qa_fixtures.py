"""Definitions of the QA fixture world shared by scripts/seed_qa.py and the live test suites.

The HTTP end-to-end suites under tests/ drive a running backend and therefore need
accounts that already exist. Keeping the definitions here means the seed script and
the assertions can never drift apart: seed_qa.py creates exactly what the suites log
into, and both import the same constants.

Nothing here is used by the application itself.
"""
from __future__ import annotations

BOT_PASSWORD = "QaBot!2026"

# Leader of the attacking alliance. Advanced far enough in the campaign that
# unit gates, formation suggestions and boss stages are reachable.
QA_LORD = {"email": "qa.lord@example.com", "password": "QaLordPass!2026", "display_name": "QA Lord"}

# Regular members of the attacking alliance. qa.bot1 is deliberately left without
# officer rank so the "officer_required" branches can be exercised.
QA_BOTS = [{"email": f"qa.bot{i}@idle1.app", "password": BOT_PASSWORD, "display_name": f"Cavaliere QA {i}"} for i in range(1, 10)]

# Eleventh member of the attacking alliance: with ten slots taken this account is
# what pushes an enlistment into the reserve queue.
LORD_TESTER = {"email": "lord.tester@idle1.app", "password": "Idle1Lord!2026", "display_name": "Lord Tester"}

# Deliberately kept out of every alliance to exercise "not_in_alliance".
OUTSIDER = {"email": "qa.outsider@idle1.app", "password": BOT_PASSWORD, "display_name": "Straniero QA"}

# Defending alliance.
ORS_LEADER = {"email": "orsi.leader@idle1.app", "password": BOT_PASSWORD, "display_name": "Ursus Rex"}
ORS_BOTS = [{"email": f"orsi.bot{i}@idle1.app", "password": BOT_PASSWORD, "display_name": f"Orso {i}"} for i in range(1, 10)]

# End-game account with every progression system maxed out.
MAX_LORD = {"email": "max.lord@idle1.app", "password": "MaxLord!2026", "display_name": "Max Lord"}

QA_ALLIANCE = {"name": "Lupi del Nord", "tag": "QAT", "description": "Alleanza QA", "language": "it"}
ORS_ALLIANCE = {"name": "Orsi Neri", "tag": "ORS", "description": "Rivali della QA", "language": "it"}

# The end-game suite posts this alliance and tolerates "already_member". Seeding it
# up front keeps it from being created and disbanded on every run, which would hand
# out a different home castle each time and break the [QAT]/[ORS] border.
MAX_ALLIANCE = {"name": "Maximus Guard", "tag": "MAX", "description": "End-game QA", "language": "it"}

# Campaign progress given to the QA lord and the bots. High enough that stage 50 is
# unlocked (boss timing test) and that army suggestions return a non-empty formation.
QA_LORD_STAGE = 60
QA_BOT_STAGE = 30

# Decoration applied to the QA lord so the public showcase has something to expose.
# lord_golden_emperor is deliberately left unowned, to exercise "not_owned" on equip.
SHOWCASE = {
    "lord_name": "Sir Aldric",
    "lord_skin": "lord_frost_warden",
    "castle_skin": "castle_dragon_keep",
    "army_skin": "army_crimson_legion",
}
