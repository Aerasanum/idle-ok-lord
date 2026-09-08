import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _req(name: str) -> str:
    v = os.environ.get(name)
    if v is None or v == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


class Settings:
    MONGO_URL = _req("MONGO_URL")
    DB_NAME = _req("DB_NAME")
    ENV = os.environ.get("IDLE1_ENV", "production")
    JWT_SECRET = _req("JWT_SECRET")
    JWT_ISSUER = os.environ.get("JWT_ISSUER", "idle1-api")
    JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "idle1-mobile")
    ACCESS_MINUTES = int(os.environ.get("ACCESS_TOKEN_MINUTES", "15"))
    REFRESH_DAYS = int(os.environ.get("REFRESH_TOKEN_DAYS", "30"))
    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
    EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
    EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "")
    PUSH_KEY = os.environ.get("EMERGENT_PUSH_KEY", "placeholder")
    RC_SECRET = os.environ.get("REVENUECAT_SECRET_KEY", "")
    RC_WEBHOOK_TOKEN = os.environ.get("REVENUECAT_WEBHOOK_TOKEN", "")
    RC_WEBHOOK_SIGNING_SECRET = os.environ.get("REVENUECAT_WEBHOOK_SIGNING_SECRET", "")
    TEST_HOOKS = os.environ.get("TEST_HOOKS_ENABLED", "false").lower() == "true"
    RATE_LIMIT_DISABLED = os.environ.get("RATE_LIMIT_DISABLED", "false").lower() == "true"  # QA/load simulations only; refused in production
    MIN_AGE = int(os.environ.get("MIN_AGE_GATE", "13"))
    PRIVACY_URL = os.environ.get("PRIVACY_POLICY_URL", "")
    TERMS_URL = os.environ.get("TERMS_URL", "")
    CANON_PATH = ROOT / "canon" / "IDLE_1_v1.1_CANONICAL_SPEC.json"


settings = Settings()

if len(settings.JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET too short (min 32 chars)")
if settings.ENV == "production" and settings.TEST_HOOKS:
    raise RuntimeError("TEST_HOOKS_ENABLED must be false in production")
if settings.ENV == "production" and settings.RATE_LIMIT_DISABLED:
    raise RuntimeError("RATE_LIMIT_DISABLED must be false in production")
