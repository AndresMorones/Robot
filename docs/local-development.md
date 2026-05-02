# Local development

End-to-end loop on Windows for testing the full stack (FastAPI + Next.js dashboard + HR webhook receiver) before deploying to Fly.

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | already on system |
| `uv` | 0.11+ | `irm https://astral.sh/uv/install.ps1 \| iex` (PowerShell) |
| Node | 18+ | already on system |
| Git | any | already on system |

After installing `uv`, restart your terminal so `uv` is on PATH.

## One-time setup

### 1. Clone + cd
```powershell
git clone <repo-url> Robot
cd Robot
```

### 2. Configure secrets — FastAPI

Create `api/.env` (gitignored at `api/.gitignore:11`):

```ini
# Must match dashboard/.env.local API_BEARER_TOKEN (FE↔BE auth).
API_BEARER_TOKEN=local-dev-token-12345

HR_BASE_URL=https://platform.happyrobot.ai/api/v2
HAPPYROBOT_API_KEY=sk_live_<your-hr-key>          # see secrets.local.md
FMCSA_WEB_KEY=cdc33e44d693a3a58451898d4ec9df862c65b954

LOADS_CSV_PATH=../data/loads.csv
LOG_LEVEL=INFO
```

Reference: `api/.env.example` is the canonical template.

### 3. Configure secrets — Dashboard

Create `dashboard/.env.local` (gitignored):

```ini
API_BEARER_TOKEN=local-dev-token-12345
API_BASE_URL=http://localhost:8000
```

**Critical**: `API_BEARER_TOKEN` MUST match between `api/.env` and `dashboard/.env.local`. If they differ, every dashboard → FastAPI request returns `401 {"detail":"Missing or invalid API key (x-api-key or Authorization: Bearer)"}`.

### 4. Install deps

Two terminals (one per service):

```powershell
# Terminal A
cd Robot\api
uv sync

# Terminal B
cd Robot\dashboard
npm install
```

`uv sync` reads `api/pyproject.toml`, creates `api/.venv/`, installs FastAPI + uvicorn + cachetools + everything else.

## Daily run loop

### Terminal A — FastAPI

```powershell
cd Robot\api
uv run pytest -x                                  # green-light tests
uv run uvicorn app.main:app --reload --port 8000
```

You should see structlog JSON output and `Application startup complete`. Leave running.

Smoke test it:
```powershell
curl http://localhost:8000/healthz
curl -H "Authorization: Bearer local-dev-token-12345" http://localhost:8000/v1/dashboard/funnel
```

The first hits a public health endpoint (200). The second requires Bearer auth and returns funnel JSON from Twin.

### Terminal B — Next.js dashboard

```powershell
cd Robot\dashboard
npm run typecheck                                 # one-time sanity check
npm run dev
```

Open http://localhost:3000 → redirects to `/dashboard`. Server-rendered pages fetch from `http://localhost:8000` using the Bearer token.

## Testing the HR webhook receiver locally

The Option C push pipeline (ADR-009) needs HR's `call.ended` webhook to reach `POST /v1/events/call-ended`. Locally that's at `http://localhost:8000` — not reachable from HR's cloud.

Two options:

### Option 1 — Simulate the webhook with curl

```powershell
curl -X POST http://localhost:8000/v1/events/call-ended `
  -H "Authorization: Bearer local-dev-token-12345" `
  -H "Content-Type: application/json" `
  -d '{"call_id":"test-call-1","run_id":"test-run-1","time":"2026-04-28T12:00:00Z"}'
```

You should see `204 No Content`. The dashboard's `<LiveRefresh />` (if open) will receive the SSE event and call `router.refresh()`, fetching fresh data. Repeat with the same `call_id` within 5 minutes — second response is also 204 but cache invalidate is suppressed (idempotency).

### Option 2 — Tunnel localhost via cloudflared / ngrok

```powershell
cloudflared tunnel --url http://localhost:8000
# or:
ngrok http 8000
```

Take the public URL the tool prints (e.g., `https://random-string.trycloudflare.com`) and use it as the HR webhook URL in the workflow editor. HR can then hit your laptop's FastAPI directly. Tear the tunnel down when done.

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `401 Missing or invalid API key` on every dashboard load | `API_BEARER_TOKEN` mismatch between `api/.env` and `dashboard/.env.local` | Sync the two values |
| `program not found: uvicorn` after `uv run uvicorn` | Ran from wrong dir or missed `uv sync` | `cd api; uv sync; uv run uvicorn ...` |
| Dashboard renders zero data with no error | FastAPI not running on `:8000` | Start Terminal A first |
| 500 on dashboard pages, FastAPI logs show `httpx.ConnectError` to Twin | `HAPPYROBOT_API_KEY` invalid / expired | Check `secrets.local.md`, rotate key, restart Terminal A |
| `<LiveRefresh />` infinite reconnect loop in browser console | FastAPI not running, OR Bearer mismatch on `/v1/events/session` proxy | Restart Terminal A; check tokens match |
| Cloudflare 403 HTML returned from Twin queries | Cloudflare WAF triggered (`information_schema`, multi-col `COUNT(*)`, `ORDER BY`+`LIMIT`) | Simplify query; avoid those patterns |
| Webhook 401 even with Bearer set in HR | HR is sending the token but FastAPI doesn't have `API_BEARER_TOKEN` env var pointing at the same value | `fly secrets list -a robot-api-andres-morones` and reset to match |

## Running tests

```powershell
cd Robot\api
uv run pytest -x                                  # stop on first fail
uv run pytest -k events                           # only event-bus + SSE tests
uv run pytest -k security                         # only auth + scrub + transcript tests
uv run pytest --cov=app --cov-report=term-missing
```

Test coverage map:
- `test_auth.py` — Bearer auth happy/sad paths
- `test_security.py` — query-string rejection, log scrubbing, transcript opt-in (ADR-008)
- `test_events.py` — webhook receiver, SSE session swap, idempotency LRU (ADR-009)
- `test_dashboard_*.py` — funnel/economics/operational/quality endpoint shapes
- `test_dashboard_caching.py` — TTLCache behavior + invalidation (ADR-007)
- `test_loads.py` + `test_calls_endpoints.py` + `test_carriers_endpoints.py` — endpoint integration

## Production deployment

When local-test passes, deploy:

```powershell
cd Robot
fly deploy -a robot-api-andres-morones --config api/fly.toml
fly deploy -a robot-dashboard-andres-morones --config dashboard/fly.toml
```

Fly secrets (NOT in `api/.env`):
```powershell
fly secrets list -a robot-api-andres-morones
# API_BEARER_TOKEN, HAPPYROBOT_API_KEY must be present
```

If you've rotated the HR key, update Fly:
```powershell
fly secrets set HAPPYROBOT_API_KEY=sk_live_<new> -a robot-api-andres-morones
```

## Reference

- `secrets.local.md` (gitignored) — current secret values + rotation history
- `api/.env.example` — canonical local env template
- `dashboard/.env.example` — canonical dashboard env template
- ADR-007 (caching), ADR-008 (security), ADR-009 (push pipeline) — design rationale
- `docs/services-integration.md` — full service topology + auth chain
