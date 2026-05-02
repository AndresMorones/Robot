# Submission Checklist

Single-page reviewer-facing reference and submission gate. Every FDE spec deliverable, every placeholder, every user-time task — all in one place.

Pairs with: `docs/FDE-TECHNICAL-CHALLENGE.md`, `README.md`, `docs/email-to-carlos.md`, `docs/broker-doc.md`, `docs/loom-shot-list.md`, `docs/iac/reproduce.md`.

---

## Spec deliverables (FDE § Deliverables, verbatim)

| # | Spec clause | Component / Path | Verification |
|---|---|---|---|
| 1 | "An email to your prospect client, Carlos Becker (c.becker@happyrobot.ai with your recruiter in cc) indicating your latest advancements" | `docs/email-to-carlos.md` | Placeholders filled (cc + repo + workflow + Loom) and message sent |
| 2 | "Write a document as if you were submitting the build description to a real freight broker (e.g., 'Acme Logistics')" | `docs/broker-doc.md` | No TODO markers; reviewed end-to-end |
| 3 | "Access to your deployed dashboard" | https://robot-dashboard-andres-morones.fly.dev | `curl -I` returns 200; loads in browser |
| 4 | "Link to your code repository" | [PLACEHOLDER — GitHub URL] | Public on GitHub; cloneable without invite |
| 5 | "Link to the workflow in the HappyRobot platform" | [PLACEHOLDER — HR Production share URL] | Opens for Carlos in HR UI on Production env |
| 6 | "A short video (5 mins) walking through: Use case setup / Short demo / Dashboard" | [PLACEHOLDER — Loom URL] | Plays without sign-in; runtime 4:30–5:15; all 3 sub-clauses covered |

---

## Placeholders to fill (4 total)

- [ ] **GitHub repo URL** → `README.md` (Live URLs + Deliverables table) and `docs/email-to-carlos.md` (Repo line)
- [ ] **HR Production share URL** → `README.md` (Live URLs) and `docs/email-to-carlos.md` (Workflow line). Source: HR UI → Workflow → Share → Production env
- [ ] **Loom video URL** → `README.md` (Live URLs) and `docs/email-to-carlos.md` (Video line). Record per `docs/loom-shot-list.md`
- [ ] **Recruiter cc email** → `docs/email-to-carlos.md` Cc header (replaces `[PLACEHOLDER — recruiter email]`)

---

## User-time critical path (in order)

Sequenced so each step unblocks the next.

1. Verify Fly API health (`curl /healthz` → 200)
2. Verify dashboard health (`curl -I` → 200; 4 tabs render in browser)
3. Smoke `/v1/dashboard/funnel` with bearer; confirm `FunnelMetrics` shape
4. Publish HR workflow to Production env (fork → publish → share)
5. Capture Production share URL → paste into 3 placeholders
6. Run a live web call end-to-end (FMCSA → loads → negotiation → transfer → Extract → Twin)
7. Spot-check `calls_log` + `bookings` in HR Twin SQL editor (most-recent row populated, CHS non-null, `apply_rate` populated)
8. Record Loom per `docs/loom-shot-list.md` (4:30–5:15)
9. Upload Loom; copy URL → paste into placeholders
10. Confirm GitHub repo is Public (Settings → General → Visibility); copy URL
11. Fill all 4 placeholders in `README.md` + `docs/email-to-carlos.md`
12. Re-read `email-to-carlos.md` for typos, salutation, cc
13. Re-read `broker-doc.md` for leftover TODO / `[PLACEHOLDER]` markers
14. Open deployed dashboard in a private window — no 401 surface
15. Send the email to `c.becker@happyrobot.ai` (cc recruiter)
16. (Post-submit) Rotate `HAPPYROBOT_API_KEY` at HR Settings → update Fly secret

---

## Pre-submission gate

All of these MUST be checked before sending the email. Each box maps to one or more critical-path steps above.

