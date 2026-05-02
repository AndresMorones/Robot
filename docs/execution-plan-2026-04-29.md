# Execution Plan — 2026-04-29

Comprehensive snapshot of where the project stands and what's left to ship. Captured after the dashboard v3 build (sales tab) + Option Y library cut + bug fixes landed today.

Pairs with: `docs/FDE-TECHNICAL-CHALLENGE.md` (the spec), `docs/submission-checklist.md` (gate), `docs/iac/reproduce.md` (deploy), and the master plan at `~/.claude/plans/now-i-want-you-fizzy-eagle.md`.

---

## A. Status snapshot

| Layer | State | Notes |
|---|---|---|
| HR voice agent | ✅ v15 in Development | 4 in-call tools + AI Extract + CHS post-call + Write-to-Twin |
| HR workflow envs | 🟡 Production publish pending | v15 dev-only |
| Twin: `loads` | ✅ 150 future-dated rows | seed v2 applied (verified 2026-04-29) |
| Twin: `calls_log` (15 cols) | ✅ schema verified | 12 base + 3 ALTER (intermediate_*) |
| Twin: `bookings` (6 cols) | ✅ schema verified | populates on `book_load` |
| FastAPI | ✅ 30 routes, WAF-safe | Bearer/x-api-key dual mode, 30s TTLCache |
| Next.js dashboard | ✅ 3 tabs working | Overview · Calls · New Bookings (Carriers replaced) |
| Tests | ✅ 96 passed, 7 skipped | Tier-2 fixture rewrite for endpoint integration tests |
| Docs | 🟡 substantial drafts exist | placeholders pending fill |
| GitHub | ⏳ never pushed | per-file decisions pending |
| Fly deploy | 🟡 may be stale | URLs in submission-checklist; HR API key rotated 5× since |

---

## B. Active path

### Phase 1 — Demo data collection (you, ~20 min)

Take 3 fresh calls in HR Development env to populate Twin with one of each outcome category. Use the dashboard date filter (Today / 1d) to surface only fresh data — no TRUNCATE needed.

**Call A — Happy path booking** (target: `call_outcome = load_booked`)
- MC: **250819** (confirmed-eligible; booked twice on 2026-04-28)
- Carrier opener: *"Hi, this is Mike with MC 250819, looking for a dry van out of Dallas to Atlanta."*
- Expected lane match: LOAD-0001 (Dallas → Atlanta, dry van, $1,575)
- Carrier counter: *"Best you can do is $1,700?"*
- Floor is `loadboard_rate × 0.90 = $1,418`; max_buy is `loadboard_rate × 1.10 = $1,732`
- Agent counters; agree somewhere between $1,575 and $1,700
- Carrier accepts: *"Deal."*
- Agent fires `book_load`; outcome = `load_booked`, bookings row written

**Call B — Negotiation stalled** (target: `call_outcome = carrier_declined_rate` or `no_match`)
- MC: **250819** (same eligible carrier)
- Carrier opener: *"Mike again, MC 250819. Got anything Phoenix to Denver, dry van?"*
- Expected lane match: LOAD-0011 (Phoenix → Denver, dry van, $1,650)
- Carrier pushes hard: *"Need at least $2,200 to make it work."*
- Agent counters; carrier insists $2,200 across 3 rounds
- Floor never goes below ~$1,485; carrier won't drop
- Carrier walks: *"Can't make it work, thanks."*
- No booking; outcome = `carrier_declined_rate` or `no_match`

**Call C — FMCSA decline** (target: `call_outcome = carrier_not_qualified`)
- MC: **859314** (confirmed-ineligible per Twin history; FMCSA returns not-authorized)
- Carrier opener: *"Hi, MC 859314, looking for any dry van out of Texas."*
- Agent fires `verify_carrier` → FMCSA AND-gate fails (e.g. `allowedToOperate = N` or revoked)
- Agent declines politely: *"Looks like FMCSA shows your authority isn't active right now — I can't dispatch this load. Reach out once you're back in good standing."*
- No booking; outcome = `carrier_not_qualified`, `fmcsa_eligibility_failure_reason` populated

