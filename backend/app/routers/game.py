from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core import db
from ..core.canon import canon, kingdom_visual_tier, army_visual_tier, validation_report
from ..core.security import Principal, current_user
from ..core.util import clean, fail, now
from ..domain import campaign as C
from ..domain import domain_map as D
from ..domain import formulas as F
from ..domain import gear as G
from ..domain import hero as H
from ..domain import kingdom as K
from ..domain import offline as O
from ..domain import player as P

router = APIRouter(tags=["game"])


async def load(p: Principal) -> dict:
    pl = await P.load(p.player_id)
    if pl.get("deleted_at"):
        raise fail(401, "account_unavailable")
    return pl


@router.get("/canon/validation")
async def canon_validation():
    return validation_report()


@router.get("/canon/static")
async def canon_static():
    """Read-only canonical catalogs for client rendering (names, tiers, regions). Numbers stay server-authoritative."""
    c = canon()
    return {
        "regions": c["battle"]["regions"], "units": [{k: u[k] for k in ("key", "name", "category", "role", "command_cost", "base_power")} for u in c["units"]["catalog"]],
        "gear": {"slots": c["gear"]["slots"], "rarity_order": c["gear"]["rarity_order"], "rarity_rules": c["gear"]["rarity_rules"], "rarity_unlock_stage": c["gear"]["rarity_unlock_stage"], "affix_pool": c["gear"]["affix_pool"]},
        "kingdom_visual_tiers": c["kingdom"]["visual_tiers"], "army_visual_tiers": c["army_visual_progression"]["tiers"], "skills": c["hero"]["auto_skills"], "talents": c["hero"]["talents"],
        "skill_slot_unlock_levels": c["hero"]["skill_slot_unlock_levels"], "buildings": [{k: b[k] for k in ("key", "name", "unlock_castle_level", "max_level")} for b in c["buildings"]],
        "performance": c["performance"], "ux": c["ux"], "domain_tile_visuals": c["personal_domain"]["tile_visuals"],
    }


@router.get("/profile")
async def profile(p: Principal = Depends(current_user)):
    pl = await load(p)
    st = await P.public_state(pl)
    st["kingdom_visual_tier"] = kingdom_visual_tier(pl["kingdom"]["castle_level"])
    st["army_visual_tier"] = army_visual_tier(max(pl["campaign"]["highest_cleared"], pl["campaign"]["current_stage"]), st["combat"]["army_deployed"])
    st["offline_preview"] = O.preview(pl)
    st["unread_notifications"] = await db.notifications.count_documents({"player_id": pl["_id"], "read": False})
    st["account"] = {"email_verified": p.account.get("email_verified", False), "email": p.account["email"]}
    return st


# ---- battle ---------------------------------------------------------------------------------------------
class AttemptIn(BaseModel):
    stage: int = Field(ge=1, le=100000)
    client_key: str | None = None


class ClaimIn(BaseModel):
    attempt_id: str


@router.get("/battle/stage/{stage}")
async def stage_preview(stage: int, p: Principal = Depends(current_user)):
    pl = await load(p)
    mix = F.stage_enemy_mix(stage)
    prof = await P.combat_profile(pl, enemy_mix=mix)
    base_army = P.army_power(pl, prof["hero"]["affixes"].get("army_power_pct", 0))[0]
    pv = C.stage_preview(stage)
    pv["player_power"] = prof["total_power"]
    pv["army_power"] = prof["army_power"]
    pv["army_counter_pct"] = prof["army_counter_pct"]
    pv["army_counter_net_pct"] = round((prof["army_power"] / base_army - 1) * 100, 1) if base_army else 0.0
    pv["enemy_mix"] = mix
    pv["can_win"] = prof["total_power"] >= pv["required_power"]
    pv["locked"] = stage > pl["campaign"]["highest_cleared"] + 1
    pv["army_visual_tier"] = army_visual_tier(stage, prof["army_deployed"])
    return pv


@router.post("/battle/attempt")
async def battle_attempt(body: AttemptIn, p: Principal = Depends(current_user)):
    pl = await load(p)
    return await C.start_attempt(pl, body.stage, body.client_key)


@router.post("/battle/claim")
async def battle_claim(body: ClaimIn, p: Principal = Depends(current_user)):
    pl = await load(p)
    return await C.claim_attempt(pl, body.attempt_id)


@router.get("/battle/attempts")
async def attempts(p: Principal = Depends(current_user)):
    rows = await db.battle_attempts.find({"player_id": p.player_id}, {"timeline": 0}).sort("created_at", -1).limit(20).to_list(20)
    return {"attempts": [clean(a) for a in rows], "server_time": now().isoformat()}


# ---- gear ------------------------------------------------------------------------------------------------
class EquipIn(BaseModel):
    item_id: str


class SlotIn(BaseModel):
    slot: str


class SalvageIn(BaseModel):
    item_ids: list[str]


class ReforgeIn(BaseModel):
    item_id: str
    affix_index: int


