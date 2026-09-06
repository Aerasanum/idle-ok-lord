"""E2E smoke of the core loop against a running backend (used during development; pytest suite is in tests/)."""
import json
import sys
import time
import uuid

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001/api"
S = requests.Session()


def call(method, path, expect=200, **kw):
    r = S.request(method, BASE + path, **kw)
    if r.status_code != expect:
        print("FAIL", method, path, r.status_code, r.text[:400])
        sys.exit(1)
    return r.json() if r.text else None


email = f"smoke_{uuid.uuid4().hex[:8]}@example.com"
reg = call("POST", "/auth/register", 201, json={"email": email, "password": "StrongPass!2026", "display_name": "SmokeLord", "age_confirmed": True, "consent": True})
S.headers["Authorization"] = f"Bearer {reg['access_token']}"
code = call("GET", f"/_test/last-code?email={email}")["code"]
call("POST", "/auth/verify-email", json={"code": code})
prof = call("GET", "/profile")
print("profile ok: power", prof["combat"]["total_power"], "res", prof["resources"]["gold"])
pv = call("GET", "/battle/stage/1")
print("stage1", pv["required_power"], "can_win", pv["can_win"])
att = call("POST", "/battle/attempt", json={"stage": 1})["attempt"]
print("attempt", att["id"], "win", att["win"], "duration", att["duration"])
r = S.post(BASE + "/battle/claim", json={"attempt_id": att["id"]})
assert r.status_code == 425, r.text
call("POST", "/_test/time-shift", json={"seconds": 120})
c1 = call("POST", "/battle/claim", json={"attempt_id": att["id"]})
c2 = call("POST", "/battle/claim", json={"attempt_id": att["id"]})
assert c1 == c2, "claim not idempotent"
print("claim idempotent ok; rewards", c1["rewards"], "highest", c1["highest_cleared"])
# progress a few stages
for s in range(2, 12):
    att = call("POST", "/battle/attempt", json={"stage": s})["attempt"]
    call("POST", "/_test/time-shift", json={"seconds": 120})
    c = call("POST", "/battle/claim", json={"attempt_id": att["id"]})
    if not c["win"]:
        print("lost at", s)
        break
prof = call("GET", "/profile")
print("after stages: highest", prof["campaign"]["highest_cleared"], "level", prof["hero"]["level"], "domain", prof["domain"]["owned"], "gold", prof["resources"]["gold"])
inv = call("GET", "/gear/inventory")
print("inventory", inv["count"], "equipped", {k: bool(v) for k, v in inv["equipped"].items()})
# kingdom
k = call("GET", "/kingdom")
print("kingdom castle", k["castle_level"], "tier", k["visual_tier"]["name"])
up = call("POST", "/kingdom/upgrade", json={"building": "farm"})
print("farm upgrade", up.get("queued", up))
call("POST", "/_test/time-shift", json={"seconds": 600})
k = call("GET", "/kingdom")
print("farm level now", next(b for b in k["buildings"] if b["key"] == "farm")["level"])
# offline
off = call("GET", "/offline")
print("offline preview hours", off["hours"], "claimable", off["claimable"])
if off["claimable"]:
    o1 = call("POST", "/offline/claim")
    r = S.post(BASE + "/offline/claim")
    print("offline claim ok; second claim status", r.status_code)
# research + army
call("POST", "/_test/grant", json={"resources": {"gold": 100000, "grain": 100000, "wood": 100000, "clay": 100000, "iron": 100000}, "castle_level": 3, "highest_cleared": 10})
rs = call("POST", "/research/start", json={"node": "military.infantry_drill"})
print("research queued", rs["queued"]["node"])
rc = call("POST", "/army/recruit", json={"unit": "infantry", "quantity": 20})
call("POST", "/_test/time-shift", json={"seconds": 3600})
a = call("GET", "/army")
inf = next(u for u in a["units"] if u["key"] == "infantry")
print("infantry owned", inf["owned"], "slots", a["formation_slots"], "cap", a["command_capacity"])
f = call("PUT", "/army/formation", json={"formation": {"infantry": min(inf["owned"], 20)}})
print("formation", f)
prof = call("GET", "/profile")
print("total power with army", prof["combat"]["total_power"], "army tier", prof["army_visual_tier"]["tier"])
# forge
slot = next((s for s, v in inv["equipped"].items() if v), None)
if slot:
    fr = call("POST", "/forge/upgrade", json={"slot": slot})
    print("forge", fr["slot"], fr["forge_level"])
# quests/achievements
q = call("GET", "/quests")
print("daily points", q["daily"]["points"])
lg = call("POST", "/quests/login/claim")
print("login claim day", lg["day"])
ach = call("GET", "/achievements")
unl = [a for a in ach["achievements"] if a["unlocked"] and not a["claimed"]]
if unl:
    print("achievement claim", call("POST", "/achievements/claim", json={"key": unl[0]["key"]}))
# events
ev = call("GET", "/events")
print("event", ev["event"]["archetype"], "energy", ev["energy"])
dep = call("POST", "/events/deploy", json={"index": 0})
call("POST", "/_test/time-shift", json={"seconds": 3600})
cl = call("POST", "/events/claim", json={"id": dep["id"]})
print("event claim tokens", cl["event_tokens"])
# dungeons
call("POST", "/_test/grant", json={"highest_cleared": 20})
d = call("POST", "/dungeons/start", json={"key": "forge_depths", "tier": 1})
call("POST", "/_test/time-shift", json={"seconds": 700})
print("dungeon claim", call("POST", "/dungeons/claim", json={"id": d["id"]})["granted"])
# store
cat = call("GET", "/store/catalog")
print("catalog products", len(cat["store_products"]), "rc configured", cat["revenuecat_configured"])
r = S.post(BASE + "/purchases/verify", json={})
print("verify without RC ->", r.status_code)
# export
ex = call("GET", "/account/export")
print("export keys", list(ex.keys()))
print("SMOKE OK")
