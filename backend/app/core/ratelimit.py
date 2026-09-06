from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["600/minute"])

from .config import settings  # noqa: E402

if settings.ENV == "test":
    limiter.enabled = False