class AutoSalvageIn(BaseModel):
    enabled: bool
    max_rarity: str = "common"
    below_equipped: bool = False
    slots: list[str] = []


@router.get("/gear/inventory")
async def inventory(p: Principal = Depends(current_user)):
    pl = await load(p)
    items = await G.list_inventory(pl)
    return {"items": [clean(i) for i in items], "capacity": pl.get("inventory_capacity"), "count": len([i for i in items if not i["equipped_slot"]]), "equipped": pl["equipped"], "forge": pl["forge"],
            "auto_salvage": pl.get("auto_salvage"), "auto_salvage_unlocked": pl["campaign"]["highest_cleared"] >= canon()["gear"]["inventory"]["auto_salvage_unlock_stage"],
            "forge_costs": {s: (None if not pl["equipped"].get(s) else None) for s in pl["forge"]}, "expansions": canon()["gear"]["inventory"]["expansions"]}


@router.post("/gear/equip")
async def equip(body: EquipIn, p: Principal = Depends(current_user)):
    return await G.equip(await load(p), body.item_id)


@router.post("/gear/unequip")
async def unequip(body: SlotIn, p: Principal = Depends(current_user)):
    return await G.unequip(await load(p), body.slot)


@router.post("/gear/auto-equip")
async def auto_equip(p: Principal = Depends(current_user)):
    return await G.auto_equip(await load(p))


@router.post("/gear/salvage")
async def salvage(body: SalvageIn, p: Principal = Depends(current_user)):
    return await G.salvage(await load(p), body.item_ids)


@router.post("/forge/upgrade")
async def forge(body: SlotIn, p: Principal = Depends(current_user)):
    return await G.forge_upgrade(await load(p), body.slot)


@router.get("/forge/costs")
async def forge_costs(p: Principal = Depends(current_user)):
    pl = await load(p)
    from ..domain import formulas as F
    out = {}
    items = {i["_id"]: i for i in await P.equipped_items(pl)}
    for slot, lvl in pl["forge"].items():
        it = items.get(pl["equipped"].get(slot))
        out[slot] = {"level": lvl, "multiplier": F.forge_multiplier(lvl), "next_cost": F.forge_next_cost(it["item_level"], lvl) if it and lvl < 20 else None, "item_level": it["item_level"] if it else None}
    return out


@router.post("/gear/reforge")
async def reforge(body: ReforgeIn, p: Principal = Depends(current_user)):
    return await G.reforge(await load(p), body.item_id, body.affix_index)


@router.post("/gear/expand")
async def expand(p: Principal = Depends(current_user)):
    return await G.expand_inventory(await load(p))


@router.put("/gear/auto-salvage")
async def auto_salvage(body: AutoSalvageIn, p: Principal = Depends(current_user)):
    return await G.set_auto_salvage(await load(p), body.model_dump())


# ---- hero -----------------------------------------------------------------------------------------------
class TalentIn(BaseModel):
    branch: str


class SkillsIn(BaseModel):
    slots: list[str | None]


@router.get("/hero")
async def hero(p: Principal = Depends(current_user)):
    pl = await load(p)
    prof = await P.combat_profile(pl)
    return {"hero": pl["hero"], "stats": prof["hero"], "xp_to_next": __import__("app.domain.formulas", fromlist=["x"]).xp_to_next(pl["hero"]["level"]), "skills": H.unlocked_skills(pl["hero"]["level"]),
            "all_skills": canon()["hero"]["auto_skills"], "skill_slots_unlocked": H.unlocked_slot_count(pl["hero"]["level"]), "talents": canon()["hero"]["talents"],
            "talent_points_total": __import__("app.domain.formulas", fromlist=["x"]).talent_points_for_level(pl["hero"]["level"]), "talent_points_spent": sum(pl["hero"]["talents"].values())}


@router.post("/hero/talents")
async def talents(body: TalentIn, p: Principal = Depends(current_user)):
    return await H.allocate_talent(await load(p), body.branch)


@router.post("/hero/talents/respec")
async def respec(p: Principal = Depends(current_user)):
    return await H.respec(await load(p))


@router.put("/hero/skills")
async def skills(body: SkillsIn, p: Principal = Depends(current_user)):
    return await H.set_skill_slots(await load(p), body.slots)


# ---- kingdom / research / army --------------------------------------------------------------------------
class BuildingIn(BaseModel):
    building: str


class SpeedupIn(BaseModel):
    queue: str
    item_id: str


class ResearchIn(BaseModel):
    node: str


class RecruitIn(BaseModel):
    unit: str
    quantity: int = Field(ge=1, le=5000)


class FormationIn(BaseModel):
    formation: dict[str, int]


