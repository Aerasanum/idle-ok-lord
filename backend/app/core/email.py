"""Emergent managed transactional email (Resend proxy). Templates are fixed server-side (G2/G4)."""
import ipaddress
import logging
import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from .config import settings

logger = logging.getLogger("idle1.email")
EMAIL_BASE_URL = "https://integrations.emergentagent.com"

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = (
    "reply with your password", "reply with the code", "send your password", "cvv", "send us your password",
    "enter your password below", "confirm your card number", "your full card number", "seed phrase",
    "recovery phrase", "verify your card", "social security number", "confirm your bank details",
)
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str) -> str | None:
    _assert_safe_email(subject, html)
    if not settings.EMAIL_KEY or not settings.EMAIL_FROM_NAME:
        raise HTTPException(status_code=503, detail="Email service not configured")
    payload = {"to": [to], "subject": subject, "html": html, "from_name": settings.EMAIL_FROM_NAME}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": settings.EMAIL_KEY}, json=payload)
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPStatusError as e:
        logger.error("Email send failed: %s %s", e.response.status_code, e.response.text)
        raise HTTPException(status_code=502, detail="Failed to send email")
    except Exception as e:
        logger.error("Email send error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to send email")


def _wrap(title: str, body: str) -> str:
    brand = escape(settings.EMAIL_FROM_NAME)
    return (
        '<table role="presentation" width="100%" style="background:#11151C;padding:24px 0"><tr><td align="center">'
        '<table role="presentation" width="520" style="background:#F4EBD8;border:3px solid #B89947;border-radius:6px;'
        'font-family:Georgia,serif;color:#11151C"><tr><td style="padding:28px">'
        f'<h1 style="margin:0 0 16px;font-size:24px;color:#800020">{escape(title)}</h1>{body}'
        f'<p style="font-size:12px;color:#555;margin-top:24px">Sent by {brand}. We never ask for your password by email.</p>'
        "</td></tr></table></td></tr></table>"
    )


async def send_verification_code(to: str, code: str) -> None:
    body = (
        f"<p>Welcome, Lord. Enter this code in the app to verify your account:</p>"
        f'<p style="font-size:32px;letter-spacing:8px;font-weight:bold;color:#2E472D">{escape(code)}</p>'
        "<p>The code expires in 24 hours.</p>"
    )
    await send_email(to=to, subject=f"{settings.EMAIL_FROM_NAME} - verify your account", html=_wrap("Verify your account", body))


async def send_recovery_code(to: str, code: str) -> None:
    body = (
        "<p>A password recovery was requested for your account. Enter this code in the app to choose a new password:</p>"
        f'<p style="font-size:32px;letter-spacing:8px;font-weight:bold;color:#2E472D">{escape(code)}</p>'
        "<p>The code expires in 30 minutes. If you did not request this, you can ignore this email.</p>"
    )
    await send_email(to=to, subject=f"{settings.EMAIL_FROM_NAME} - password recovery", html=_wrap("Password recovery", body))
