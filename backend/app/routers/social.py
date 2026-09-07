from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..core.ratelimit import limiter
from ..core.security import Principal, current_user, verified_user
from ..domain import player as P
from ..domain import social as S
from ..domain import wars as W

router = APIRouter(tags=["social"])


async def load(p: Principal) -> dict:
    return await P.load(p.player_id)


class CreateIn(BaseModel):
    name: str
    tag: str
    join_mode: str = "open"
    description: str = ""
    language: str = "it"


class IdIn(BaseModel):
    id: str


class DecideIn(BaseModel):
    player_id: str
    accept: bool


class MemberIn(BaseModel):
    player_id: str
    action: str


class SettingsIn(BaseModel):
    join_mode: str | None = None
    description: str | None = None


class DonateIn(BaseModel):
    gold: int = Field(ge=1)


class MessageIn(BaseModel):
    channel: str
    text: str


class ModerateIn(BaseModel):
    action: str
    target_id: str | None = None
    message_id: str | None = None
    channel: str | None = None
    minutes: int | None = None
    reason: str | None = None


class DeclareIn(BaseModel):
    node_id: int = Field(ge=0, le=360)


class RosterIn(BaseModel):
    war_id: str
    player_ids: list[str]


class TierIn(BaseModel):
    tier: int = Field(ge=1, le=10)


@router.get("/alliances")
async def list_alliances(q: str | None = None, language: str | None = None, p: Principal = Depends(current_user)):
    return {"alliances": await S.list_alliances(q, language)}


@router.get("/alliances/mine")
async def mine(p: Principal = Depends(current_user)):
    me = await S.membership(p.player_id)
    if not me:
        return {"alliance": None}
    return {"alliance": await S.alliance_view(me["alliance_id"], p.player_id)}


@router.get("/alliances/{alliance_id}")
async def alliance(alliance_id: str, p: Principal = Depends(current_user)):
    return {"alliance": await S.alliance_view(alliance_id, p.player_id)}


@router.post("/alliances")
async def create(body: CreateIn, p: Principal = Depends(verified_user)):
    return await S.create_alliance(await load(p), body.name, body.tag, body.join_mode, body.description, body.language)


@router.post("/alliances/join")
async def join(body: IdIn, p: Principal = Depends(verified_user)):
    return await S.join(await load(p), body.id)


@router.post("/alliances/applications/decide")
async def decide(body: DecideIn, p: Principal = Depends(current_user)):
    return await S.decide_application(await load(p), body.player_id, body.accept)


@router.post("/alliances/leave")
async def leave(p: Principal = Depends(current_user)):
    return await S.leave(await load(p))


@router.post("/alliances/members")
async def members(body: MemberIn, p: Principal = Depends(current_user)):
    return await S.manage_member(await load(p), body.player_id, body.action)


@router.patch("/alliances/settings")
async def settings(body: SettingsIn, p: Principal = Depends(current_user)):
    return await S.update_settings(await load(p), body.join_mode, body.description)


@router.post("/alliances/donate")
async def donate(body: DonateIn, p: Principal = Depends(current_user)):
    return await S.donate(await load(p), body.gold)


@router.get("/chat/messages")
async def messages(channel: str = Query(...), before: str | None = None, limit: int = 50, p: Principal = Depends(current_user)):
    return {"messages": await S.list_messages(await load(p), channel, before, limit)}


@router.post("/chat/messages")
@limiter.limit("30/minute")
async def post(request: Request, body: MessageIn, p: Principal = Depends(verified_user)):
    return await S.post_message(await load(p), body.channel, body.text)


@router.post("/chat/moderate")
async def moderate(body: ModerateIn, p: Principal = Depends(current_user)):
    return await S.moderate(await load(p), body.action, body.target_id, body.message_id, body.channel, body.minutes, body.reason)


@router.get("/wars/map")
async def war_map(p: Principal = Depends(current_user)):
    return await W.map_view(await load(p))


@router.get("/wars")
async def wars(p: Principal = Depends(current_user)):
    return await W.list_wars(await load(p))


@router.get("/wars/{war_id}")
async def war(war_id: str, p: Principal = Depends(current_user)):
    return await W.war_detail(await load(p), war_id)


@router.post("/wars/declare")
async def declare(body: DeclareIn, p: Principal = Depends(verified_user)):
    return await W.declare(await load(p), body.node_id)


@router.post("/wars/{war_id}/enlist")
async def war_enlist(war_id: str, p: Principal = Depends(current_user)):
    return await W.enlist(await load(p), war_id)


@router.post("/wars/{war_id}/withdraw")
async def war_withdraw(war_id: str, p: Principal = Depends(current_user)):
    return await W.withdraw(await load(p), war_id)


@router.post("/wars/roster")
async def roster(body: RosterIn, p: Principal = Depends(current_user)):
    return await W.set_roster(await load(p), body.war_id, body.player_ids)


@router.get("/alliance-boss")
async def boss(p: Principal = Depends(current_user)):
    return await W.boss_view(await load(p))


@router.post("/alliance-boss/start")
async def boss_start(body: TierIn, p: Principal = Depends(current_user)):
    return await W.start_boss(await load(p), body.tier)


@router.post("/alliance-boss/attack")
async def boss_attack(p: Principal = Depends(current_user)):
    return await W.attack_boss(await load(p))
