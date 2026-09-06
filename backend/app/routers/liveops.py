from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.security import Principal, current_user
from ..domain import liveops as L
from ..domain import player as P

router = APIRouter(tags=["liveops"])


async def load(p: Principal) -> dict:
    return await P.load(p.player_id)


class DeployIn(BaseModel):
    index: int = Field(ge=0, le=3)


class IdIn(BaseModel):
    id: str


class TrackIn(BaseModel):
    tier: int
    premium: bool = False


class DungeonIn(BaseModel):
    key: str
    tier: int = Field(ge=1, le=10)


class ChestIn(BaseModel):
    kind: str
    index: int


class KeyIn(BaseModel):
    key: str


class PctIn(BaseModel):
    pct: int


class SeasonIn(BaseModel):
    level: int
    premium: bool = False


@router.get("/events")
async def events(p: Principal = Depends(current_user)):
    return await L.event_view(await load(p))


@router.post("/events/deploy")
async def deploy(body: DeployIn, p: Principal = Depends(current_user)):
    return await L.deploy(await load(p), body.index)


@router.post("/events/claim")
async def claim_dep(body: IdIn, p: Principal = Depends(current_user)):
    return await L.claim_deployment(await load(p), body.id)


@router.post("/events/instant-finish")
async def instant(body: IdIn, p: Principal = Depends(current_user)):
    return await L.instant_finish(await load(p), body.id)


@router.post("/events/refill")
async def refill(p: Principal = Depends(current_user)):
    return await L.refill_energy(await load(p))


@router.post("/events/booster")
async def booster(p: Principal = Depends(current_user)):
    return await L.buy_booster(await load(p))


@router.post("/events/track/claim")
async def track(body: TrackIn, p: Principal = Depends(current_user)):
    return await L.claim_track(await load(p), body.tier, body.premium)


@router.get("/dungeons")
async def dungeons(p: Principal = Depends(current_user)):
    return await L.dungeons_view(await load(p))


@router.post("/dungeons/start")
async def d_start(body: DungeonIn, p: Principal = Depends(current_user)):
    return await L.start_dungeon(await load(p), body.key, body.tier)


@router.post("/dungeons/claim")
async def d_claim(body: IdIn, p: Principal = Depends(current_user)):
    return await L.claim_dungeon(await load(p), body.id)


@router.post("/dungeons/speedup")
async def d_speed(body: IdIn, p: Principal = Depends(current_user)):
    return await L.speedup_dungeon(await load(p), body.id)


@router.get("/quests")
async def quests(p: Principal = Depends(current_user)):
    return L.quests_view(await load(p))


@router.post("/quests/claim")
async def q_claim(body: ChestIn, p: Principal = Depends(current_user)):
    return await L.claim_quest_chest(await load(p), body.kind, body.index)


@router.post("/quests/login/claim")
async def login_claim(p: Principal = Depends(current_user)):
    return await L.claim_login(await load(p))


@router.get("/achievements")
async def achievements(p: Principal = Depends(current_user)):
    return L.achievements_view(await load(p))


@router.post("/achievements/claim")
async def a_claim(body: KeyIn, p: Principal = Depends(current_user)):
    return await L.claim_achievement(await load(p), body.key)


@router.get("/codex")
async def codex(p: Principal = Depends(current_user)):
    return L.codex_view(await load(p))


@router.post("/codex/claim")
async def c_claim(body: PctIn, p: Principal = Depends(current_user)):
    return await L.claim_codex(await load(p), body.pct)


@router.get("/season")
async def season(p: Principal = Depends(current_user)):
    return L.season_view(await load(p))


@router.post("/season/claim")
async def s_claim(body: SeasonIn, p: Principal = Depends(current_user)):
    return await L.claim_season(await load(p), body.level, body.premium)
