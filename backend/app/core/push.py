"""Emergent managed push relay (SuprSend passthrough). Backend-only calls."""
import logging

import httpx
from fastapi import HTTPException

from .config import settings

logger = logging.getLogger("idle1.push")
PUSH_BASE_URL = "https://integrations.emergentagent.com"
_client = httpx.AsyncClient(base_url=PUSH_BASE_URL, headers={"X-Push-Key": settings.PUSH_KEY}, timeout=10.0)


async def register_device(user_id: str, platform: str, device_token: str) -> None:
    resp = await _client.post("/api/v1/push/users/register", json={"user_id": user_id, "platform": platform, "device_token": device_token})
    if resp.status_code == 401:
        raise HTTPException(500, "EMERGENT_PUSH_KEY missing or invalid")
    if resp.status_code >= 500:
        raise HTTPException(502, "Push provider unavailable")
    resp.raise_for_status()


async def send_push(recipients: list[str], data: dict, idempotency_key: str | None = None) -> None:
    if not recipients:
        return
    if len(recipients) > 100:
        raise ValueError("max 100 recipients per /trigger call; chunk before sending")
    if "title" not in data or "message" not in data:
        raise ValueError("data must include title and message")
    payload: dict = {"recipients": recipients, "data": data}
    if idempotency_key:
        payload["$idempotency_key"] = idempotency_key
    resp = await _client.post("/api/v1/push/trigger", json=payload)
    if resp.status_code == 401:
        raise HTTPException(500, "EMERGENT_PUSH_KEY missing or invalid")
    if resp.status_code >= 500:
        raise HTTPException(502, "Push provider unavailable")
    resp.raise_for_status()


async def safe_push(recipients: list[str], data: dict, idempotency_key: str | None = None) -> None:
    try:
        await send_push(recipients, data, idempotency_key)
    except Exception as e:  # push must never block gameplay
        logger.warning("Push failed (non-blocking): %s", e)