#### Verify after each call (you, 2 min)
1. HR Twin SQL editor:
   ```sql
   SELECT call_id, mc_number, call_outcome, sentiment, case_health_score, fmcsa_eligibility_failure_reason FROM calls_log WHERE created_at > '2026-04-29'
   ```
   Should return 3 rows with the expected outcomes.
2. Dashboard at http://localhost:3000:
   - Set date filter to "Today" or "1d"
   - Overview tab: KPIs reflect the 3 new calls
   - Calls tab: 3 new rows; click each → drill-through with full transcript + telemetry
   - New Bookings tab: 1 sales-rep card from Call A
   - Sentiment + outcome distribution updated

---

### Phase 2 — Documentation review/update (Claude ~60 min, you review ~15 min)

Existing docs (most already substantial):

| File | State | Action |
|---|---|---|
| `README.md` | exists | refresh to reflect 30 routes + Option Y stack + 3 tabs |
| `docs/broker-doc.md` | substantial | refresh tool list (4 tools), post-call chain, Tier-2 roadmap |
| `docs/email-to-carlos.md` | drafted with placeholders | fill 4 placeholders (recruiter cc / GitHub URL / HR Production share / Loom URL) |
| `docs/loom-shot-list.md` | exists | review for current 3-tab dashboard |
| `docs/submission-checklist.md` | comprehensive | verify accurate; update spec scorecard if anything stale |
| `docs/activity-log.md` | running journal | append today's: bug fixes, library cut, sales view, pytest patches, loads probe |
| `docs/decisions/ADR-010` | **MISSING in numbering** | resolve gap or add new ADR-012 for dashboard v3 sales view |

---

### Phase 3 — GitHub push (Claude audit ~30 min, you push ~10 min)

#### 3.1 Pre-push audit (Claude)
- `.gitignore` verification: `secrets.local.md`, `api/.env`, `dashboard/.env.local`, `.mcp.json`, `node_modules/`, `.next/`, `__pycache__/`, `.venv/`, `data/calls_log_review_*.{json,ndjson}`
- `git check-ignore -v` for each
- Grep ALL committed files for `sk_live_`, `Bearer ` followed by hex, hardcoded tokens
- Per-file decisions per `project_github_push_content_decision_pending.md`:
  - `prompts/voice-agent-system-prompt-v4.md` (current) + v1/v2/v2-DRAFT/v3 — push as-is, redact, or local-only?
  - `prompts/ai-extract-schema.md` + `ai-extract-schema-v3.md` — push as-is recommended
  - `prompts/classify-outcome-realtime.md` + `classify-sentiment-realtime.md` — push as-is recommended
  - `docs/dashboard-v2-research/01-09.md` — push as-is or summarize
  - `docs/handoffs/2026-04-26-twin-search-architecture.md` — push as-is recommended
  - `docs/v3-prompt-audit/A-D.md` — push as-is or local-only
  - `scripts/snapshots/hr-iac-2026-04/*` — HR JSON snapshots; verify no secrets
  - `data/calls_log_review_*.{json,ndjson}` — likely PII; gitignore recommended
  - `data/calls_log.sql`, `data/twin_seed_loads*.sql`, `data/load-policies.json`, `data/fmcsa-fixtures/` — push as-is recommended

#### 3.2 Commit hygiene
Currently 32 commits. Options:
- (a) Push as-is — transparent dev history
- (b) Squash into 5-10 logical commits — cleaner narrative
- Recommendation: (a) unless you prefer otherwise

#### 3.3 Push (you)
```bash
gh repo create AndresMorones/Robot --public --source=. --remote=origin --push
```

#### 3.4 Verify
- README renders, ADRs visible, no `.env` files
- Test clone in private window
- Public per spec ("cloneable without invite")

---

### Phase 4 — HR v15 Production publish (you, ~10 min)

1. HR UI → workflow `inbound-carrier-sales-new` → Versions → v15 → Publish to Production
2. If webhook URLs differ between Dev and Prod envs, update HR `find_available_loads` / `search_loads_by_lane` / `book_load` to point at correct backend (local FastAPI or Fly URL)
3. Click Share → copy Production share URL
4. Save URL for email placeholder fill

---

### Phase 5 — Submission gates (deferred per user direction 2026-04-29)

