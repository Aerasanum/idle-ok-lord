"""Shared plumbing for the live suites, which drive a running backend over HTTP.

These suites are the counterpart of the in-process ASGI tests in test_core_loop.py
and friends: they exercise the deployed contract, so they need a base URL and the
fixture accounts created by scripts/seed_qa.py.

The target backend is resolved from the environment rather than hardcoded, so the
same suites run against a local server, a preview deployment or CI:

  1. EXPO_PUBLIC_BACKEND_URL
  2. EXPO_BACKEND_URL
  3. EXPO_PUBLIC_BACKEND_URL inside frontend/.env
  4. http://127.0.0.1:8001
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

import pytest
import requests

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
CANON_PATH = BACKEND_ROOT / "canon" / "IDLE_1_v1.1_CANONICAL_SPEC.json"
RULES_PDF = BACKEND_ROOT / "static" / "IDLE1_Regolamento.pdf"

DEFAULT_BACKEND_URL = "http://127.0.0.1:8001"
N = 19  # war map is N x N
TIMEOUT = 30


def _from_frontend_env() -> str | None:
    env_file = REPO_ROOT / "frontend" / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*EXPO_PUBLIC_BACKEND_URL\s*=\s*\"?([^\"\s]+)\"?", line)
        if m:
            return m.group(1)
    return None


def backend_url() -> str:
    for candidate in (os.environ.get("EXPO_PUBLIC_BACKEND_URL"), os.environ.get("EXPO_BACKEND_URL"), _from_frontend_env()):
        if candidate:
            return candidate.rstrip("/")
    return DEFAULT_BACKEND_URL


BASE_URL = backend_url()
API = f"{BASE_URL}/api"


@lru_cache(maxsize=1)
def spec() -> dict:
    return json.loads(CANON_PATH.read_text(encoding="utf-8"))


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def token(spec_or_email, password: str | None = None) -> str:
    """Log in a fixture account, skipping the suite when the QA world has not been seeded."""
    if isinstance(spec_or_email, dict):
        email, password = spec_or_email["email"], spec_or_email["password"]
    else:
        email = spec_or_email
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=TIMEOUT)
    if r.status_code == 401:
        pytest.skip(f"fixture account {email} is missing; run backend/scripts/seed_qa.py against {BASE_URL}")
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


def session(spec_or_email, password: str | None = None) -> dict:
    """Return the headers plus the player id, which most suites need together."""
    tok = token(spec_or_email, password)
    h = hdr(tok)
    prof = requests.get(f"{API}/profile", headers=h, timeout=TIMEOUT)
    assert prof.status_code == 200, prof.text[:200]
    return {"token": tok, "headers": h, "player_id": prof.json()["id"]}


# ---------------------------------------------------------------- war map helpers

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


def war_map(headers: dict) -> dict:
    r = requests.get(f"{API}/wars/map", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:200]
    return r.json()


def clear_war_cooldown(headers: dict, seconds: int = 200000) -> None:
    """Age every war, including resolved ones, so the 24h attack cooldown lapses."""
    requests.post(f"{API}/_test/war-shift", json={"seconds": seconds, "include_resolved": True}, headers=headers, timeout=TIMEOUT)
    requests.post(f"{API}/_test/tick", headers=headers, timeout=TIMEOUT)


def shift_wars(headers: dict, seconds: int) -> None:
    r = requests.post(f"{API}/_test/war-shift", json={"seconds": seconds}, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:200]


def tick(headers: dict) -> None:
    r = requests.post(f"{API}/_test/tick", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:200]


def war_detail(headers: dict, war_id: str) -> dict:
    r = requests.get(f"{API}/wars/{war_id}", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def border_nodes(headers: dict, my_alliance_id: str) -> list[dict]:
    """Nodes we may declare on: adjacent to our territory and not a home castle.

    Home castles are excluded on purpose. Capturing one displaces the loser for twelve
    hours and moves it elsewhere on the map, which would break the border every later
    suite depends on.
    """
    mp = war_map(headers)
    node = {n["node_id"]: n for n in mp["nodes"]}
    mine = {n for n, v in node.items() if v.get("owner") == my_alliance_id}
    return [node[n] for n in sorted({nb for m in mine for nb in neighbours(m)} - mine)
            if node[n]["type"] != "home_castle"]


def enemy_target_node(headers: dict, my_alliance_id: str, enemy_alliance_id: str) -> int | None:
    """An enemy-held node bordering our territory, i.e. one we are allowed to declare on."""
    for n in border_nodes(headers, my_alliance_id):
        if n.get("owner") == enemy_alliance_id:
            return n["node_id"]
    return None


def neutral_target_node(headers: dict, my_alliance_id: str) -> int | None:
    for n in border_nodes(headers, my_alliance_id):
        if n.get("owner") is None:
            return n["node_id"]
    return None


def conquer(attacker: dict, roster: list[str], node_id: int) -> bool:
    """Run a whole war to completion so the attacker ends up owning node_id."""
    war_id = declare_fresh_war(attacker, node_id)
    requests.post(f"{API}/wars/roster", json={"war_id": war_id, "player_ids": roster[:10]},
                  headers=attacker["headers"], timeout=TIMEOUT)
    shift_wars(attacker["headers"], 9 * 3600)
    tick(attacker["headers"])
    return bool((war_detail(attacker["headers"], war_id)["war"].get("result") or {}).get("captured"))


def restore_enemy_border(attacker: dict, defender: dict) -> int | None:
    """Give the defender back a non-home node bordering the attacker, and return it.

    The war suites capture their target, so after one has run the attacker may share no
    border with the defender any more. Rather than depending on suite order, each war
    fixture re-establishes the border it needs.
    """
    mine = alliance_of(attacker["headers"])["id"]
    theirs = alliance_of(defender["headers"])["id"]
    existing = enemy_target_node(attacker["headers"], mine, theirs)
    if existing is not None:
        return existing
    attacker_owned = {n["node_id"] for n in war_map(attacker["headers"])["nodes"] if n.get("owner") == mine}
    bridges = [n["node_id"] for n in border_nodes(defender["headers"], theirs)
               if any(nb in attacker_owned for nb in neighbours(n["node_id"]))]
    if not bridges:
        return None
    roster = [m["player_id"] for m in alliance_of(defender["headers"])["members"]]
    if not conquer(defender, roster, bridges[0]):
        return None
    clear_war_cooldown(attacker["headers"])
    return enemy_target_node(attacker["headers"], mine, theirs)


def declare_fresh_war(attacker: dict, node_id: int) -> str:
    """Clear any cooldown or leftover war, then declare on node_id and return the war id."""
    clear_war_cooldown(attacker["headers"])
    r = requests.post(f"{API}/wars/declare", json={"node_id": node_id}, headers=attacker["headers"], timeout=TIMEOUT)
    if r.status_code >= 400:
        pytest.skip(f"could not declare on node {node_id}: {r.status_code} {r.text[:200]}")
    body = r.json()
    war_id = body.get("id") or body.get("_id")
    assert war_id, body
    return war_id


def enlist(headers: dict, war_id: str) -> requests.Response:
    return requests.post(f"{API}/wars/{war_id}/enlist", headers=headers, timeout=TIMEOUT)


def withdraw(headers: dict, war_id: str) -> requests.Response:
    return requests.post(f"{API}/wars/{war_id}/withdraw", headers=headers, timeout=TIMEOUT)


def alliance_of(headers: dict) -> dict:
    r = requests.get(f"{API}/alliances/mine", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:200]
    alliance = r.json().get("alliance")
    assert alliance, "fixture account is not in an alliance; run backend/scripts/seed_qa.py"
    return alliance
