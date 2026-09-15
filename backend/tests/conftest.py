import os
import sys
import uuid
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

# The suites import `server` and `qa_fixtures` from the backend root, which is only
# on sys.path automatically when pytest is invoked as `python -m pytest` from there.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DB_NAME"] = "idle1_test"
os.environ["TEST_HOOKS_ENABLED"] = "true"
os.environ["IDLE1_ENV"] = "test"

from server import app  # noqa: E402
from app.core import db  # noqa: E402
from app.core import email as email_mod  # noqa: E402
from app.core.config import settings  # noqa: E402


async def _fake_send_email(*, to: str, subject: str, html: str) -> str:
    """Tests never hit the Resend proxy (it blocks synthetic recipients); the G2/G3 content guard still runs."""
    email_mod._assert_safe_email(subject, html)
    return "test-email-id"


email_mod.send_email = _fake_send_email


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_db():
    db.rebind(AsyncIOMotorClient(settings.MONGO_URL, uuidRepresentation="standard"))
    await db.client.drop_database("idle1_test")
    await db.ensure_indexes()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api") as c:
        yield c


async def register(client: AsyncClient, verified: bool = True, name: str = "TestLord") -> dict:
    email = f"t_{uuid.uuid4().hex[:10]}@example.com"
    r = await client.post("/auth/register", json={"email": email, "password": "StrongPass!2026", "display_name": name, "age_confirmed": True, "consent": True})
    assert r.status_code == 201, r.text
    d = r.json()
    d["email"] = email
    d["headers"] = {"Authorization": f"Bearer {d['access_token']}"}
    if verified:
        code = (await client.get(f"/_test/last-code?email={email}")).json()["code"]
        v = await client.post("/auth/verify-email", json={"code": code}, headers=d["headers"])
        assert v.status_code == 200, v.text
    return d


async def grant(client: AsyncClient, h: dict, **kw):
    r = await client.post("/_test/grant", json=kw, headers=h)
    assert r.status_code == 200, r.text


async def shift(client: AsyncClient, h: dict, seconds: int):
    r = await client.post("/_test/time-shift", json={"seconds": seconds}, headers=h)
    assert r.status_code == 200, r.text
