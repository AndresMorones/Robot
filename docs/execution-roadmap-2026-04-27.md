# Execution Roadmap — Synthesized 2026-04-27

Output of 3-agent review panel: inventory (Agent A) + dashboard v2 design (Agent B) + dependency-ordered roadmap (Agent C). Synthesized into one intermediate-scope plan honoring the user direction "ambitious but not full enterprise; postpone the heavier ones."

## Framing

- Horizon: ship the take-home to Carlos in ~5-7 days
- Total work: ~16-18 hours
- Every item from the 50+ memory files has a phase home; nothing omitted
- Default decisions made — user can override

## SPEC ANCHOR

Bible: `docs/FDE-TECHNICAL-CHALLENGE.md`. Every decision below cites a clause. Re-audit done 2026-04-27 after user direction "this is your north star always remember this as the bible."

## 5 default decisions (RE-AUDITED against spec)

1. ~~negotiate_evaluate → stay Tier-2~~ **OVERRIDDEN. Moves to Phase 5.8d critical path.** Spec clause: *"Handle up to 3 back and forth's negotiating the offer."* Test 3 failed because agent said "I don't have the ability to negotiate rates directly" — that's a spec compliance failure, not a Tier-2 deferral choice.
2. Dashboard polish → **FULL enterprise scope** (~20 Claude-hr; user time ~30 min review). Reasoning: Claude time is effectively free; only user time is the constraint. See `feedback_user_time_vs_claude_time_scope.md`. Includes a metric-discovery prerequisite phase (5.85) to lock the canonical metric catalog before pixel-pushing.
3. Submission tone → consultancy broker doc + engineer-builder README/email
4. Test re-run → 7 fresh calls (5 original + 2 new)
5. finalize_call → stay Tier-2

## NEW Phase 5.85 — Metric-discovery + analysis (~2-3 Claude-hr, ZERO user time)

Per `feedback_analytical_foundation_before_dashboard.md` — analyze BEFORE building.

Outputs:
1. **Canonical metric catalog** — every metric with: friendly name, business question, target audience, formula, schema source, empty-state, alert threshold
2. **Coverage matrix** — audience × surface (KPI tile / panel / drilldown / alert)
3. **Schema gap report** — computable today vs needs new column vs needs new instrumentation
4. **Anti-list** — metrics deliberately NOT tracked + why
5. **Audience personas** — ops manager / sales lead / exec / engineer

Saved to `docs/dashboard-metric-catalog.md`. Becomes source of truth for Phase 5.9 build.

## Phase 5.9 prerequisites (added 2026-04-27)

**Null-resilience requirement (must hold across ALL dashboard endpoints + UI)**: every metric calculation, aggregate, and chart MUST handle null values without breaking. Per user direction 2026-04-27: "a null value should not break it fix this logic in dashboard". Examples:
- AVG / SUM aggregations: skip null rows, don't NaN
- Booking rate: numerator counts non-null bookings; denominator excludes nulls cleanly
- Sentiment / outcome distributions: null/empty values bucket as "unknown" (visible in chart) OR filtered explicitly with caption
- KPI tiles: render "—" or "Pending" when underlying data is null, never "$NaN" or "NaN%"

**Multi-load aware metrics (booked vs not-booked at booking-grain, not call-grain)**: per user direction 2026-04-27, dashboards count BOOKINGS not just calls. A call where carrier booked 2 of 5 pitched loads = 2 bookings (success), not "partial". Booked-vs-not should be counted per booking (load-grain), not per call (call-grain).

## Phase 5.9 (REVISED) — Full enterprise dashboard build (~20 Claude-hr)

Per Agent B's full spec (NOT the intermediate cut). Restored because user clarified: "do dashboard in detail as it doesn't cost me time only you and I do not care about that."

7 incremental shippable steps:
1. Visual foundation refresh (palette, typography, spacing, redacted labels, drop "why matters") — 3 hr
2. Filter bar v2 (preset pills + calendar popover + chip multiselects + active-filter tray + URL state) — 4 hr
3. Executive KPI row + sparklines + prior-window deltas — 3 hr
4. System Health redesign (stoplight + sparklines + click-to-scroll, drop noisy alert) — 2 hr
5. Replace histogram with scatter + Economics empty-state UX — 3 hr
6. Chart interactivity (click-to-filter on donut/funnel/sentiment/FMCSA/carrier) — 3 hr
7. Drilldown panel polish (tabbed) + Recent Calls table refinement — 2 hr

Each step leaves dashboard fully functional + deployed. User time per step = ~5 min review.

## Phase 5.8d — Voice prompt + HR chip rebinds + negotiate_evaluate sidecar + seed (~5-7 hr USER, spec-anchored)