@router.get("/kingdom")
async def kingdom(p: Principal = Depends(current_user)):
    pl = await load(p)
    q = canon()["kingdom"]
    return {"castle_level": pl["kingdom"]["castle_level"], "visual_tier": kingdom_visual_tier(pl["kingdom"]["castle_level"]), "buildings": K.building_view(pl), "queues": {k: [clean(i) for i in pl["kingdom"].get(k, [])] for k in ("construction_queue", "recruit_queue", "research_queue")},
            "queue_caps": {"construction": q["construction_queues"]["max"] if pl["kingdom"]["castle_level"] >= q["construction_queues"]["second_unlock_castle_level"] else q["construction_queues"]["start"],
                           "recruit": q["recruit_queues"]["max"] if pl["kingdom"]["castle_level"] >= q["recruit_queues"]["second_unlock_castle_level"] else q["recruit_queues"]["start"], "research": q["research_queues"]},
            "resources": pl["resources"], "production_per_hour": {k: round(v) for k, v in P.production_per_hour(pl).items()}, "warehouse_capacity": P.warehouse_capacity(pl), "server_time": now().isoformat(),
            "visual_tiers": q["visual_tiers"]}


@router.post("/kingdom/upgrade")
async def upgrade(body: BuildingIn, p: Principal = Depends(current_user)):
    return await K.upgrade_building(await load(p), body.building)


@router.post("/kingdom/speedup")
async def speedup(body: SpeedupIn, p: Principal = Depends(current_user)):
    return await K.speedup(await load(p), body.queue, body.item_id)


@router.get("/research")
async def research(p: Principal = Depends(current_user)):
    pl = await load(p)
    return {"nodes": K.research_view(pl), "branches": canon()["research"]["branches"], "queue": [clean(i) for i in pl["kingdom"].get("research_queue", [])], "server_time": now().isoformat()}


@router.post("/research/start")
async def research_start(body: ResearchIn, p: Principal = Depends(current_user)):
    return await K.start_research(await load(p), body.node)


@router.get("/army")
async def army(p: Principal = Depends(current_user)):
    pl = await load(p)
    prof = await P.combat_profile(pl)
    stage = max(pl["campaign"]["highest_cleared"] + 1, pl["campaign"]["current_stage"])
    mix = F.stage_enemy_mix(stage)
    cc = canon()["units"]["counters"]
    region_counter = {u["key"]: round(F.unit_counter_pct(u["key"], mix), 1) for u in canon()["units"]["catalog"]}
    return {"units": K.army_view(pl), "formation": pl["army"]["formation"], "command_capacity": prof["command_capacity"], "command_used": prof["command_used"], "formation_slots": prof["formation_slots"],
            "army_power": prof["army_power"], "army_per_unit": prof["army_per_unit"], "queue": [clean(i) for i in pl["kingdom"].get("recruit_queue", [])], "campaign_army_unlock_stage": canon()["units"]["campaign_army_unlock_stage"],
            "visual_tier": army_visual_tier(max(pl["campaign"]["highest_cleared"], pl["campaign"]["current_stage"]), prof["army_deployed"]), "server_time": now().isoformat(),
            "counters": {"bonus_pct": cc["bonus_pct"], "malus_pct": cc["malus_pct"], "class_labels": cc["class_labels"], "unit_class": cc["unit_class"], "table": cc["table"]},
            "region_counter": {"stage": stage, "region": F.region_for_stage(min(stage, 200))["name"], "enemy_mix": mix, "unit_pct": region_counter}}


@router.post("/army/recruit")
async def recruit(body: RecruitIn, p: Principal = Depends(current_user)):
    return await K.recruit(await load(p), body.unit, body.quantity)


@router.put("/army/formation")
async def formation(body: FormationIn, p: Principal = Depends(current_user)):
    return await K.set_formation(await load(p), body.formation)


@router.get("/army/suggest")
async def suggest(stage: int | None = None, p: Principal = Depends(current_user)):
    """Suggested formation vs the enemy class mix of `stage` (default: next stage). Nothing is applied — use PUT /army/formation."""
    pl = await load(p)
    st = stage or max(pl["campaign"]["highest_cleared"] + 1, pl["campaign"]["current_stage"])
    mix = F.stage_enemy_mix(st)
    prof = await P.combat_profile(pl, enemy_mix=mix)
    sug = K.suggest_formation(pl, prof["hero"]["affixes"].get("army_power_pct", 0), mix)
    cc = canon()["units"]["counters"]
    return {**sug, "stage": st, "region": F.region_for_stage(min(st, canon()["battle"]["campaign_stages"]))["name"], "kind": F.stage_kind(st), "enemy_mix": mix,
            "class_labels": cc["class_labels"], "current_army_power": prof["army_power"], "current_formation": pl["army"]["formation"], "hero_power": prof["hero"]["power"],
            "required_power": F.enemy_required_power(st)}



# ---- domain / offline -----------------------------------------------------------------------------------
@router.get("/domain")
async def domain(p: Principal = Depends(current_user)):
    return D.domain_view(await load(p))


@router.get("/offline")
async def offline(p: Principal = Depends(current_user)):
    return O.preview(await load(p))


@router.post("/offline/claim")
async def offline_claim(p: Principal = Depends(current_user)):
    return await O.claim(await load(p))
