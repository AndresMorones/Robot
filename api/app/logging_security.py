"""structlog processors + helpers for credential-safe logging.

Layered defense against secret leakage into structured log output:

* `scrub_secrets_processor` — walks every log event_dict and replaces matches of
  known secret shapes (HR `sk_live_...` keys, full `Authorization: Bearer ...`
  header values, the literal `API_BEARER_TOKEN` value) with `<redacted>`.
* `safe_request_log_fields` — filters request metadata (headers / query / etc.)
  before binding into the structlog context, so the raw `Authorization` header
  value never reaches the logger in the first place.

The scrubber is the last line of defense. The middleware filter is the first.
Both are mounted in `app.main` (structlog config + request middleware).
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from app.config import settings

REDACTED = "<redacted>"

# Match HR `sk_live_<30+ chars>` keys.
_HR_KEY_RE = re.compile(r"sk_live_[a-zA-Z0-9_-]{30,}")

# Match `Bearer <token>` header values (case-insensitive scheme).
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9._\-]{20,}")


def _redact_text(value: str) -> str:
    """Apply every scrubber regex + literal-token compare to a string."""
    if not value:
        return value
    out = _HR_KEY_RE.sub(REDACTED, value)
    out = _BEARER_RE.sub(f"Bearer {REDACTED}", out)
    # Literal compare on the configured Bearer token (covers raw token logging).
    token = settings.api_bearer_token
    if token and len(token) >= 8 and token in out:
        out = out.replace(token, REDACTED)
    return out


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, Mapping):
        return {k: _scrub_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        scrubbed = [_scrub_value(v) for v in value]
        return type(value)(scrubbed) if isinstance(value, tuple) else scrubbed
    return value


def scrub_secrets_processor(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog processor — scrubs secrets from every event_dict value.

    Mounted before the JSON renderer so redaction applies to anything bound via
    contextvars, kwargs, or the event message itself.
    """
    return {k: _scrub_value(v) for k, v in event_dict.items()}


# --- request-binding helpers ----------------------------------------------

# Header names that must NEVER reach structlog (raw or otherwise).
_SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie", "set-cookie"}


def safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of `headers` with sensitive values redacted.

    Used by the request middleware before binding header context. Belt-and-
    suspenders with the structlog scrubber — keeps raw secrets out of the
    contextvars store entirely.
    """
    return {
        k: (REDACTED if k.lower() in _SENSITIVE_HEADERS else v)
        for k, v in headers.items()
    }
