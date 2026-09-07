"""Seed a demo alliance-war scenario on the preview backend (idempotent, public API + preview test hooks only).

- Fills the QA Lord's alliance up to 10 members (bots `qa.bot1..9@idle1.app`) so it can declare war.
- Creates the rival alliance "Orsi Neri" [ORS] with 10 members, which conquers one neutral node next to its home
  (declare -> roster -> war-shift -> tick), so the map shows a resolved war, captured territory and leaderboard points.

Usage: python scripts/seed_war_demo.py [--base https://.../api]
"""
import argparse
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
QA = {"email": "qa.lord@example.com", "password": "QaLordPass!2026"}
BOT_PASSWORD = "QaBot!2026"


def auth(c: httpx.Client, email: str, password: str, name: str) -> dict:
    for attempt in range(6):
        r = c.post("/auth/register", json={"email": email, "password": password, "display_name": name, "age_confirmed": True, "consent": True})
        if r.status_code == 429:
            time.sleep(10)
            continue
        if r.status_code != 201:
            r = c.post("/auth/login", json={"email": email, "password": password})
            if r.status_code == 429:
                time.sleep(10)
                continue
            r.raise_for_status()
        break
    d = r.json()
    h = {"Authorization": f"Bearer {d['access_token']}"}
    c.post("/_test/grant", json={"email_verified": True}, headers=h).raise_for_status()  # skip the rate-limited code flow
    return {"headers": h, "player_id": d["player_id"], "email": email}


def my_alliance(c: httpx.Client, h: dict) -> dict | None:
    r = c.get("/alliances/mine", headers=h)
    return r.json().get("alliance") if r.status_code == 200 else None


def fill_alliance(c: httpx.Client, alliance_id: str, prefix: str, label: str, n: int) -> list[dict]:
    members = []
    for i in range(1, n + 1):
        b = auth(c, f"{prefix}{i}@idle1.app", BOT_PASSWORD, f"{label} {i}")
        c.post("/_test/grant", json={"castle_level": 8, "highest_cleared": 10 + i, "hero_level": 8 + i}, headers=b["headers"]).raise_for_status()
        mine = my_alliance(c, b["headers"])
        if mine and mine["id"] != alliance_id:
            c.post("/alliances/leave", json={}, headers=b["headers"])
            mine = None
        if not mine:
            j = c.post("/alliances/join", json={"id": alliance_id}, headers=b["headers"])
            if j.status_code != 200:
                print(f"  join failed for {b['email']}: {j.text[:120]}")
        members.append(b)
    return members


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=(os.environ.get("EXPO_PUBLIC_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"))
    args = ap.parse_args()
    c = httpx.Client(base_url=args.base, timeout=60)

    # 1) QA Lord's alliance -> 10 members
    qa = auth(c, QA["email"], QA["password"], "QA Lord")
    qa_alliance = my_alliance(c, qa["headers"])
    if not qa_alliance:
        c.post("/_test/grant", json={"castle_level": 8, "resources": {"gold": 20000}}, headers=qa["headers"]).raise_for_status()
        r = c.post("/alliances", json={"name": "Lupi del Nord", "tag": "LUP", "join_mode": "open", "description": "Alleanza QA", "language": "it"}, headers=qa["headers"])
        r.raise_for_status()
        qa_alliance = r.json()
    print(f"QA alliance [{qa_alliance['tag']}] {qa_alliance['name']} ({qa_alliance['id']})")
    fill_alliance(c, qa_alliance["id"], "qa.bot", "Cavaliere QA", 9)
    a = my_alliance(c, qa["headers"])
    print(f"  members: {a['member_count']}")

    # 2) Rival alliance "Orsi Neri"
    rl = auth(c, "orsi.leader@idle1.app", BOT_PASSWORD, "Ursus Rex")
    c.post("/_test/grant", json={"castle_level": 8, "resources": {"gold": 20000}, "highest_cleared": 28, "hero_level": 18}, headers=rl["headers"]).raise_for_status()
    rival = my_alliance(c, rl["headers"])
    if not rival:
        r = c.post("/alliances", json={"name": "Orsi Neri", "tag": "ORS", "join_mode": "application", "description": "Rivali della QA", "language": "it"}, headers=rl["headers"])
        r.raise_for_status()
        rival = r.json()
    print(f"Rival alliance [{rival['tag']}] {rival['name']} ({rival['id']})")
    c.patch("/alliances/settings", json={"join_mode": "open"}, headers=rl["headers"])
    bots = fill_alliance(c, rival["id"], "orsi.bot", "Orso", 9)
    c.patch("/alliances/settings", json={"join_mode": "application"}, headers=rl["headers"])
    rival = my_alliance(c, rl["headers"])
    print(f"  members: {rival['member_count']}")

    # 3) Rival conquers one neutral node adjacent to its home (only if it has not fought yet)
    wars = c.get("/wars", headers=rl["headers"]).json()["wars"]
    if not wars:
        mp = c.get("/wars/map", headers=rl["headers"]).json()
        home = mp["my_home"]
        hx, hy = home % 19, home // 19
        target = next(n for n in mp["nodes"] if abs(n["x"] - hx) + abs(n["y"] - hy) == 1 and n["owner"] is None)
        war = c.post("/wars/declare", json={"node_id": target["node_id"]}, headers=rl["headers"])
        war.raise_for_status()
        war = war.json()
        roster = [rl["player_id"]] + [b["player_id"] for b in bots]
        c.post("/wars/roster", json={"war_id": war["id"], "player_ids": roster[:10]}, headers=rl["headers"]).raise_for_status()
        c.post("/_test/war-shift", json={"seconds": 8 * 3600 + 60}, headers=rl["headers"]).raise_for_status()
        c.post("/_test/tick", headers=rl["headers"]).raise_for_status()
        detail = c.get(f"/wars/{war['id']}", headers=rl["headers"]).json()
        res = detail["war"]["result"] or {}
        print(f"  rival war on node {target['node_id']} ({target['type']}): {detail['war']['status']} {res.get('attacker_points')}-{res.get('defender_points')} captured={res.get('captured')}")
    else:
        print(f"  rival already has {len(wars)} war(s): {[w['status'] for w in wars]}")

    mp = c.get("/wars/map", headers=qa["headers"]).json()
    print("leaderboard:", [(l["tag"], l["season_points"]) for l in mp["leaderboard"]])
    print("QA home node:", mp["my_home"], "· alliances on map:", len(mp["alliances"]))


if __name__ == "__main__":
    sys.exit(main())
