"""Account lifecycle (I01): register/verify/login/refresh/logout-all/recover/reset, Emergent Google session, export, delete."""
import re
from datetime import timedelta

import httpx

from ..core import db
from ..core.config import settings
from ..core.email import send_recovery_code, send_verification_code
from ..core.security import hash_password, hash_secret, issue_tokens, numeric_code, verify_password
from ..core.util import aware, clean, fail, new_id, now
from .player import initial_state

EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


def norm_email(e: str) -> str:
    return e.strip().casefold()


def check_password(p: str) -> None:
    if len(p) < 10 or len(p) > 256:
        raise fail(400, "weak_password", "Password must be at least 10 characters")


def check_name(n: str) -> str:
    n = n.strip()
    if not (3 <= len(n) <= 16) or not re.match(r"^[\w \-']+$", n):
        raise fail(400, "bad_display_name", "3-16 letters/numbers")
    return n


async def _issue_code(account_id: str, kind: str, minutes: int) -> str:
    code = numeric_code()
    await db.one_time_codes.delete_many({"account_id": account_id, "kind": kind})
    await db.one_time_codes.insert_one({"_id": new_id("otc_"), "account_id": account_id, "kind": kind, "code_hash": hash_secret(code), "expires_at": now() + timedelta(minutes=minutes), "attempts": 0, "created_at": now()})
    if settings.TEST_HOOKS:
        await db.one_time_codes.update_one({"account_id": account_id, "kind": kind}, {"$set": {"test_plain": code}})
    return code


async def _consume_code(account_id: str, kind: str, code: str) -> None:
    doc = await db.one_time_codes.find_one({"account_id": account_id, "kind": kind})
    if not doc or aware(doc["expires_at"]) <= now():
        raise fail(400, "code_invalid")
    if doc.get("attempts", 0) >= 5:
        raise fail(429, "code_locked", "Too many attempts, request a new code")
    if not __import__("hmac").compare_digest(doc["code_hash"], hash_secret(code.strip())):
        await db.one_time_codes.update_one({"_id": doc["_id"]}, {"$inc": {"attempts": 1}})
        raise fail(400, "code_invalid")
    await db.one_time_codes.delete_one({"_id": doc["_id"]})


async def register(email: str, password: str, display_name: str, age_confirmed: bool, consent: bool, device: str | None) -> dict:
    email = norm_email(email)
    check_password(password)
    display_name = check_name(display_name)
    if not age_confirmed:
        raise fail(403, "age_gate", f"You must be at least {settings.MIN_AGE} years old")
    if not consent:
        raise fail(400, "consent_required", "Accept Privacy Policy and Terms to continue")
    if await db.accounts.find_one({"email": email}):
        raise fail(409, "email_in_use", "Unable to create account with this email")
    acc = {"_id": new_id("acc_"), "email": email, "password_hash": hash_password(password), "email_verified": False, "providers": ["email_password"], "token_version": 0,
           "created_at": now(), "age_confirmed_at": now(), "consent_at": now(), "min_age_gate": settings.MIN_AGE, "deleted_at": None}
    await db.accounts.insert_one(acc)
    player = initial_state(acc["_id"], display_name)
    await db.players.insert_one(player)
    code = await _issue_code(acc["_id"], "verify", 24 * 60)
    email_sent = True
    try:
        await send_verification_code(email, code)
    except Exception:
        email_sent = False
    tokens = await issue_tokens(acc, player["_id"], device)
    return {**tokens, "account": public_account(acc), "player_id": player["_id"], "verification_email_sent": email_sent}


def public_account(acc: dict) -> dict:
    return {"id": acc["_id"], "email": acc["email"], "email_verified": acc.get("email_verified", False), "providers": acc.get("providers", []), "created_at": acc["created_at"].isoformat()}


async def login(email: str, password: str, device: str | None) -> dict:
    acc = await db.accounts.find_one({"email": norm_email(email)})
    ok = verify_password(password, acc.get("password_hash") if acc else None)
    if not acc or not ok or acc.get("deleted_at"):
        raise fail(401, "invalid_credentials", "Invalid email or password")
    player = await db.players.find_one({"account_id": acc["_id"]}, {"_id": 1})
    tokens = await issue_tokens(acc, player["_id"], device)
    return {**tokens, "account": public_account(acc), "player_id": player["_id"]}


async def verify_email(account: dict, code: str) -> dict:
    await _consume_code(account["_id"], "verify", code)
    await db.accounts.update_one({"_id": account["_id"]}, {"$set": {"email_verified": True, "verified_at": now()}})
    return {"email_verified": True}


async def resend_verification(account: dict) -> dict:
    if account.get("email_verified"):
        return {"email_verified": True}
    code = await _issue_code(account["_id"], "verify", 24 * 60)
    await send_verification_code(account["email"], code)
    return {"sent": True}


async def forgot_password(email: str) -> dict:
    acc = await db.accounts.find_one({"email": norm_email(email), "deleted_at": None})
    if acc and "email_password" in acc.get("providers", []):
        code = await _issue_code(acc["_id"], "reset", 30)
        try:
            await send_recovery_code(acc["email"], code)
        except Exception:
            pass
    return {"message": "If the address is registered, a recovery code was sent."}


