"""Cosmetic skins (Lord and Castle). Pure appearance: no stats, no power. Bought with Rubies, owned forever, one equipped per kind.

The catalog lives here (not in the canonical spec, which only lists cosmetic *categories*): prices are deliberately in the
"accelerator" range of the monetization pillar so a skin never competes with progression spend.
"""
from ..core import db
from ..core.util import fail, new_id, now

CATALOG: list[dict] = [
    # ---- Lord skins (art: frontend/assets/art/skins/lord_<key>.webp)
    {"key": "lord_forest_ranger", "kind": "lord", "name": "Ranger della Foresta", "desc": "Cuoio elfico con motivi di foglie, mantello con cappuccio e arco ornato.", "rubies": 300, "rarity": "rare"},
    {"key": "lord_crimson_paladin", "kind": "lord", "name": "Paladino Cremisi", "desc": "Piastra cremisi e argento, tabarro con croce bianca, elmo alato e spada sacra.", "rubies": 350, "rarity": "rare"},
    {"key": "lord_frost_warden", "kind": "lord", "name": "Guardiano del Gelo", "desc": "Armatura incantata blu ghiaccio, spallacci di cristallo e spadone congelato.", "rubies": 450, "rarity": "epic"},
    {"key": "lord_shadow_reaper", "kind": "lord", "name": "Mietitore d'Ombra", "desc": "Cavaliere-assassino incappucciato, energia del vuoto e lame ricurve gemelle.", "rubies": 600, "rarity": "epic"},
    {"key": "lord_dragon_knight", "kind": "lord", "name": "Cavaliere del Drago", "desc": "Scaglie di drago nere e rosse, elmo a teschio di drago e spada fiammeggiante.", "rubies": 750, "rarity": "legendary"},
    {"key": "lord_golden_emperor", "kind": "lord", "name": "Imperatore Dorato", "desc": "Armatura imperiale radiosa, corona alta, mantello bianco e oro, spada-scettro ingioiellata.", "rubies": 900, "rarity": "legendary"},
    # ---- Castle skins (art: frontend/assets/art/skins/castle_<key>.webp)
    {"key": "castle_winter_citadel", "kind": "castle", "name": "Cittadella d'Inverno", "desc": "Pietra bianca innevata, tetti blu ghiaccio, stendardi gelati e lanterne.", "rubies": 500, "rarity": "epic"},
    {"key": "castle_elven_palace", "kind": "castle", "name": "Palazzo Elfico", "desc": "Marmo bianco e alberi viventi, cupole a foglia d'oro, giardini pensili e rune.", "rubies": 700, "rarity": "epic"},
    {"key": "castle_obsidian_fortress", "kind": "castle", "name": "Fortezza d'Ossidiana", "desc": "Ossidiana nera, cristalli arcani viola, pietre fluttuanti e fiamme violette.", "rubies": 800, "rarity": "legendary"},
    {"key": "castle_dragon_keep", "kind": "castle", "name": "Fortezza del Drago", "desc": "Roccia vulcanica con crepe di lava, statue di drago, torri a punta e un drago in cima.", "rubies": 900, "rarity": "legendary"},
]
BY_KEY = {c["key"]: c for c in CATALOG}
DEFAULT = {"owned": [], "lord_skin": None, "castle_skin": None}


def state(p: dict) -> dict:
    c = p.get("cosmetics") or {}
    return {"owned": list(c.get("owned") or []), "lord_skin": c.get("lord_skin"), "castle_skin": c.get("castle_skin")}


def view(p: dict) -> dict:
    s = state(p)
    return {"catalog": [{**c, "owned": c["key"] in s["owned"], "equipped": s[f"{c['kind']}_skin"] == c["key"]} for c in CATALOG], **s, "rubies": p["resources"].get("rubies", 0)}


async def buy(p: dict, key: str) -> dict:
    c = BY_KEY.get(key)
    if not c:
        raise fail(404, "skin_not_found")
    s = state(p)
    if key in s["owned"]:
        raise fail(409, "already_owned", "Skin già posseduta")
    # atomic: enough rubies and not yet owned; auto-equip on purchase
    res = await db.players.update_one(
        {"_id": p["_id"], "resources.rubies": {"$gte": c["rubies"]}, "cosmetics.owned": {"$ne": key}},
        {"$inc": {"resources.rubies": -c["rubies"], "version": 1}, "$addToSet": {"cosmetics.owned": key}, "$set": {f"cosmetics.{c['kind']}_skin": key}},
    )
    if res.matched_count == 0:
        raise fail(409, "insufficient_rubies", f"La skin costa {c['rubies']} Rubini")
    await db.purchases.insert_one({"_id": new_id("rb_"), "transaction_key": f"skin:{p['_id']}:{key}", "player_id": p["_id"], "kind": "ruby_spend", "item": key, "rubies": c["rubies"], "created_at": now()})
    return {"bought": key, "equipped": True, "rubies_spent": c["rubies"]}


async def equip(p: dict, kind: str, key: str | None) -> dict:
    if kind not in ("lord", "castle"):
        raise fail(400, "bad_kind")
    if key is not None:
        c = BY_KEY.get(key)
        if not c or c["kind"] != kind:
            raise fail(404, "skin_not_found")
        if key not in state(p)["owned"]:
            raise fail(403, "not_owned", "Skin non posseduta")
    await db.players.update_one({"_id": p["_id"]}, {"$set": {f"cosmetics.{kind}_skin": key}, "$inc": {"version": 1}})
    return {"kind": kind, "equipped": key}
