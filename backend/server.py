"""IDLE 1 v1.1 backend - FastAPI application entrypoint (routes prefixed with /api)."""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core import db
from app.core.canon import canon, validation_report
from app.core.config import settings
from app.core.ratelimit import limiter
from app.domain import scheduler
from app.routers import auth, game, liveops, social, store

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("idle1")


@asynccontextmanager
async def lifespan(app: FastAPI):
    canon()  # fail fast if canonical spec is missing/invalid
    logger.info("Canonical validation: %s", validation_report())
    await db.ensure_indexes()
    task = asyncio.create_task(scheduler.run_forever())
    yield
    task.cancel()
    db.client.close()


app = FastAPI(title="IDLE 1 v1.1 API", version="1.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["http://localhost"],
    allow_origin_regex=r"https://.*\.emergentagent\.com" if settings.ENV != "production" else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": {"code": "internal_error", "message": "Internal server error"}})


API = "/api"
app.include_router(auth.router, prefix=API)
app.include_router(auth.acc_router, prefix=API)
app.include_router(game.router, prefix=API)
app.include_router(liveops.router, prefix=API)
app.include_router(social.router, prefix=API)
app.include_router(store.router, prefix=API)

RULES_PDF = Path(__file__).parent / "static" / "IDLE1_Regolamento.pdf"


@app.get(f"{API}/docs/regolamento.pdf", include_in_schema=False)
async def rules_pdf():
    """Public, read-only rulebook generated from the canonical spec (scripts/gen_rules_pdf.py)."""
    if not RULES_PDF.exists():
        return JSONResponse(status_code=404, content={"detail": {"code": "not_found", "message": "Regolamento non generato"}})
    return FileResponse(RULES_PDF, media_type="application/pdf", filename="IDLE1_Regolamento.pdf", content_disposition_type="inline",
                        headers={"Cache-Control": "public, max-age=3600"})

if settings.TEST_HOOKS:
    from app.routers import test_hooks

    app.include_router(test_hooks.router, prefix=API)
    logger.warning("TEST HOOKS ENABLED (preview only)")


@app.get(f"{API}/")
async def root():
    return {"project": "IDLE 1", "version": "1.1", "status": "ok", "canon": validation_report()}


@app.get(f"{API}/health")
async def health():
    await db.db.command("ping")
    return {"ok": True, "env": settings.ENV}