- [ ] All 4 placeholders filled (repo / workflow / Loom / recruiter cc)
- [ ] Both Fly apps respond 200 on `curl` (API + dashboard)
- [ ] HR Production-env publish complete and share URL works in private window
- [ ] Loom video uploaded; URL plays without sign-in; runtime in target window
- [ ] Email reviewed for typos and correct recruiter cc
- [ ] Broker doc reviewed for leftover TODOs
- [ ] Repo is public on GitHub; URL verified live in private window
- [ ] Live test call succeeded end-to-end (FMCSA → booking → Twin write → dashboard reflects)
- [ ] (Post-submit) `HAPPYROBOT_API_KEY` rotated at HR Settings

---

## Smoke commands (paste-ready)

Set `TOKEN=<API_BEARER_TOKEN>` first.

```bash
# Health (no auth)
curl https://robot-api-andres-morones.fly.dev/healthz
curl -I https://robot-dashboard-andres-morones.fly.dev/

# Dashboard endpoints (auth required)
H="Authorization: Bearer $TOKEN"
curl -H "$H" https://robot-api-andres-morones.fly.dev/v1/dashboard/funnel
curl -H "$H" https://robot-api-andres-morones.fly.dev/v1/dashboard/economics
curl -H "$H" https://robot-api-andres-morones.fly.dev/v1/dashboard/operational
curl -H "$H" https://robot-api-andres-morones.fly.dev/v1/dashboard/quality

# HR query_loads parity
curl -H "$H" "https://robot-api-andres-morones.fly.dev/v1/loads/search?origin_state=TX&max_results=3"

# Auth gate — should return 401
curl -i https://robot-api-andres-morones.fly.dev/v1/dashboard/funnel
```

---

## Spec compliance scorecard

Mirrors `README.md` § Spec compliance. Legend: `OK` = shipped + verified; `FILL` = placeholder pending.

| Objective | Spec clause | Status | Evidence |
|---|---|---|---|
| 1 | HappyRobot inbound agent | OK | `inbound-carrier-sales-new` (alias `inbound-carrier-v15`) |
| 1 | 13-field loads catalog | OK | `data/loads.csv` (150 rows) + Twin `loads` |
| 1 | FMCSA MC verification | OK | HR `verify_carrier` → FMCSA QCMobile |
| 1 | Search + pitch loads | OK | HR `query_loads` (Read-from-Twin) |
| 1 | Negotiate up to 3 rounds | OK | HR `negotiate_rate` → `calculate_rate.py` sidecar |
| 1 | Mock transfer to sales rep | OK | HR Transfer Popup |
| 1 | Extract relevant data | OK | HR AI Extract (JSON Schema strict) |
| 1 | Classify outcome + sentiment | OK | AI Extract outcome enum + CHS node sentiment |
| 2 | Custom dashboard (not HR analytics) | OK | Next.js 15 + FastAPI; 4 tabs |
| 3 | Docker | OK | `api/Dockerfile`, `dashboard/Dockerfile` |
| 3 | Cloud deploy | OK | Fly.io `iad`; `fly.toml` |
| 3 | HTTPS / Let's Encrypt | OK | Fly auto-issued; `force_https = true` |
| 3 | API key auth | OK | `app/deps.py::require_bearer` constant-time |
| 3 | Reproduce instructions | OK | `docs/iac/reproduce.md` |
| 3 | No phone number bought | OK | Web-call trigger only |
| Deliv. 1 | Email to Carlos w/ recruiter cc | FILL | `docs/email-to-carlos.md` |
| Deliv. 2 | Acme broker doc | OK | `docs/broker-doc.md` |
| Deliv. 3 | Deployed dashboard | OK | https://robot-dashboard-andres-morones.fly.dev |
| Deliv. 4 | Code repo link | FILL | GitHub URL placeholder |
| Deliv. 5 | HR workflow link | FILL | HR Production share URL |
| Deliv. 6 | 5-min Loom video | FILL | Loom URL; shot list at `docs/loom-shot-list.md` |

====
**Submission gate:** 4 placeholders + 9 gate boxes + 16-step user-time critical path + 8 paste-ready curl smokes.
**Spec coverage:** every clause from `docs/FDE-TECHNICAL-CHALLENGE.md` § Goals + § Deliverables + § Additional Considerations mapped to a component.
**Reviewer path:** open this doc → run smoke commands → check spec scorecard → done.
====
