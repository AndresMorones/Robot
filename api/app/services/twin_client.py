"""HR Twin REST API client.

Verified endpoints (2026-04-25 / 2026-04-27):
  GET  https://platform.happyrobot.ai/api/v2/twin/tables/{tableName}
  POST https://platform.happyrobot.ai/api/v2/twin/tables/{tableName}/rows
       body: {"values": {<col>: <stringified value>, ...}}
  POST https://platform.happyrobot.ai/api/v2/twin/sql
       body: {"sql": "<single-statement SQL>"}
       returns: {"rows": [...], "count": N} on SELECT; {"ok": true} on DDL.

Auth: Bearer HAPPYROBOT_API_KEY. The org-level key authenticates writes + reads.

Twin SQL constraint (per ADR-004):
  Twin does NOT honor `:placeholder`, `$1`, or `?` parameter binding. Cloudflare
  WAF intermittently 403s bodies with quoted SQL literals. For the dashboard
  read path we tolerate this because:
    1. All SQL is server-authored (no carrier/HR input flows into the SQL).
    2. The `params` kwarg accepts only simple typed values (str/int/float/bool/None)
       which we quote-escape ourselves before splicing — defense-in-depth in case
       a future caller does pass user input.
  IN-lists and JSONB ops are avoided here because the WAF rejects some patterns
  (per Cloudflare WAF guidance in the deliverable spec).

Failures degrade gracefully — sync reads return [] and inserts return None so
the dashboard renders a zero-state instead of crashing. The async `query` path
raises HTTPException(502) on Twin errors so dashboard endpoints can map cleanly.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx
import structlog
from fastapi import HTTPException

from app.config import settings

log = structlog.get_logger()


def _stringify_value(v: Any) -> Any:
    """HR Twin's POST /rows expects string-typed values; server coerces to typed columns."""
    if v is None:
        return None
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (dict, list)):
        import json as _json
        return _json.dumps(v)
    return str(v)


def _format_datetime_for_waf(dt: datetime) -> str:
    """Render a datetime in a form Cloudflare WAF tolerates.

    The WAF in front of Twin trips on `'YYYY-MM-DDTHH:MM:SS+00:00'` shapes
    (the `+00:00` offset substring matches a rule). Drop the offset and
    use a space separator — PostgreSQL parses both shapes identically when
    the column is `timestamptz` and the literal is treated as UTC.
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _sql_literal(v: Any) -> str:
    """Render a Python value as a SQL literal, with strict whitelist of types.

    Used to splice `params` into SQL because Twin lacks parameter binding.
    Any value outside the whitelist raises ValueError.
    """
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, datetime):
        return f"'{_format_datetime_for_waf(v)}'"
    if isinstance(v, date):
        return f"'{v.isoformat()}'"
    if isinstance(v, str):
        # Strings that look like ISO timestamps with a UTC offset get the
        # same WAF-safe rewrite. Other strings pass through with quote escape.
        if "T" in v and ("+00:00" in v or v.endswith("Z")):
            try:
                parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return f"'{_format_datetime_for_waf(parsed)}'"
            except ValueError:
                pass
        # Postgres single-quote escape: '' inside a literal.
        escaped = v.replace("'", "''")
        return f"'{escaped}'"
    raise ValueError(f"Unsupported SQL parameter type: {type(v).__name__}")


def _interpolate(sql: str, params: dict[str, Any] | None) -> str:
    """Splice :name placeholders with quoted SQL literals.

    Caller is trusted (server-authored SQL); `params` values are still escaped
    to keep this safe against a future bug or refactor that surfaces user input.
    """
    if not params:
        return sql
    out = sql
    for k, v in params.items():
        if not k.isidentifier():
            raise ValueError(f"Invalid SQL param name: {k!r}")
        out = out.replace(f":{k}", _sql_literal(v))
    return out


class TwinClient:
    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=settings.hr_base_url,
            headers={
                "Authorization": f"Bearer {settings.happyrobot_api_key}",
                "Accept": "application/json",
            },
            timeout=10.0,
        )
        self._async: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------ sync
    def get_rows(self, table_name: str, *, limit: int | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        try:
            resp = self._client.get(f"/twin/tables/{table_name}", params=params)
            resp.raise_for_status()
            return resp.json().get("rows", [])
        except httpx.HTTPError as e:
            log.error("twin.fetch_failed", table=table_name, error=str(e))
            return []

    def insert_row(self, table_name: str, values: dict[str, Any]) -> dict | None:
        normalized = {k: _stringify_value(v) for k, v in values.items() if v is not None}
        try:
            resp = self._client.post(
                f"/twin/tables/{table_name}/rows",
                json={"values": normalized},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            log.error(
                "twin.insert_failed",
                table=table_name,
                error=str(e),
                response=getattr(e, "response", None) and e.response.text[:500],
            )
            return None

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ async
    def _aclient(self) -> httpx.AsyncClient:
        if self._async is None:
            self._async = httpx.AsyncClient(
                base_url=settings.hr_base_url,
                headers={
                    "Authorization": f"Bearer {settings.happyrobot_api_key}",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
        return self._async

    async def query(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read-only SQL statement against Twin and return rows.

        `params` substitutes `:name` placeholders with quoted SQL literals.
        Only str/int/float/bool/None values are supported — other types raise
        ValueError before the request leaves the process.

        Raises HTTPException(502) on Twin transport failures.
        Raises HTTPException(400) on Twin-reported SQL errors.
        Raises HTTPException(401) if Twin rejects the org-level Bearer.
        """
        body_sql = _interpolate(sql, params)
        try:
            resp = await self._aclient().post("/twin/sql", json={"sql": body_sql})
        except httpx.HTTPError as e:
            log.error("twin.sql_transport_failed", error=str(e))
            raise HTTPException(status_code=502, detail="Twin upstream unavailable") from e

        if resp.status_code == 401:
            log.error("twin.sql_unauthorized")
            raise HTTPException(status_code=401, detail="Twin auth rejected (HAPPYROBOT_API_KEY)")
        if resp.status_code >= 400:
            preview = resp.text[:500]
            log.error("twin.sql_error", status=resp.status_code, body=preview)
            raise HTTPException(
                status_code=400 if resp.status_code < 500 else 502,
                detail=f"Twin SQL error ({resp.status_code}): {preview}",
            )

        try:
            data = resp.json()
        except ValueError as e:
            log.error("twin.sql_bad_json", error=str(e))
            raise HTTPException(status_code=502, detail="Twin returned non-JSON") from e

        rows = data.get("rows") if isinstance(data, dict) else None
        return rows or []

    async def aclose(self) -> None:
        if self._async is not None:
            await self._async.aclose()
            self._async = None


twin_client = TwinClient()
