import hashlib
import secrets
from datetime import timedelta

import jwt
from fastapi import Depends, Request
from pwdlib import PasswordHash

from . import db
from .config import settings
from .util import aware, fail, now

passwords = PasswordHash.recommended()  # Argon2id
DUMMY_HASH = passwords.hash("idle1-dummy-constant-time-verify")
ALG = "HS256"


def hash_password(p: str) -> str:
    return passwords.hash(p)


def verify_password(p: str, h: str | None) -> bool:
    return passwords.verify(p, h or DUMMY_HASH)


def hash_secret(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def random_token() -> str:
    return secrets.token_urlsafe(48)


def numeric_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def make_access(account_id: str, player_id: str, token_version: int, sid: str) -> str:
    t = now()
    return jwt.encode(
        {
            "sub": account_id,
            "pid": player_id,
            "sid": sid,
            "ver": token_version,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": t,
            "exp": t + timedelta(minutes=settings.ACCESS_MINUTES),
        },
        settings.JWT_SECRET,
        algorithm=ALG,
    )


def decode_access(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALG], issuer=settings.JWT_ISSUER, audience=settings.JWT_AUDIENCE)


async def issue_tokens(account: dict, player_id: str, device: str | None = None) -> dict:
    refresh = random_token()
    sid = secrets.token_urlsafe(18)
    await db.refresh_sessions.insert_one(
        {
            "_id": sid,
            "account_id": account["_id"],
            "token_hash": hash_secret(refresh),
            "family_id": secrets.token_urlsafe(18),
            "revoked": False,
            "device": device,
            "expires_at": now() + timedelta(days=settings.REFRESH_DAYS),
            "created_at": now(),
        }
    )
    return {
        "access_token": make_access(account["_id"], player_id, account.get("token_version", 0), sid),
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_MINUTES * 60,
    }


async def rotate_refresh(raw: str) -> dict:
    old = await db.refresh_sessions.find_one({"token_hash": hash_secret(raw)})
    if not old or old.get("revoked") or aware(old["expires_at"]) <= now():
        if old:
            await db.refresh_sessions.update_many({"family_id": old["family_id"]}, {"$set": {"revoked": True}})
        raise fail(401, "invalid_refresh")
    # atomic claim of the old token prevents concurrent double-rotation
    claimed = await db.refresh_sessions.update_one({"_id": old["_id"], "revoked": False}, {"$set": {"revoked": True}})
    if claimed.modified_count == 0:
        raise fail(401, "invalid_refresh")
    account = await db.accounts.find_one({"_id": old["account_id"]})
    if not account or account.get("deleted_at"):
        raise fail(401, "account_unavailable")
    player = await db.players.find_one({"account_id": account["_id"]}, {"_id": 1})
    new_raw = random_token()
    sid = secrets.token_urlsafe(18)
    await db.refresh_sessions.insert_one(
        {
            "_id": sid,
            "account_id": account["_id"],
            "token_hash": hash_secret(new_raw),
            "family_id": old["family_id"],
            "revoked": False,
            "device": old.get("device"),
            "expires_at": old["expires_at"],
            "created_at": now(),
        }
    )
    await db.refresh_sessions.update_one({"_id": old["_id"]}, {"$set": {"replaced_by": sid}})
    return {
        "access_token": make_access(account["_id"], player["_id"], account.get("token_version", 0), sid),
        "refresh_token": new_raw,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_MINUTES * 60,
    }


class Principal:
    def __init__(self, account: dict, player_id: str, sid: str):
        self.account = account
        self.account_id = account["_id"]
        self.player_id = player_id
        self.sid = sid


async def current_user(request: Request) -> Principal:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise fail(401, "missing_token")
    try:
        claims = decode_access(auth[7:])
    except jwt.PyJWTError:
        raise fail(401, "invalid_token")
    account = await db.accounts.find_one({"_id": claims["sub"]})
    if not account or account.get("deleted_at"):
        raise fail(401, "account_unavailable")
    if claims.get("ver", 0) != account.get("token_version", 0):
        raise fail(401, "token_revoked")
    return Principal(account, claims["pid"], claims["sid"])


async def verified_user(p: Principal = Depends(current_user)) -> Principal:
    if not p.account.get("email_verified"):
        raise fail(403, "email_not_verified", "Verify your email to use this feature")
    return p
