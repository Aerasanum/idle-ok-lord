"""Seed the QA fixture world used by the live (HTTP) test suites. Idempotent.

Creates, using only the public API plus the preview-only test hooks:
  * the attacking alliance [QAT] with the QA lord, nine bots and an eleventh
    member, so enlistment overflows into the reserve queue;
  * the defending alliance [ORS] with ten members;
  * an outsider account that belongs to no alliance;
  * a fully maxed end-game account;
  * territory adjacency between [QAT] and [ORS], so a war can be declared from
    one against the other.

The suites under tests/ declare their own wars on top of this world, so running
this script once is enough for a whole test session.

Usage:
    python scripts/seed_qa.py [--base http://127.0.0.1:8001/api]

Requires TEST_HOOKS_ENABLED=true on the target backend. Setting
RATE_LIMIT_DISABLED=true makes the run much faster, but is not required.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from qa_fixtures import (  # noqa: E402
    LORD_TESTER,
    MAX_ALLIANCE,
    MAX_LORD,
    ORS_ALLIANCE,
    ORS_BOTS,
    ORS_LEADER,
    OUTSIDER,
    QA_ALLIANCE,
    QA_BOT_STAGE,
    QA_BOTS,
    QA_LORD,
    QA_LORD_STAGE,
    SHOWCASE,
)

N = 19  # war map is N x N
WAR_RESOLVE_SECONDS = 8 * 3600 + 3600


def xy(node_id: int) -> tuple[int, int]:
    return node_id % N, node_id // N


def neighbours(node_id: int) -> list[int]:
    x, y = xy(node_id)
    out = []
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < N and 0 <= ny < N:
            out.append(ny * N + nx)
    return out


class Client:
    """Thin API wrapper that retries the register/login endpoints through rate limits."""

    def __init__(self, base: str):
        self.c = httpx.Client(base_url=base, timeout=60)

    def _retrying(self, method: str, url: str, **kw) -> httpx.Response:
        for attempt in range(6):
            r = self.c.request(method, url, **kw)
            if r.status_code != 429:
                return r
            time.sleep(2 * (attempt + 1))
        return r

    def account(self, spec: dict) -> dict:
        """Register or log in, then mark the address verified without the emailed code."""
        r = self._retrying("POST", "/auth/register", json={
            "email": spec["email"], "password": spec["password"], "display_name": spec["display_name"],
            "age_confirmed": True, "consent": True,
        })
        if r.status_code != 201:
            r = self._retrying("POST", "/auth/login", json={"email": spec["email"], "password": spec["password"]})
        if r.status_code >= 400:
            raise RuntimeError(f"could not obtain a session for {spec['email']}: {r.status_code} {r.text[:200]}")
        d = r.json()
        if "access_token" not in d:
            raise RuntimeError(f"unexpected auth payload for {spec['email']}: {str(d)[:200]}")
        acc = {"email": spec["email"], "player_id": d["player_id"], "headers": {"Authorization": f"Bearer {d['access_token']}"}}
        self.grant(acc, email_verified=True)
        return acc

    def grant(self, acc: dict, **body) -> None:
        r = self.c.post("/_test/grant", json=body, headers=acc["headers"])
        if r.status_code >= 400:
            raise RuntimeError(f"grant failed for {acc['email']}: {r.status_code} {r.text[:200]}")

    def get(self, acc: dict, url: str, **kw):
        return self.c.get(url, headers=acc["headers"], **kw)

    def post(self, acc: dict, url: str, **kw):
        return self.c.post(url, headers=acc["headers"], **kw)

    def patch(self, acc: dict, url: str, **kw):
        return self.c.patch(url, headers=acc["headers"], **kw)

    def put(self, acc: dict, url: str, **kw):
        return self.c.put(url, headers=acc["headers"], **kw)

    def my_alliance(self, acc: dict) -> dict | None:
        r = self.get(acc, "/alliances/mine")
        return r.json().get("alliance") if r.status_code == 200 else None


def ensure_alliance(api: Client, leader: dict, spec: dict) -> dict:
    mine = api.my_alliance(leader)
    if mine:
        if mine["tag"] != spec["tag"]:
            raise RuntimeError(f"{leader['email']} already leads [{mine['tag']}], expected [{spec['tag']}]")
        return mine
    # Founding an alliance needs castle 8 and gold; never lower an already higher castle.
    if api.get(leader, "/profile").json()["kingdom"]["castle_level"] < 8:
        api.grant(leader, castle_level=8)
    api.grant(leader, resources={"gold": 20000})
    r = api.post(leader, "/alliances", json={**spec, "join_mode": "open"})
    if r.status_code >= 400:
        raise RuntimeError(f"could not create [{spec['tag']}]: {r.status_code} {r.text[:200]}")
    return r.json()


def join_alliance(api: Client, member: dict, alliance_id: str) -> None:
    mine = api.my_alliance(member)
    if mine and mine["id"] == alliance_id:
        return
    if mine:
        api.post(member, "/alliances/leave", json={})
    r = api.post(member, "/alliances/join", json={"id": alliance_id})
    if r.status_code >= 400:
        raise RuntimeError(f"{member['email']} could not join {alliance_id}: {r.status_code} {r.text[:200]}")


def leave_all_alliances(api: Client, member: dict) -> None:
    if api.my_alliance(member):
        api.post(member, "/alliances/leave", json={})


def place_on_map(api: Client, leader: dict) -> int | None:
    """Alliances are assigned a home castle lazily, on their first look at the war map."""
    r = api.get(leader, "/wars/map")
    if r.status_code >= 400:
        raise RuntimeError(f"war map unavailable for {leader['email']}: {r.status_code} {r.text[:200]}")
    return r.json().get("my_home")


def clear_war_cooldown(api: Client, acc: dict) -> None:
    """Age every war clock, which also lapses the 12h displacement after a lost castle."""
    api.post(acc, "/_test/war-shift", json={"seconds": 200000, "include_resolved": True})
    api.post(acc, "/_test/tick")


def conquer(api: Client, leader: dict, members: list[dict], node_id: int) -> bool:
    """Declare, fill the roster, then fast-forward until the war resolves."""
    r = api.post(leader, "/wars/declare", json={"node_id": node_id})
    if r.status_code >= 400:
        print(f"  declare on {node_id} refused: {r.status_code} {r.text[:160]}")
        return False
    war_id = r.json().get("id") or r.json().get("_id")
    roster = [leader["player_id"]] + [m["player_id"] for m in members]
    api.post(leader, "/wars/roster", json={"war_id": war_id, "player_ids": roster[:10]})
    api.post(leader, "/_test/war-shift", json={"seconds": WAR_RESOLVE_SECONDS})
    api.post(leader, "/_test/tick")
    detail = api.get(leader, f"/wars/{war_id}").json()["war"]
    captured = bool((detail.get("result") or {}).get("captured"))
    print(f"  war on node {node_id}: {detail['status']} captured={captured}")
    return captured


def owned_nodes(api: Client, acc: dict, alliance_id: str) -> set[int]:
    mp = api.get(acc, "/wars/map").json()
    return {n["node_id"] for n in mp["nodes"] if n.get("owner") == alliance_id}


def ensure_adjacency(api: Client, qa: dict, ors: dict, ors_members: list[dict], qa_id: str, ors_id: str) -> bool:
    """Give [ORS] a non-home node bordering [QAT], so [QAT] always has something to declare on.

    The bridge is deliberately held by the defender and is never a home castle: the war
    suites capture their target, and letting them take a home castle would permanently
    reshape the map for every later run.
    """
    mp = api.get(qa, "/wars/map").json()
    node = {n["node_id"]: n for n in mp["nodes"]}
    mine = {n for n, v in node.items() if v.get("owner") == qa_id}
    theirs = {n for n, v in node.items() if v.get("owner") == ors_id}

    def usable(nid: int) -> bool:
        return node[nid]["type"] != "home_castle"

    if any(nb in theirs and usable(nb) for n in mine for nb in neighbours(n)):
        print("  [ORS] already holds a non-home node bordering [QAT]")
        return True

    bridges = sorted(n for n, v in node.items()
                     if usable(n) and v.get("owner") != ors_id
                     and any(nb in mine for nb in neighbours(n))
                     and any(nb in theirs for nb in neighbours(n)))
    if not bridges:
        print("  no node bridges [QAT] and [ORS]; war suites will skip")
        return False
    clear_war_cooldown(api, ors)
    return conquer(api, ors, ors_members, bridges[0])


def decorate_showcase(api: Client, acc: dict) -> None:
    """Give the QA lord a named hero, equipped skins and equipped gear.

    The public showcase endpoint exposes exactly these, so the assertions stay
    meaningful instead of tolerating an undecorated account.
    """
    api.patch(acc, "/account/settings", json={"lord_name": SHOWCASE["lord_name"]})
    api.grant(acc, resources={"rubies": 5000})
    for kind in ("lord", "castle", "army"):
        key = SHOWCASE[f"{kind}_skin"]
        r = api.post(acc, "/store/cosmetics/buy", json={"key": key})
        if r.status_code >= 400 and "already_owned" not in r.text:
            raise RuntimeError(f"could not buy {key}: {r.status_code} {r.text[:160]}")
        api.post(acc, "/store/cosmetics/equip", json={"kind": kind, "key": key})

    # Gear only drops on a first clear, so the campaign is rewound a few stages and
    # then replayed up to QA_LORD_STAGE with the suggested formation deployed.
    suggested = api.get(acc, "/army/suggest").json().get("formation") or {}
    if suggested:
        api.put(acc, "/army/formation", json={"formation": suggested})
    api.grant(acc, highest_cleared=QA_LORD_STAGE - 8)
    while True:
        stage = api.get(acc, "/profile").json()["campaign"]["current_stage"]
        if stage > QA_LORD_STAGE:
            break
        r = api.post(acc, "/battle/attempt", json={"stage": stage})
        if r.status_code >= 400:
            print(f"  battle on stage {stage} refused: {r.status_code} {r.text[:120]}")
            break
        attempt = r.json().get("attempt") or r.json()
        api.post(acc, "/_test/time-shift", json={"seconds": 600})
        api.post(acc, "/battle/claim", json={"attempt_id": attempt["id"]})
    api.post(acc, "/gear/auto-equip")
    inv = api.get(acc, "/gear/inventory").json()
    filled = sum(1 for v in inv["equipped"].values() if v)
    print(f"  showcase: hero '{SHOWCASE['lord_name']}', skins equipped, {filled} gear slots filled")


def seed_max_lord(api: Client, spec: dict) -> None:
    """Max out every progression system so the end-game guard rails can be asserted."""
    import json

    canon = json.loads((BACKEND_ROOT / "canon" / "IDLE_1_v1.1_CANONICAL_SPEC.json").read_text(encoding="utf-8"))
    buildings = {b["key"]: b["max_level"] for b in canon["buildings"]}
    research = {n["key"]: canon["research"]["max_level_each"] for n in canon["research"]["nodes"]}
    forge = {slot: canon["gear"]["forge"]["max_level_per_slot"] for slot in canon["gear"]["slots"]}
    units = {u["key"]: 500 for u in canon["units"]["catalog"]}

    acc = api.account(spec)
    api.grant(acc, highest_cleared=200, hero_level=canon["hero"]["max_level"], castle_level=buildings["castle"],
              buildings=buildings, research=research, forge=forge, units=units,
              resources={k: 2_000_000 for k in ("grain", "wood", "clay", "iron", "gold")})
    api.grant(acc, resources={"rubies": 50_000, "forge_dust": 200_000, "reforge_stone": 500, "war_coins": 20_000})
    # Units only contribute power once deployed, and stage 200 is unbeatable without them.
    suggested = api.get(acc, "/army/suggest").json().get("formation") or {}
    if suggested:
        api.put(acc, "/army/formation", json={"formation": suggested})
    api.post(acc, "/gear/auto-equip")
    ensure_alliance(api, acc, MAX_ALLIANCE)
    place_on_map(api, acc)
    prof = api.get(acc, "/profile").json()
    stage200 = api.get(acc, "/battle/stage/200").json()
    print(f"  {spec['email']}: stage {prof['campaign']['highest_cleared']}, castle {prof['kingdom']['castle_level']}, "
          f"hero {prof['hero']['level']}, domain {prof['domain']['owned']}, "
          f"power {stage200['player_power']} vs {stage200['required_power']} required at stage 200, "
          f"can_win={stage200['can_win']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:8001/api", help="backend API root, including /api")
    args = ap.parse_args()
    api = Client(args.base.rstrip("/"))

    print(f"Seeding QA world on {args.base}")

    print("Attacking alliance")
    qa = api.account(QA_LORD)
    api.grant(qa, castle_level=20, hero_level=60, highest_cleared=QA_LORD_STAGE,
              units={"infantry": 400, "archer": 400, "cavalry": 400, "catapult": 60},
              resources={k: 1_000_000 for k in ("grain", "wood", "clay", "iron", "gold")})
    decorate_showcase(api, qa)
    qa_alliance = ensure_alliance(api, qa, QA_ALLIANCE)
    qa_members = []
    for spec in QA_BOTS + [LORD_TESTER]:
        m = api.account(spec)
        api.grant(m, castle_level=8, highest_cleared=QA_BOT_STAGE, hero_level=20,
                  units={"infantry": 120, "archer": 120, "cavalry": 120})
        join_alliance(api, m, qa_alliance["id"])
        qa_members.append(m)
    qa_alliance = api.my_alliance(qa)
    print(f"  [{qa_alliance['tag']}] {qa_alliance['name']}: {qa_alliance['member_count']} members, "
          f"home {place_on_map(api, qa)}")

    print("Defending alliance")
    ors = api.account(ORS_LEADER)
    api.grant(ors, castle_level=20, hero_level=60, highest_cleared=QA_LORD_STAGE,
              units={"infantry": 400, "archer": 400, "cavalry": 400, "catapult": 60},
              resources={k: 1_000_000 for k in ("grain", "wood", "clay", "iron", "gold")})
    ors_alliance = ensure_alliance(api, ors, ORS_ALLIANCE)
    ors_members = []
    for spec in ORS_BOTS:
        m = api.account(spec)
        api.grant(m, castle_level=8, highest_cleared=QA_BOT_STAGE, hero_level=20,
                  units={"infantry": 120, "archer": 120, "cavalry": 120})
        join_alliance(api, m, ors_alliance["id"])
        ors_members.append(m)
    ors_alliance = api.my_alliance(ors)
    print(f"  [{ors_alliance['tag']}] {ors_alliance['name']}: {ors_alliance['member_count']} members, "
          f"home {place_on_map(api, ors)}")

    print("Outsider")
    outsider = api.account(OUTSIDER)
    leave_all_alliances(api, outsider)
    print(f"  {OUTSIDER['email']}: no alliance")

    print("End-game account")
    seed_max_lord(api, MAX_LORD)

    print("Territory")
    # Previous test runs may have left [ORS] without a home castle and displaced; ageing
    # the clocks lets the scheduler re-seat it before the border is rebuilt.
    clear_war_cooldown(api, qa)
    place_on_map(api, ors)
    ensure_adjacency(api, qa, ors, ors_members, qa_alliance["id"], ors_alliance["id"])
    clear_war_cooldown(api, qa)
    clear_war_cooldown(api, ors)

    mp = api.get(qa, "/wars/map").json()
    print(f"Done. [{qa_alliance['tag']}] home {mp['my_home']} · "
          f"alliances on shard {len(mp['alliances'])} · leaderboard {[(x['tag'], x['season_points']) for x in mp['leaderboard']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