Items in dependency order:
1. Fork v13 → v14 (UI clone)
2. Smoke-test v14 voice
3. BUG-005 §0 Time.Now block
4. BUG-002 §6 MC readback
5. BUG-001 §7 FMCSA STOP RULE
6. BUG-004 §3 origin-from-utterance
7. BUG-003 §13 injection deflection example
8. BUG-006 silence threshold bump
9. BUG-007 carrier_name chip → legalName
10. SCH-009 / M-015 pitched_loadboard_rate from Twin row (DEMO-BLOCKING per metric catalog — Listed Rate / Discount % unusable until this binds)
11. SCH-004 fmcsa_eligibility_failure_reason enum lock
12. BUG-009 Classify Outcome override on FMCSA failure
13. **VA-006 negotiate_evaluate Python sidecar** (PROMOTED per spec — *"Handle up to 3 back and forth's negotiating the offer"*)
14. Prompt §9 rewrite to invoke negotiate_evaluate tool
15. SCH-015 loads.json relative dates
16. Publish v14 → smoke test

DEFERRED (not blocking v14 publish): refresh `data/loads.csv` to 100-500 future-dated rows. Current 25 rows are mostly past-dated by demo day. Trigger before Phase 6 test calls OR Phase 7 demo polish. See memory `project_loads_dummy_data_refresh.md`.

DEFERRED (apply during Phase 6 pre-flight OR Phase 7 polish): full Twin `calls_log` data re-audit. After v14 produces 5-10 real test calls covering all scenarios, run a per-column scorecard checking population, shape, source-of-truth, cardinality, coverage gaps, and drift. Output: `docs/twin-data-audit-YYYY-MM-DD.md`. Memory `project_twin_data_reaudit.md` has the runbook. Pairs with the field-rename runbook.

DEFERRED (apply during Phase 5.9 OR Phase 7): field-name renames cascade. AI Extract was updated 2026-04-27 to emit `original_rate` (was `pitched_loadboard_rate`) + `apply_rate` (was `agreed_rate`). Twin `calls_log` column renames + FastAPI/dashboard code grep-replaces are queued. Full runbook in memory `project_field_renames_pending.md`. NOT critical-path for v14 publish — chip bindings still work with the name mismatch; ugly but functional.

DEFERRED (Tier-2 polish, watch in smoke test): `finalize_call` tool to fix agent-stays-waiting-after-transfer. Current MVP relies on prompt §9's explicit "Stop speaking" instruction after the spec literal transfer message. If smoke testing v14 reveals the agent doesn't end the call cleanly, options in order of effort: (a) tighten prompt §9 to be more aggressive about silence + add a hard "End your turn here" instruction; (b) bind the call.ended event to fire when the agent says the literal transfer phrase; (c) add `finalize_call` Run Python tool with End-call-after-execution flag set. See memory `project_call_end_tool_pattern.md`. Recommend starting with (a) — zero new nodes — and only escalate if it fails on real calls.

Exit: clean MC capture + FMCSA decline working + carrier_name showing legalName + Listed Rate populated + negotiate_evaluate completes 3 rounds correctly.

## Phase 5.9 — Dashboard build (REVISED — full enterprise scope)

Replaced the "intermediate cut" with full Agent B spec. See "Phase 5.9 (REVISED)" in the decisions section above. ~20 Claude-hr, ~30 min user review across 7 deploy checkpoints. Phase 5.85 metric-discovery runs first.

## Phase 6 — Test re-run (~1-2 hr USER + sub-agent)

7 fresh test calls + sub-agent transcript review. Test 3 negotiation stays failed by design.

## Phase 7 — Submission deliverables (~5-7 hr)

1. SPEC-005 reproduce-deployment doc
2. SPEC-007 architecture doc
3. SPEC-008 data-model doc
4. SPEC-002 broker build doc (consultancy tone, Tier-2 as roadmap)
5. SPEC-001 README pass
6. SPEC-003 video script + 5-min Loom
7. SPEC-004 submission email
8. SPEC-006 submission checklist
9. CLAUDE.md drift cleanup
10. DASH-012 memory file p70/p90 purge

## Phase 8 — Post-MVP voice agent depth (Tier-2, post-submission)

VA-006 negotiate_evaluate → VA-007 Calculate Carrier Cost → VA-009 finalize_call → SCH-007 audit_remarks enum + sub-agent goliath → SCH-001 calls_log v2 schema → SCH-013/014 carriers + offers tables → SCH-016 improvement_signal → VA-001/002/004/011 consolidated prompt rewrite → VA-005 10 lane-search tests → VA-008 Module Change → VA-012/013 Auditor + Computations → VA-014 Carrier Intelligence → VA-015 classifier A/B → SCH-017 format-contracts.md → INF-016 DB CHECK constraints

## Phase 9 — Infrastructure + scale (Tier-2/Tier-3)

