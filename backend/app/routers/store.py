from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from ..core import db
from ..core.push import register_device
from ..core.security import Principal, current_user
from ..core.util import clean, fail, now
from ..domain import cosmetics as CS
from ..domain import player as P
from ..domain import store as S

router = APIRouter(tags=["store"])


class CrateIn(BaseModel):
    key: str


class VerifyIn(BaseModel):
    product_id: str | None = None
    transaction_id: str | None = None
    store: str | None = None


class PushIn(BaseModel):
    user_id: str
    platform: str
    device_token: str


class ReadIn(BaseModel):
    ids: list[str] | None = None


@router.get("/store/catalog")
async def catalog(p: Principal = Depends(current_user)):
    c = S.catalog()
    c["entitlements"] = await S.entitlements_view(p.player_id)
    return c


@router.post("/store/crate")
async def crate(body: CrateIn, p: Principal = Depends(current_user)):
    return await S.buy_crate(await P.load(p.player_id), body.key)


class SkinIn(BaseModel):
    key: str


class EquipSkinIn(BaseModel):
    kind: str
    key: str | None = None


@router.get("/store/cosmetics")
async def cosmetics(p: Principal = Depends(current_user)):
    return CS.view(await P.load(p.player_id))


@router.post("/store/cosmetics/buy")
async def cosmetics_buy(body: SkinIn, p: Principal = Depends(current_user)):
    return await CS.buy(await P.load(p.player_id), body.key)


@router.post("/store/cosmetics/equip")
async def cosmetics_equip(body: EquipSkinIn, p: Principal = Depends(current_user)):
    return await CS.equip(await P.load(p.player_id), body.kind, body.key)


@router.post("/purchases/verify")
async def verify(body: VerifyIn, p: Principal = Depends(current_user)):
    """Server-side verification against RevenueCat; never credits from client claims."""
    return await S.sync_subscriber(p.player_id)


@router.post("/purchases/restore")
async def restore(p: Principal = Depends(current_user)):
    return await S.sync_subscriber(p.player_id)


@router.post("/purchases/revenuecat/webhook")
async def webhook(request: Request, authorization: str | None = Header(default=None), x_revenuecat_webhook_signature: str | None = Header(default=None)):
    return await S.handle_webhook(await request.body(), authorization, x_revenuecat_webhook_signature)


@router.get("/notifications")
async def notifications(p: Principal = Depends(current_user)):
    rows = await db.notifications.find({"player_id": p.player_id}).sort("created_at", -1).limit(100).to_list(100)
    return {"notifications": [clean(n) for n in rows], "unread": sum(1 for n in rows if not n.get("read"))}


@router.post("/notifications/read")
async def mark_read(body: ReadIn, p: Principal = Depends(current_user)):
    flt = {"player_id": p.player_id}
    if body.ids:
        flt["_id"] = {"$in": body.ids}
    res = await db.notifications.update_many(flt, {"$set": {"read": True, "read_at": now()}})
    return {"updated": res.modified_count}


@router.post("/register-push", status_code=201)
async def register_push(body: PushIn, p: Principal = Depends(current_user)):
    if body.user_id != p.player_id:
        raise fail(403, "user_mismatch")
    if body.platform not in ("android", "ios"):
        raise fail(400, "bad_platform")
    await register_device(body.user_id, body.platform, body.device_token)
    return {"status": "registered"}
