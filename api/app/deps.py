"""FastAPI dependencies (auth)."""

import hmac

import structlog
from fastapi import Header, HTTPException, Query, status

from app.config import settings

log = structlog.get_logger()


def require_bearer(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> None:
    """Authenticate via Authorization header (preferred) or `?token=` query (fallback).

    Constant-time compare to prevent timing side-channels. Header takes precedence
    when both are supplied. Query-string path emits a warning so we can quantify
    HappyRobot's tier behavior over time.
    """
    expected = settings.api_bearer_token

    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and hmac.compare_digest(value, expected):
            return

    if token and hmac.compare_digest(token, expected):
        log.warning("auth.query_string_used")
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