| Gate | Status |
|---|---|
| Fly API + dashboard healthy | DEFERRED |
| Live test call against Fly | DEFERRED |
| Loom recording | DEFERRED |
| Email send to Carlos | DEFERRED |
| Post-submit: rotate `HAPPYROBOT_API_KEY` | DEFERRED until after submit |

---

## C. Loose ends (small details to verify)

**Code/state:**
1. `HR_WORKFLOW_ID` env var in `api/.env` — is it set? Active-calls indicator stays "Live status off" until set.
2. Fly secrets state — `HAPPYROBOT_API_KEY` has rotated 5× since last `fly secrets set`. Likely stale.
3. `book_load` tool name in HR — earlier audit saw v18 with `book_load_` (trailing space). Verify v15 clean.
4. Field rename verification — `apply_rate` (bookings) vs old `agreed_rate`; `original_rate` vs old `pitched_loadboard_rate`. Verify all code paths use new names.
5. Dashboard `dashboard/.env.local` — exists locally? Gitignored?
6. WAF compliance audit — every SQL in `app/services/*.py` should be single-statement, no LIMIT/ORDER+LIMIT/LEFT JOIN+IS NULL/multi-aggregate/IN-list.
7. `_LIST_COLS` in `api/app/routers/calls.py` doesn't include the 3 ALTER cols — should it?

**Doc loose ends:**
8. ADR-010 numbering gap — reserved? Skipped? Should ADR-012 be added for dashboard v3?
9. `docs/dashboard-design-philosophy.md` — verify reflects current state
10. v15-* doc set (architecture, two-table-schema, dashboard SQL queries, book_load spec, query_loads spec) — likely accurate but verify
11. `docs/agent-logic-tree.md` — flow diagram; verify still current
12. `docs/v3-prompt-audit/A-D.md` — open or resolved?

**HR-side:**
13. HR Northstars defined on Prompt? Per memory, enabled for Carrier Sales Auditor
14. Custom Evals built? Memory says deferred
15. Adversarial Suite built? Memory says deferred
16. Contact Intelligence enabled per memory — verify
17. Workflow variables current values: `negotiation_floor_pct`, `max_negotiation_rounds`, `company_name`, `agent_name`, `agent_version`
18. Real-time classifiers (Sentiment, Outcome) per memory — verify functioning
19. HR webhook URLs in v15 — point to local or Fly?

**GitHub-prep:**
20. `prompts/voice-agent-system-prompt-v4.md` — IP-sensitive? Push decision pending
21. `data/calls_log_review_2026-04-27.{json,ndjson}` — real call transcripts; PII risk
22. `scripts/snapshots/hr-iac-2026-04/` — HR JSON snapshots; check for secrets

---

## D. Deferred (user direction 2026-04-29)

- Fly deploy + secrets sync
- Carlos email send
- Loom recording
- Dashboard visual polish
- Tab-switching speed fix (asyncio.gather + Suspense — see `project_dashboard_polish_deferred.md`)
- 7 skipped dashboard endpoint test rewrites

---

## E. Tier-2 / post-MVP

**Architecture hardening** (`project_post_mvp_scalability_availability.md`):
- Fly multi-machine + multi-region
- Postgres migration off Twin
- Redis caching when multi-machine
- OpenTelemetry traces backend
- Prometheus metrics endpoint backend

**Security hardening** (`project_post_mvp_security_hardening.md`):
- Credential rotation runbook
- App rate limits + CSP
- Supply-chain (pin deps, audit)
- Fly platform hardening

**Dashboard expansion** (`project_dashboard_goliath_three_new_tabs.md`):
- Tab 4: Overall Agent Performance
- Tab 5: Agent Metrics (CloudWatch-Bedrock-style)
- Cross-filter on chart click
- Lane geographic heatmap
- Bookmarkable named views
- Dynamic multi-dim filtering

**Telemetry/transcript review** (`project_post_mvp_telemetry_transcript_dashboard.md`):
- Langfuse / Phoenix / Logfire
- Conversation-grain analytics
- Prompt iteration UI

**Self-improvement loops** (`project_post_mvp_*` series):
- Northstars iteration cycle
- Custom evals regression suite
- Negotiation policy auto-tune
- Sentiment-triggered intervention learning
- Per-carrier personalization via Twin Memories

