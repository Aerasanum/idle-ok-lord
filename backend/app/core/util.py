import hashlib
import math
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def rnd(x: float) -> int:
    """Canonical round(): half away from zero, as in the spec tables."""
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def ceil(x: float) -> int:
    return int(math.ceil(x))


def seeded_rng(*parts: Any) -> random.Random:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def day_key(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d")


def week_key(dt: datetime | None = None) -> str:
    d = dt or now()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def week_start(dt: datetime | None = None) -> datetime:
    d = (dt or now()).replace(hour=0, minute=0, second=0, microsecond=0)
    return d - timedelta(days=d.weekday())


def fail(status: int, code: str, detail: str | None = None) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": detail or code})


def clean(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        elif isinstance(v, datetime):
            out[k] = iso(aware(v))
        elif isinstance(v, dict):
            out[k] = clean(v)
        elif isinstance(v, list):
            out[k] = [clean(x) if isinstance(x, dict) else (iso(aware(x)) if isinstance(x, datetime) else x) for x in v]
        else:
            out[k] = v
    return out