async def reset_password(email: str, code: str, new_password: str) -> dict:
    check_password(new_password)
    acc = await db.accounts.find_one({"email": norm_email(email), "deleted_at": None})
    if not acc:
        raise fail(400, "code_invalid")
    await _consume_code(acc["_id"], "reset", code)
    await db.accounts.update_one({"_id": acc["_id"]}, {"$set": {"password_hash": hash_password(new_password)}, "$inc": {"token_version": 1}})
    await db.refresh_sessions.update_many({"account_id": acc["_id"]}, {"$set": {"revoked": True}})
    return {"reset": True}


async def change_password(account: dict, current: str, new_password: str) -> dict:
    if not verify_password(current, account.get("password_hash")):
        raise fail(401, "invalid_credentials")
    check_password(new_password)
    await db.accounts.update_one({"_id": account["_id"]}, {"$set": {"password_hash": hash_password(new_password)}, "$inc": {"token_version": 1}})
    await db.refresh_sessions.update_many({"account_id": account["_id"]}, {"$set": {"revoked": True}})
    return {"changed": True}


async def logout_all(account: dict) -> dict:
    await db.refresh_sessions.update_many({"account_id": account["_id"]}, {"$set": {"revoked": True}})
    await db.accounts.update_one({"_id": account["_id"]}, {"$inc": {"token_version": 1}})
    return {"ok": True}


async def logout(refresh_token: str) -> dict:
    await db.refresh_sessions.update_one({"token_hash": hash_secret(refresh_token)}, {"$set": {"revoked": True}})
    return {"ok": True}


async def google_session(session_id: str, device: str | None) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": session_id})
    if r.status_code != 200:
        raise fail(401, "invalid_session")
    data = r.json()
    email = norm_email(data.get("email", ""))
    if not email:
        raise fail(401, "invalid_session")
    acc = await db.accounts.find_one({"email": email})
    if acc and acc.get("deleted_at"):
        raise fail(401, "account_unavailable")
    if not acc:
        acc = {"_id": new_id("acc_"), "email": email, "password_hash": None, "email_verified": True, "providers": ["google"], "token_version": 0, "created_at": now(),
               "age_confirmed_at": None, "consent_at": None, "min_age_gate": settings.MIN_AGE, "deleted_at": None, "google_name": data.get("name"), "picture": data.get("picture")}
        await db.accounts.insert_one(acc)
        name = check_name(re.sub(r"[^\w \-']", "", (data.get("name") or "Lord")[:16]) or "Lord")
        await db.players.insert_one(initial_state(acc["_id"], name))
    else:
        if "google" not in acc.get("providers", []):
            await db.accounts.update_one({"_id": acc["_id"]}, {"$addToSet": {"providers": "google"}, "$set": {"email_verified": True}})
            acc["email_verified"] = True
    player = await db.players.find_one({"account_id": acc["_id"]}, {"_id": 1})
    tokens = await issue_tokens(acc, player["_id"], device)
    return {**tokens, "account": public_account(acc), "player_id": player["_id"], "needs_consent": acc.get("consent_at") is None}


async def accept_consent(account: dict, age_confirmed: bool) -> dict:
    if not age_confirmed:
        raise fail(403, "age_gate")
    await db.accounts.update_one({"_id": account["_id"]}, {"$set": {"consent_at": now(), "age_confirmed_at": now()}})
    return {"consent_at": now().isoformat()}


async def export_data(account: dict, player_id: str) -> dict:
    p = await db.players.find_one({"_id": player_id})
    items = await db.gear_items.find({"owner_id": player_id}).to_list(400)
    purchases = await db.purchases.find({"player_id": player_id}, {"raw": 0}).to_list(200)
    msgs = await db.chat_messages.find({"player_id": player_id}).sort("created_at", -1).limit(500).to_list(500)
    await db.export_requests.insert_one({"_id": new_id("exp_"), "account_id": account["_id"], "created_at": now(), "delivered": "inline"})
    return {"exported_at": now().isoformat(), "account": public_account(account), "player": clean({k: v for k, v in p.items() if k != "recent_ledger_keys"}), "gear_items": [clean(i) for i in items],
            "purchases": [clean(x) for x in purchases], "chat_messages": [clean(m) for m in msgs]}


async def delete_account(account: dict, player_id: str, password: str | None) -> dict:
    if "email_password" in account.get("providers", []) and not verify_password(password or "", account.get("password_hash")):
        raise fail(401, "invalid_credentials", "Confirm your password to delete the account")
    anon = f"deleted_{account['_id']}@deleted.invalid"
    await db.accounts.update_one({"_id": account["_id"]}, {"$set": {"deleted_at": now(), "email": anon, "password_hash": None, "google_name": None, "picture": None}, "$inc": {"token_version": 1}})
    await db.refresh_sessions.update_many({"account_id": account["_id"]}, {"$set": {"revoked": True}})
    await db.one_time_codes.delete_many({"account_id": account["_id"]})
    await db.players.update_one({"_id": player_id}, {"$set": {"deleted_at": now(), "display_name": "Lord (deleted)", "alliance_id": None}})
    await db.alliance_members.delete_many({"player_id": player_id})
    await db.gear_items.delete_many({"owner_id": player_id})
    await db.chat_messages.update_many({"player_id": player_id}, {"$set": {"deleted_at": now(), "display_name": "[deleted]", "text": ""}})
    await db.notifications.delete_many({"player_id": player_id})
    # purchases/entitlements/ledgers are retained for store/financial reconciliation only (canonical privacy rule)
    await db.audit_events.insert_one({"_id": new_id("aud_"), "player_id": player_id, "kind": "account_deleted", "created_at": now()})
    return {"deleted": True}
