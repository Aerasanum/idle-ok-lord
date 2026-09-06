from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from ..core import db
from ..core.config import settings
from ..core.ratelimit import limiter
from ..core.security import Principal, current_user, rotate_refresh
from ..core.util import clean, now
from ..domain import account as A
from ..domain import store as S

router = APIRouter(prefix="/auth", tags=["auth"])
acc_router = APIRouter(prefix="/account", tags=["account"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    display_name: str = Field(min_length=1, max_length=32)
    age_confirmed: bool = False
    consent: bool = False
    device: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    device: str | None = None


class RefreshIn(BaseModel):
    refresh_token: str


class CodeIn(BaseModel):
    code: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class SessionIn(BaseModel):
    session_id: str
    device: str | None = None


class ChangePwIn(BaseModel):
    current_password: str
    new_password: str


class DeleteIn(BaseModel):
    password: str | None = None
    confirm: str


class ConsentIn(BaseModel):
    age_confirmed: bool


class SettingsIn(BaseModel):
    push_nonessential: bool | None = None
    analytics: bool | None = None
    language: str | None = None
    display_name: str | None = None
    heraldic_color: str | None = None


@router.post("/register", status_code=201)
@limiter.limit("10/minute")
async def register(request: Request, body: RegisterIn):
    return await A.register(body.email, body.password, body.display_name, body.age_confirmed, body.consent, body.device)


@router.post("/login")
@limiter.limit("20/minute")
async def login(request: Request, body: LoginIn):
    return await A.login(body.email, body.password, body.device)


@router.post("/refresh")
@limiter.limit("60/minute")
async def refresh(request: Request, body: RefreshIn):
    return await rotate_refresh(body.refresh_token)


@router.post("/logout")
async def logout(body: RefreshIn):
    return await A.logout(body.refresh_token)


@router.post("/logout-all")
async def logout_all(p: Principal = Depends(current_user)):
    return await A.logout_all(p.account)


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(request: Request, body: CodeIn, p: Principal = Depends(current_user)):
    return await A.verify_email(p.account, body.code)


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend(request: Request, p: Principal = Depends(current_user)):
    return await A.resend_verification(p.account)


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot(request: Request, body: ForgotIn):
    return await A.forgot_password(body.email)


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset(request: Request, body: ResetIn):
    return await A.reset_password(body.email, body.code, body.new_password)


@router.post("/session")
@limiter.limit("20/minute")
async def session(request: Request, body: SessionIn):
    return await A.google_session(body.session_id, body.device)


@router.get("/me")
async def me(p: Principal = Depends(current_user)):
    player = await db.players.find_one({"_id": p.player_id}, {"display_name": 1, "hero.level": 1, "settings": 1, "heraldic_color": 1})
    return {"account": A.public_account(p.account), "player_id": p.player_id, "display_name": player.get("display_name") if player else None, "settings": (player or {}).get("settings"),
            "needs_consent": p.account.get("consent_at") is None, "legal": {"privacy_policy_url": settings.PRIVACY_URL or None, "terms_url": settings.TERMS_URL or None, "min_age": settings.MIN_AGE}}


@acc_router.post("/consent")
async def consent(body: ConsentIn, p: Principal = Depends(current_user)):
    return await A.accept_consent(p.account, body.age_confirmed)


@acc_router.post("/change-password")
async def change_pw(body: ChangePwIn, p: Principal = Depends(current_user)):
    return await A.change_password(p.account, body.current_password, body.new_password)


@acc_router.get("/export")
@limiter.limit("3/minute")
async def export(request: Request, p: Principal = Depends(current_user)):
    return await A.export_data(p.account, p.player_id)


@acc_router.post("/delete")
async def delete(body: DeleteIn, p: Principal = Depends(current_user)):
    if body.confirm != "DELETE":
        from ..core.util import fail
        raise fail(400, "confirm_required", "Type DELETE to confirm")
    return await A.delete_account(p.account, p.player_id, body.password)


@acc_router.patch("/settings")
async def update_settings(body: SettingsIn, p: Principal = Depends(current_user)):
    sets = {}
    for k in ("push_nonessential", "analytics", "language"):
        v = getattr(body, k)
        if v is not None:
            sets[f"settings.{k}"] = v
    if body.display_name is not None:
        sets["display_name"] = A.check_name(body.display_name)
    if body.heraldic_color is not None and __import__("re").match(r"^#[0-9A-Fa-f]{6}$", body.heraldic_color):
        sets["heraldic_color"] = body.heraldic_color
    if sets:
        sets["updated_at"] = now()
        await db.players.update_one({"_id": p.player_id}, {"$set": sets, "$inc": {"version": 1}})
    return {"updated": list(sets)}


@acc_router.get("/purchases")
async def purchases(p: Principal = Depends(current_user)):
    return {"purchases": await S.purchase_history(p.player_id), "entitlements": await S.entitlements_view(p.player_id)}


@acc_router.get("/legal")
async def legal():
    return {"privacy_policy_url": settings.PRIVACY_URL or None, "terms_url": settings.TERMS_URL or None, "min_age": settings.MIN_AGE,
            "note": "Final legal wording and public URLs are owner deployment inputs (CANONICAL_SPEC privacy_account.legal_copy)."}
