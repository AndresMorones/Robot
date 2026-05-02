"""FastAPI auth dependency — validates API key on every protected endpoint.

Two accepted credential sources, both checked against `API_BEARER_TOKEN`:
  1. `x-api-key` header — preferred path; matches HR webhook config (HR's tool/POST webhooks send this)
  2. `Authorization: Bearer <token>` header — matches dashboard server-side fetch

The legacy `?token=<value>` query-string fallback was removed (see
`docs/decisions/ADR-008-api-security-hardening.md`): query-string credentials
leak into Fly access logs, Cloudflare logs, browser history, referer headers,
error pages, and screenshots. Header-only is the production posture.

Constant-time compare via hmac.compare_digest to prevent timing side-channels.
"""

import hmac

import structlog
from fastapi import Header, HTTPException, status

from app.config import settings

log = structlog.get_logger()


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
    authorization: str | None = Header(default=None),
) -> None:
    expected = settings.api_bearer_token

    if x_api_key and hmac.compare_digest(x_api_key, expected):
        return

    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and hmac.compare_digest(value, expected):
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key (x-api-key or Authorization: Bearer)",
        headers={"WWW-Authenticate": "Bearer"},
    )


require_bearer = require_api_key
