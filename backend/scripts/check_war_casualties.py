"""Live check of canon v1.5 casualties: declare -> roster -> lock -> resolve, then verify troops were deducted once."""
import json
import sys

import requests

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("EXPO_PUBLIC_BACKEND_URL")][0] + "/api"


def login(email, pw):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=15).json()
    tok = r.get("access_token") or r["tokens"]["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def main():
    qa = login("qa.lord@example.com", "QaLordPass!2026")
    ors = login("orsi.leader@idle1.app", "QaBot!2026")
    requests.post(f"{BASE}/_test/war-shift", json={"seconds": 100000, "include_resolved": True}, headers=qa, timeout=15)
    requests.post(f"{BASE}/_test/tick", headers=qa, timeout=30)
    m = requests.get(f"{BASE}/wars/map", headers=qa, timeout=15).json()
    own = {n["node_id"] for n in m["nodes"] if n.get("owner") == m["my_alliance_id"]}
    ors_id = next(a for a in m["alliances"] if a != m["my_alliance_id"]) if isinstance(m["alliances"], dict) else None
    # pick an ORS-owned adjacent node first (player vs player casualties), else any adjacent
    cands = []
    for n in m["nodes"]:
        if n["node_id"] in own:
            continue
        x, y = n["x"], n["y"]
        if any(abs(x - o["x"]) + abs(y - o["y"]) == 1 for o in m["nodes"] if o["node_id"] in own):
            cands.append(n)
    cands.sort(key=lambda n: (n.get("owner") != ors_id, n["node_id"]))
    war_id = None
    for n in cands:
        r = requests.post(f"{BASE}/wars/declare", json={"node_id": n["node_id"]}, headers=qa, timeout=15)
        if r.status_code in (200, 201):
            war_id = r.json().get("id") or r.json().get("war", {}).get("id")
            print("declared on", n["node_id"], "owner", n.get("owner"), "type", n["type"])
            break
        print("skip", n["node_id"], r.status_code, r.text[:100])
    assert war_id
    # QA side: make sure the QA Lord deploys a known formation
    army = requests.get(f"{BASE}/army", headers=qa, timeout=15).json()
    units = {u["key"]: u["owned"] for u in army["units"]} if "units" in army else {}
    print("QA owned before:", units)
    prof = requests.get(f"{BASE}/profile", headers=qa, timeout=15).json()
    my_pid = prof.get("player_id") or prof.get("id") or prof.get("_id")
    form_before = prof["army"]["formation"] if "army" in prof else None
    print("QA formation before:", form_before)
    mine = requests.get(f"{BASE}/alliances/mine", headers=qa, timeout=15).json()["alliance"]
    pids = [x["player_id"] for x in mine["members"]][:10]
    print("roster", requests.post(f"{BASE}/wars/roster", json={"war_id": war_id, "player_ids": pids}, headers=qa, timeout=15).status_code)
    d = requests.get(f"{BASE}/wars/{war_id}", headers=ors, timeout=15).json()
    if d["my_side"] == "defense":
        mo = requests.get(f"{BASE}/alliances/mine", headers=ors, timeout=15).json()["alliance"]
        print("ors roster", requests.post(f"{BASE}/wars/roster", json={"war_id": war_id, "player_ids": [x["player_id"] for x in mo["members"]][:10]}, headers=ors, timeout=15).status_code)
    requests.post(f"{BASE}/_test/war-shift", json={"seconds": 8 * 3600}, headers=qa, timeout=15)
    requests.post(f"{BASE}/_test/tick", headers=qa, timeout=60)
    requests.post(f"{BASE}/_test/war-shift", json={"seconds": 1800}, headers=qa, timeout=15)
    requests.post(f"{BASE}/_test/tick", headers=qa, timeout=60)
    d = requests.get(f"{BASE}/wars/{war_id}", headers=qa, timeout=15).json()
    w = d["war"]
    print("status", w["status"], "result", w["result"]["attacker_points"], "-", w["result"]["defender_points"])
    snap_before = json.dumps(d["snapshot"], sort_keys=True, default=str)
    cas = w["result"]["casualties"]
    print("casualties players:", len(cas))
    for pid, c in list(cas.items())[:4]:
        print(" ", pid[:12], c["side"], "lane", c["lane"], "won", c["won"], "r", c["ratio"], "rate", c["rate_pct"], "lost", c["lost_total"], "/", c["deployed_total"])
    print("team_casualties:", d["team_casualties"] and {k: d["team_casualties"][k] for k in ("deployed", "lost")})
    print("my_casualties:", d["my_casualties"] and d["my_casualties"]["units"])
    prof2 = requests.get(f"{BASE}/profile", headers=qa, timeout=15).json()
    army2 = requests.get(f"{BASE}/army", headers=qa, timeout=15).json()
    units2 = {u["key"]: u["owned"] for u in army2["units"]}
    print("QA owned after:", units2)
    print("QA formation after:", prof2["army"]["formation"])
    if d["my_casualties"]:
        for k, v in d["my_casualties"]["units"].items():
            assert units2[k] == units[k] - v["lost"], (k, units[k], units2[k], v)
            assert prof2["army"]["formation"].get(k, 0) <= units2[k]
    # tick again: nothing must change (idempotent)
    requests.post(f"{BASE}/_test/tick", headers=qa, timeout=60)
    army3 = requests.get(f"{BASE}/army", headers=qa, timeout=15).json()
    assert {u["key"]: u["owned"] for u in army3["units"]} == units2, "losses applied twice!"
    d2 = requests.get(f"{BASE}/wars/{war_id}", headers=qa, timeout=15).json()
    assert json.dumps(d2["snapshot"], sort_keys=True, default=str) == snap_before, "snapshot changed!"
    chat = requests.get(f"{BASE}/chat/messages", params={"channel": f"alliance:{m['my_alliance_id']}"}, headers=qa, timeout=15).json()
    msgs = chat.get("messages", chat)
    print("last alert:", [x["text"] for x in msgs if "Perdite" in x.get("text", "")][-1:])
    print("OK")


if __name__ == "__main__":
    main()
