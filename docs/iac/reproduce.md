# SPEC-005 — Reproduce the Deployment

This document lets a reviewer with no prior context spin up their own copy of the Robot inbound-carrier voice agent. It satisfies **FDE Spec Sec.2.b** (reviewers must be able to access **and** reproduce the deployment).

The system has three pieces:

1. **HappyRobot workflow** (voice agent + tools + post-call chain) — proprietary platform, configured in the HR UI.
2. **FastAPI backend** (`api/`) — reads HR Twin, exposes `/v1/dashboard/*`. Deployed to Fly.io.
3. **Next.js dashboard** (`dashboard/`) — server-renders HTML from the FastAPI. Deployed to Fly.io.

---

## 1. Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.12+ | API runtime |
| [`uv`](https://github.com/astral-sh/uv) | latest | Python package manager (replaces pip/poetry) |
| Node.js | 20+ | Dashboard build/runtime |
| [`flyctl`](https://fly.io/docs/flyctl/) | latest | Fly.io deploy CLI |
| HappyRobot account | org-level | Workflow + Twin access |
| FMCSA web key | provided in spec | `cdc33e44...` (provided as part of the take-home) |

Fly.io requires a credit card to create apps even on the hobby tier.

---

## 2. Repository clone + structure

```bash
git clone https://github.com/AndresMorones/Robot.git
cd Robot
```

See `README.md` "Repo structure" section for the directory map. Key paths referenced below:

- `api/` — FastAPI backend
- `dashboard/` — Next.js 15 dashboard
- `data/twin_schema_*.sql` — Twin DDL
- `docs/iac/ui-build-guide.md` — HR UI rebuild recipe

---

## 3. HappyRobot workflow setup

The voice-agent workflow lives entirely inside HappyRobot — a proprietary platform — and is **not** in this repo as code. To inspect or run it you need either:

- **HR org access** (request from Andres or HR support), or
- the **video walkthrough** at `docs/loom-link.md`.

### 3.1 Active workflow

`inbound-carrier-sales-new`, version 17 (`v15` semantic build). Components:

- **Voice Agent** node + Prompt v4.3
- **4 tools**: `verify_carrier` (FMCSA webhook), `query_loads` (Read-from-Twin), `negotiate_rate` (Run Python sidecar), `book_load` (Write-to-Twin, mid-call)
- **Post-call chain**: AI Extract → Case Health Score (Run Python) → Update Data in Record (writes `calls_log`)

### 3.2 Twin schema (3 tables)

Open the HR Twin SQL editor (HR sidebar → Twin → SQL) and paste each of these files **one statement at a time** (HR's editor is single-statement):

1. `data/twin_schema_loads.sql` — loads catalog
2. `data/twin_seed_loads_v2.sql` — seed rows for the loads table
3. `data/twin_schema_calls_log.sql` — one row per call (post-call write)
4. `data/twin_schema_v15_bookings.sql` — one row per booking (mid-call write, `UNIQUE(call_id, load_id)` for idempotency)

### 3.3 Rebuilding the workflow from scratch

If you don't have access to import the existing version, follow `docs/iac/ui-build-guide.md` — a phase-by-phase HR UI build recipe. **Do not** try to script the build via the HR API: POSTing nodes onto a forked workflow corrupts the voice runtime (see ADR on "HR POST batch corruption"). UI-only is the supported path.

---

## 4. Backend (FastAPI) — local + Fly deploy

```bash
cd api
uv sync                                      # install deps from uv.lock
cp .env.example .env                         # local dev only

# Edit .env — set:
#   API_BEARER_TOKEN=<long random hex>
#   HAPPYROBOT_API_KEY=sk_live_...
#   FMCSA_WEB_KEY=cdc33e44...

# Local smoke test
uv run pytest -x
uv run uvicorn app.main:app --reload         # http://localhost:8000
```

### Fly deploy (one-time)

```bash
fly auth login
# Pick a globally-unique app name; substitute it everywhere below.
fly apps create robot-api-<your-handle> --org personal

fly secrets set \
  API_BEARER_TOKEN=$(openssl rand -hex 32) \
  HAPPYROBOT_API_KEY=sk_live_... \
  FMCSA_WEB_KEY=cdc33e44... \
  --app robot-api-<your-handle>

# Deploy must run from REPO ROOT (not api/) because Dockerfile context = repo root.
fly deploy --config fly.toml --app robot-api-<your-handle>
fly logs --app robot-api-<your-handle>       # tail
```

### Verification

```bash
curl https://robot-api-<your-handle>.fly.dev/healthz
# expects: {"status":"ok"}

TOKEN=<your API_BEARER_TOKEN>
curl -H "Authorization: Bearer $TOKEN" \
  https://robot-api-<your-handle>.fly.dev/v1/dashboard/funnel
# expects JSON with funnel KPIs
```

---

## 5. Frontend (Next.js dashboard) — local + Fly deploy

```bash
cd dashboard
npm install
cp .env.example .env.local

# Edit .env.local — set:
#   API_BEARER_TOKEN=<same as backend>
#   API_BASE_URL=https://robot-api-<your-handle>.fly.dev
#   LINK_SIGNING_SECRET=<leave blank for local dev to disable middleware>

npm run typecheck
npm run dev                                  # http://localhost:3000
```

> **Local dev note**: when `LINK_SIGNING_SECRET` is blank, the dashboard's
> `src/middleware.ts` fails open (dev convenience). Production deploys MUST
> set it as a Fly secret — see Section 5.x below.

### Fly deploy (one-time)

```bash
fly apps create robot-dashboard-<your-handle> --org personal

# 32-byte hex secret for the signed-link middleware (see Section 5.x)
LINK_SECRET=$(openssl rand -hex 32)

fly secrets set \
  API_BEARER_TOKEN=<same-token-as-API> \
  API_BASE_URL=https://robot-api-<your-handle>.fly.dev \
  LINK_SIGNING_SECRET=$LINK_SECRET \
  --app robot-dashboard-<your-handle>

fly deploy --app robot-dashboard-<your-handle>
```

### Verification

```bash
# Without a signed link → middleware returns 401
curl -I https://robot-dashboard-<your-handle>.fly.dev/
# expects: 401 (signed-link auth required)

# Generate a 14-day signed link + open it in a browser
LINK_SIGNING_SECRET=$LINK_SECRET python scripts/generate_signed_link.py \
  --days 14 \
  --base https://robot-dashboard-<your-handle>.fly.dev
```

Open the printed URL in a browser. The middleware:
1. Validates the HMAC signature on `?t=<exp>.<sig>`
2. Sets an `httpOnly` cookie with the token
3. Redirects to the clean URL (no token in browser history beyond first click)
4. Renders the funnel / economics / operational / quality tabs against your live FastAPI

Subsequent navigation uses the cookie. Cookie expires when the link expires (14 days by default).

### 5.x — Signed-link auth model (production)

The dashboard's `src/middleware.ts` runs on the Edge runtime and validates every
request against an HMAC-SHA256 signature. There are TWO valid auth paths:

| Path | When |
|---|---|
| `?t=<exp>.<sig>` query param | First visit from email link |
| `dash_auth` cookie | Subsequent visits within the link's TTL |

Tampered tokens, expired tokens, missing tokens → 401.

**Generating links to share** (e.g., to send a reviewer):

```bash
export LINK_SIGNING_SECRET=<the-secret-you-set-on-fly>
python scripts/generate_signed_link.py --days 14 --base https://robot-dashboard-<your-handle>.fly.dev
```

The script prints one URL. Send only that URL — never share `LINK_SIGNING_SECRET`.

**Rotating after eval period**: change the Fly secret + redeploy. All previously-issued
links die instantly because their HMAC signatures no longer validate.

```bash
fly secrets set LINK_SIGNING_SECRET=$(openssl rand -hex 32) --app robot-dashboard-<your-handle>
```

**Threat model** (be honest about what this protects):
- ✅ Random internet scanners cannot reach the dashboard (no signed link → 401)
- ✅ Auto-expires after the link TTL (no need to manually take dashboard down)
- ⚠️ If the email gets forwarded during the TTL window, anyone with the link gets in.
      For higher security (login + per-user audit), swap to NextAuth.js or Cloudflare Access.

---

## 6. HR workflow → backend connection

Important: in the v15 architecture, **HR does not webhook into our FastAPI**. Tools are wired internally to HR services:

| Tool | Backing service | Our API involved? |
|---|---|---|
| `verify_carrier` | HR demo FMCSA endpoint (`mobile.fmcsa.dot.gov`) | No |
| `query_loads` | HR Read-from-Twin | No |
| `negotiate_rate` | HR Run Python sidecar | No |
| `book_load` | HR Write-to-Twin (mid-call) | No |
| Post-call AI Extract → CHS → Update Data in Record | HR-internal | No |

The dashboard reads from FastAPI; FastAPI reads from HR Twin via REST gateway. We removed `POST /v1/calls/log` per ADR-005 — there are no inbound HR webhooks to configure.

---

## 7. End-to-end verification

1. Open the HR web-call URL (in `docs/references/happyrobot/web-call-url.txt`).
2. Speak: *"MC 250819, looking for a load Dallas to Atlanta tomorrow, dry van."*
3. Agent should: `verify_carrier` → `query_loads` → pitch → negotiate (up to 3 rounds) → `book_load` → recap → transfer.
4. Open `https://robot-dashboard-<your-handle>.fly.dev/dashboard`.
5. Refresh — your call should appear with sentiment, CHS, and outcome populated.

---

## 8. Common issues

- **Cloudflare WAF on Twin SQL queries** — certain patterns (info_schema lookups, multi-column COUNT aggregates) are blocked. Workaround: split into multiple statements; prefer plain `SELECT *`.
- **HR API key rejection (`401`)** — must be an `sk_live_...` **org-level** key, not personal. Rotate at HR Settings → API Keys.
- **Bearer-token mismatch** — `API_BEARER_TOKEN` must be identical across the API Fly secret, the dashboard Fly secret, and any local `.env`/`.env.local`. The dashboard stores it server-side only via a `server-only` import.
- **Voice agent says "transfer was successful" without handing off** — Prompt v4.3 was not pasted into the Voice Agent node. Re-do Phase A1 Edit 2 in the UI build guide.
- **Fly deploy fails on `data/loads.csv` COPY** — you ran `fly deploy` from `api/` instead of repo root. The Dockerfile's build context is repo root.

---

## 9. Tear-down

```bash
fly apps destroy robot-api-<your-handle> --yes
fly apps destroy robot-dashboard-<your-handle> --yes
```

For Twin tables, run in HR Twin SQL editor (only if you own the org):

```sql
TRUNCATE bookings;       DROP TABLE bookings;
TRUNCATE calls_log;      DROP TABLE calls_log;
TRUNCATE loads;          DROP TABLE loads;
```

Revoke the HR API key at HR Settings → API Keys.

---

**Spec citation**: this document is the artifact for FDE Spec **Sec.2.b** ("reviewer must be able to reproduce the deployment").