**Field design research** (`project_post_mvp_field_design_research.md`):
- audit_remarks enum + "other" fallback
- fmcsa_eligibility_failure_reason canonical FMCSA enum
- pitched_loadboard_rate from Twin row, not Extract
- booking_decision rationalization

**HR workflow improvements** (`project_v15_e2e_first_pass_findings.md`):
- Clarification-loop fix
- Narrowing-question rule
- Recap-before-transfer enforcement
- Robotic negotiation phrasing polish

**HR architectural review** (`reference_hr_architectural_review_2026_04_28.md`):
- 11 findings; verify which still open
- p90/p70 wiring error
- 6 unmapped Twin columns
- Real-time classifier taxonomy mismatch

---

## F. Spec gates — mapped to state

(per `docs/submission-checklist.md` § Spec compliance)

| Spec clause | Status |
|---|---|
| HR inbound agent | ✅ shipped (v15) |
| 13-field loads catalog | ✅ shipped (Twin 150 rows) |
| FMCSA verify | ✅ shipped (verify_carrier → QCMobile) |
| Search + pitch | ✅ shipped (query_loads) |
| 3-round negotiation | ✅ shipped (Python sidecar) |
| Mock transfer | ✅ shipped (Transfer Popup) |
| AI Extract | ✅ shipped (strict JSON schema) |
| Classify outcome+sentiment | ✅ shipped |
| Custom dashboard | ✅ shipped (Next.js + FastAPI) |
| Docker | ✅ shipped |
| Cloud deploy | 🟡 stale Fly; needs verify or re-deploy |
| HTTPS | 🟡 conditional on Fly |
| API key auth | ✅ shipped |
| Reproduce instructions | ✅ shipped (`docs/iac/reproduce.md`) |
| No phone bought | ✅ shipped |
| Email Carlos | ⏳ drafted, deferred send |
| Acme broker doc | 🟡 drafted, refresh |
| Deployed dashboard URL | 🟡 stale Fly |
| Code repo URL | ⏳ pending push |
| HR workflow link | ⏳ pending Prod publish |
| 5-min Loom | ⏳ deferred |

---

## G. Risks

1. **Stale Fly deploy** — submission-checklist references Fly URLs but `HAPPYROBOT_API_KEY` rotated 5× since last `fly secrets set`. Reviewer hitting Fly will get 401 from Twin. Fix is one `fly secrets set` + redeploy when un-deferred.
2. **GitHub IP-sensitivity** — voice-agent-system-prompt versions, HR IaC snapshots may contain HR's IP. Per-file decision required.
3. **Loom against local vs Fly** — recording against localhost can't claim cloud-deployed; against Fly requires verify.
4. **HR Production webhook URLs** — if env-specific, must update on publish.
5. **HR API key in chat history** — current key `sk_live_azT-...` shared in chat. Rotation post-submit is the safety net.
6. **Tab-speed in Loom** — sequential Twin queries cause noticeable lag. ~10 min `asyncio.gather` fix to un-defer if jarring.

---

## H. Reference index

**Master plan**: `~/.claude/plans/now-i-want-you-fizzy-eagle.md`

**Spec**: `docs/FDE-TECHNICAL-CHALLENGE.md`

**Submission gate**: `docs/submission-checklist.md`

**Reproduce**: `docs/iac/reproduce.md`

**Architecture**:
- `docs/hr-architecture-map.md`
- `docs/services-integration.md`
- `docs/local-development.md`
- `docs/v15-architecture-2026-04-27.md`
- `docs/v15-two-table-schema.md`

**ADRs** (in `docs/decisions/`): 001-009 + 011 (010 missing)

**HR references**: `docs/references/happyrobot/*.md`

**FMCSA references**: `docs/references/fmcsa/decline-reasons.md`

**Prompts**: `prompts/*.md` (voice-agent v1-v4, ai-extract, classify-*)

**Memory** (50+ files):
- `project_dashboard_v3_sales_rep_locked.md` (current sales tab spec)
- `project_dashboard_polish_deferred.md` (incl. tab-speed)
- `project_github_push_content_decision_pending.md`
- `feedback_creative_card_design.md`
- `reference_cloudflare_waf_limit_blocks.md`
- `project_dashboard_endpoint_tests_tier2.md`
- `project_loads_dummy_data_refresh.md` (resolved 2026-04-29)