INF-001/002 rotation runbooks → INF-003/009/010/011/012 security hardening → INF-013/014/015 CI/CD → INF-004/005 multi-machine + multi-region → INF-006/007/008 Postgres + Alembic + Tigris → DASH-015/016 OTel + Prometheus → DASH-006/007/008/009/013/014 dashboard polish tabs → DASH-010 Next.js migration → DASH-011 Langfuse/Phoenix → INF-017 IaC rebuild → INF-018 Bridge API → INF-019 Twin search Option 4 → Tier-3 R&D loops

## Drift cleanup (Phase 7)

| Item | Fix |
|---|---|
| CLAUDE.md "Stack" v4 | → v13 |
| CLAUDE.md "Frontend Next.js" | → "MVP HTML; Tier-2 Next.js" |
| CLAUDE.md "OTel + Prom" | → "planned, not active" |
| project_call_end_tool_pattern.md vs reference_hr_workflow_schema_population.md | reconcile finalize_call as Tier-2 |
| project_phase3_calls_log_v2.md p90_latency_ms | mark null/post-MVP |
| project_dashboard_enterprise_framing.md "why matters" | align with DASH-003 |
| README mermaid negotiate_evaluate | annotate Tier-2 |
| Master plan §3 + §4 | annotate "strategic, superseded" |

## Item home check (no orphans)

| Category | Items | Phase home |
|---|---|---|
| 1 Spec | SPEC-001..008 | Phase 7 |
| 2A HR-UI bugs | BUG-001..009 | Phase 5.8d |
| 2B Code bugs | BUG-010 | Phase 5.8a (done) |
| 3 Schema | SCH-001..019 | SCH-004/009/015/018 in 5.8d; rest Phase 8 |
| 4 Voice agent | VA-001..018 | VA-018 in 5.8d; rest Phase 8 |
| 5 Dashboard | DASH-001..016 | DASH-001/002/003 in 5.9; DASH-012 in 7; rest 9 |
| 6 Infra/sec | INF-001..023 | All Phase 9 |

## First 3 actions

1. Fork v13 → v14 in HR UI (5 min)
2. Patch v14 prompt (45 min) — paste-ready in `docs/test-review-findings-2026-04-27.md`
3. Re-bind 4 chips in v14 Write-to-Twin (30 min)

Then Claude takes Phase 5.9 dashboard cut.

## Pairs with

- **`docs/FDE-TECHNICAL-CHALLENGE.md` — THE BIBLE** (every decision anchored here)
- `docs/test-review-findings-2026-04-27.md` (paste-ready prompt edits + 8-issue scorecard)
- `docs/dashboard-metric-catalog.md` (29 metrics, 4 personas, build manifest mapped to Phase 5.9 steps 1-7)
- `data/calls_log_review_2026-04-27.json` (test snapshot)
- `data/calls_log_review_2026-04-27.ndjson` (pretty-printed for review)
- Memory `feedback_spec_is_the_bible.md`
- Memory `feedback_user_time_vs_claude_time_scope.md`
- Memory `feedback_analytical_foundation_before_dashboard.md`
- Memory `project_dashboard_v2_design_directives.md`
- Memory `project_post_mvp_remove_latency_metrics.md`
- Master plan `~/.claude/plans/now-i-want-you-fizzy-eagle.md` (strategic, partly superseded)

## 5 dashboard design questions — LOCKED at recommended values (user confirmed 2026-04-27)

1. **KPI strip composition** ✅ `Calls Today / Booking Rate / Revenue Booked / Avg Call Quality Score`
2. **Quality Score label** ✅ `Call Quality Score`
3. **Carrier row click semantics** ✅ filter dashboard to that MC
4. **Listed Rate empty UX** ✅ gray-with-caption "Pending data pipeline"
5. **Calendar UX** ✅ side-by-side `<input type="date">`

## Negotiation architecture revision (2026-04-27)

Per user direction "python was just for show... most of the negotiation strategy should be set in the prompt" → architecture flipped:

- **Master prompt = brain** (round counter, counter math, floor protection, persona, walk-away, all scenarios)
- **Python sidecar = capability showcase only** — small demo of "active value injection" (recommended: time-of-day floor adjustment)

Spec clause *"Handle up to 3 back and forth's negotiating the offer"* satisfied by prompt rules, not Python state machine.

Phase 5.8d adjusted:
- ~~negotiate_evaluate Python sidecar (~3 hr)~~
- ✅ Master prompt rewrite (~2 hr) + small Python demo capability (~30 min) = ~2.5 hr total

See memory `project_negotiation_prompt_driven_python_for_show.md`.

## What changes if user disagrees with defaults

- If negotiate_evaluate pulled in: +6-10 hr to critical path; Phase 5.8d ends, new Phase 5.8e wedged in
- If full dashboard polish: +5-7 hr; Phase 5.9 expands
- If Tier-2 of voice work pulled in: Phase 8 collapses partially into 5.8d; demo timeline slips ~3-5 days
- If submission tone uniform: simpler narrative, less audience signal
