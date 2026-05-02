# Security Model — 3 secrets, 3 boundaries

How authentication works across the system. Reference for anyone deploying or auditing.

## The 3 secrets

The system uses **three independent secrets**, each protecting a different boundary. Don't merge them.

| # | Secret | Stored where | Read by | Authenticates |
|---|---|---|---|---|
| 1 | `HAPPYROBOT_API_KEY` (`sk_live_...`) | Fly secret on API app + local `api/.env` | FastAPI server-side only | YOUR FastAPI → HR Twin |
| 2 | `API_BEARER_TOKEN` (random hex) | Fly secret on BOTH API app + dashboard app + local `api/.env` + `dashboard/.env.local` | FastAPI (validates incoming) + dashboard (sends outbound) | Dashboard server → YOUR FastAPI |
| 3 | `LINK_SIGNING_SECRET` (random hex) | Fly secret on dashboard app + local `dashboard/.env.local` | Dashboard middleware (`src/middleware.ts`) + `scripts/generate_signed_link.py` | Email recipient → YOUR dashboard |

## Auth flow

```
[Email recipient (Carlos)]
   │
   │ clicks signed URL: https://dash.fly.dev/?t=<exp>.<sig>
   ▼
[Dashboard middleware (Edge runtime)]
   │
   │ HMAC-validates token using LINK_SIGNING_SECRET → sets `dash_auth` cookie → redirects to clean URL
   ▼
[Dashboard server-side renderer]
   │
   │ fetches data with `Authorization: Bearer <API_BEARER_TOKEN>`
   ▼
[FastAPI on Fly]
   │
   │ validates Bearer in `app/deps.py::require_bearer` (constant-time HMAC compare)
   │ runs Twin queries with `Authorization: Bearer <HAPPYROBOT_API_KEY>`
   ▼
[HR Twin REST gateway]
   │
   │ validates HR key, returns rows
   ▼
[Twin Postgres]
```

## Why three keys, not one or two

If you reused **`HAPPYROBOT_API_KEY` as the Bearer** (proposed shortcut, NEVER do this):
- The dashboard env would have the HR org key
- Anyone leaking the dashboard env could call `platform.happyrobot.ai/api/v2/twin/sql` directly
- Blast radius: read/write on your entire HR org's data

If you skipped **`LINK_SIGNING_SECRET` and exposed the dashboard URL openly**:
- Anyone discovering the URL sees production data
- No expiry — link works forever
- No revocation — only way to lock out is to take dashboard down or rotate Bearer

Three independent keys → three independent blast radii. If one leaks, the other two still protect.

## What a leak of each key allows

| Leak | Attacker can | Mitigation |
|---|---|---|
| `LINK_SIGNING_SECRET` leaks | Mint signed links to your dashboard for any TTL | Rotate via `fly secrets set LINK_SIGNING_SECRET=...` — invalidates all prior links |
| `API_BEARER_TOKEN` leaks | Curl `/v1/*` directly, read all dashboard data | Rotate on both API + dashboard apps simultaneously |
| `HAPPYROBOT_API_KEY` leaks | Read/write your entire HR org's Twin data + all workflows | Rotate at HR Settings → API Keys; update Fly secret + local `.env` |

## What "secrets out of sync" means

The same secret name (e.g., `API_BEARER_TOKEN`) lives in MULTIPLE places. They MUST hold the same value:

- Fly secret on API app
- Fly secret on dashboard app
- Local `api/.env`
- Local `dashboard/.env.local`

If any of these holds a different value than the others, requests get **401**.

**How to detect a mismatch**: curl `/v1/dashboard/funnel` with the local Bearer; if 401, local ≠ Fly.

**How to fix**: rotate to a fresh value, push to BOTH Fly apps + update BOTH local `.env` files in one pass. Sequence in `docs/iac/reproduce.md` Section 5.

## Why deployment happens from your local laptop

The `fly` CLI is a local tool. It talks to Fly's control plane (api.fly.io) over authenticated HTTPS. From your perspective:

| Operation | Runs locally | Effect on Fly |
|---|---|---|
| Generate a secret in PowerShell | Random string in process memory | None until next step |
| `fly secrets set NAME=value --app X` | CLI sends HTTPS POST to api.fly.io | Fly stores it encrypted; restarts machines |
| `fly apps create NAME` | CLI sends HTTPS POST | Fly creates app metadata |
| `fly deploy` | Builds Docker image locally → uploads to Fly registry → triggers deploy | Fly pulls image, starts machines |
| `fly logs` | CLI streams machine logs over WebSocket | None — read-only |

The Fly machine doesn't initiate any of this. Secrets are pushed FROM your laptop TO Fly, never the reverse.

**Implication**: secret values created via PowerShell exist briefly on your laptop in memory, get pushed to Fly via TLS, then live encrypted on Fly's side. The secret value never traverses email, never enters source control, never appears in logs.

## What the email recipient does

The email contains:
- Signed dashboard URL (`https://...fly.dev/?t=<exp>.<sig>`)
- HR workflow IDs (for placing test calls)
- HR web-call URL (for testing the agent live)
- GitHub repo URL (optional — for reviewers who want to inspect code or redeploy)

What the recipient does NOT need:
- Any secret value
- Any environment configuration
- Any local setup

They just click the URL. The middleware validates the embedded HMAC + sets a session cookie + renders the dashboard.

For reviewers who want to redeploy themselves: `docs/iac/reproduce.md` walks them through getting their own HR org + setting up their own secrets + deploying their own apps.

## Rotation policies

| Secret | Routine rotation | Why |
|---|---|---|
| `HAPPYROBOT_API_KEY` | After submission ends | Avoid lingering access by reviewers |
| `API_BEARER_TOKEN` | After submission ends | Same |
| `LINK_SIGNING_SECRET` | After eval period | All previously-issued links die instantly |

Procedure for each: `fly secrets set NAME=$(openssl rand -hex 32) --app <app>` then update local `.env`.

## Spec compliance citation

FDE Spec Sec.1 ("Security"): *"If you're creating an API, add basic security features such as: HTTPS … API key authentication for all endpoints."*

| Requirement | How satisfied |
|---|---|
| HTTPS | Fly auto-issues Let's Encrypt; `force_https = true` in fly.toml |
| API key auth on all endpoints | Every `/v1/*` route declares `Depends(require_bearer)` in `api/app/deps.py`. Constant-time HMAC compare. Header-only (no query-string fallback per ADR-008). |

Beyond strict spec: signed-link middleware adds a second auth layer in front of the dashboard UI itself, which is not technically required by spec but raises the production-readiness bar.

## Pairs with

- `docs/decisions/ADR-008-api-security-hardening.md` — header-only auth, no query-string fallback
- `docs/iac/reproduce.md` Section 5 + 5.x — deployment with all 3 secrets
- `dashboard/src/middleware.ts` — the implementation
- `scripts/generate_signed_link.py` — link generator
