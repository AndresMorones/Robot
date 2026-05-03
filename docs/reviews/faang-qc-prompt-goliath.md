# FAANG-Level Quality Control — Goliath Review Prompt

**Purpose.** Single, copy-pasteable prompt to launch a multi-agent FAANG-bar quality review of the Robot take-home. Designed to (a) catch AI-collapse slop, (b) enforce architectural conformance against FDE spec + CLAUDE.md + ADRs + locked memory, (c) produce a concise top-section + deep-dive appendix usable in one pass.

**Differs from `faang-qc-prompt.md`** — that one is a dashboard-polish sign-off checklist (scoped to `dashboard/src/**` + dashboard-touched API). This one is a whole-repo goliath review with parallel sub-agents, run before sending the Carlos email.

**When to run.** Before sending the Carlos email. Re-run after any non-trivial architectural change.

**How to run.** Paste the entire `==== PROMPT START ====` … `==== PROMPT END ====` block into a fresh Claude Code session at the repo root. Read-only — no edits will be made. Output lands at `docs/reviews/faang-qc-<YYYY-MM-DD>.md`.

---

==== PROMPT START ====

You are the lead reviewer for a FAANG-bar quality control pass on the Robot repo (HappyRobot inbound carrier voice agent take-home). This is a **read-only review** — do not edit code, do not run mutations, do not commit. Your only deliverables are the artifacts described in section 7.

## 1. Mission

Produce a review that a Staff+ engineer at Google / Meta / Stripe would sign off on as "ready to ship to a prospective employer." Two failure modes are equally fatal:

1. **AI-collapse slop** — dead code, redundant abstractions, filler comments, hallucinated APIs, over-engineered defenses, half-finished refactors, copy-paste drift, two ways to do the same thing. If a senior reviewer would say "this looks like an LLM wrote it without thinking," flag it.
2. **Architectural drift** — code that contradicts the FDE spec, an ADR, CLAUDE.md, a locked memory decision, or the live HR workflow architecture. Flag every drift with a citation to the source-of-truth it violates.

You are reviewing a take-home submission. The bar is "this person knows what they're doing and ships clean work," NOT "this is production at scale." Don't suggest infra hardening that's already deferred to Tier-2. Don't suggest features that are explicitly out of scope per locked memory. Use judgment.

## 2. Sources of Truth (in priority order)

When deciding "is this correct / intentional / on-spec," consult these in order. Every finding MUST cite one of them OR cite a contradicting `file:line` in the repo itself.

1. **FDE spec** — `docs/FDE-TECHNICAL-CHALLENGE.md` (the bible — every product requirement traces here)
2. **Project conventions** — `CLAUDE.md` at repo root
3. **Architectural Decision Records** — `docs/decisions/ADR-*.md` (especially ADR-005 Twin Write, ADR-007 caching, ADR-011 dashboard library cuts, ADR-012 latency compute, ADR-013 operational vs analytical store)
4. **Locked memory decisions** — `C:\Users\Andre\.claude\projects\c--Users-Andre-OneDrive-Documentos-GitHub-Robot\memory\MEMORY.md` index → individual `.md` files. Treat as load-bearing for any "why did they do it this way" question.
5. **HR workflow architecture map** — `docs/hr-architecture-map.md` and `docs/references/happyrobot/`. The HR workflow itself lives in the HR UI (not in repo) but its contract with our API is documented here. You DO need to know HR architecture to evaluate whether our API correctly mirrors what the workflow expects.
6. **Activity log** — `docs/activity-log.md` for "is this in-progress vs done."

If a finding can't cite one of (1)–(6) or a concrete `file:line`, it is unverifiable — drop it or downgrade to a Nit.

## 3. Scope

**In scope (review everything):**
- `api/app/**` — FastAPI service, routers, services, models, deps
- `dashboard/**` — Next.js 15 App Router dashboard
- `data/**` — JSON seeds, SQL DDL, fixtures
- `docs/**` — spec, ADRs, activity log, HR references, reviews
- `scripts/**` — deploy scripts, helpers
- `tests/**` and `api/tests/**` — coverage gaps ARE in scope
- Repo-root config — `pyproject.toml`, `Dockerfile`, `fly.toml`, `.github/workflows/**`, `.mcp.json`, `package.json`, `tsconfig.json`, `next.config.*`, `tailwind.config.*`
- Cross-references between HR workflow contract (per `docs/hr-architecture-map.md`) and our API surface — flag mismatches

**Out of scope:**
- Nothing. The HR workflow internals are configured in the HR UI, but the *contract* between HR and our API is in repo and IS in scope.

## 4. Severity Bar

Every finding gets one of:

- **Blocker** — broken, insecure, spec-violating, would embarrass at interview. Must fix before sending Carlos email.
- **High** — readability / maintainability / consistency issue a FAANG reviewer would call out in a code review. Should fix.
- **Medium** — minor smell, small inconsistency, weak naming. Fix if cheap.
- **Low** — preference / style. Skip unless trivial.
- **Nit** — typo, whitespace, alphabetization. Group together; don't burn report space on these individually.

The user's instruction: prioritize Blockers, but don't omit the High-bar readability findings — that's where FAANG quality lives.

## 5. Anti-AI-Collapse Hunt List (apply to every file)

Actively hunt for ALL of:

- **(a) Dead code** — unused imports, unreachable branches, commented-out blocks, orphaned functions, unused parameters, vars assigned but never read
- **(b) Premature abstraction** — single-use helpers, "just-in-case" config knobs, factories with one product, interfaces with one implementer, wrappers that add nothing
- **(c) Filler / slop comments** — comments that restate the code (`# increment counter` above `counter += 1`), references to the task that produced the code (`# fix for issue #123`, `# added in WS2a`), stale TODOs, planning-doc artifacts in source files
- **(d) Hallucinated / wrong APIs** — calls to functions that don't exist, wrong signatures, wrong import paths, type annotations that don't match runtime behavior, fake "fixes" that wouldn't compile or run
- **(e) Over-engineering** — try/except for impossible cases, defensive shims for internal callers, backwards-compat for code never shipped, validation duplicated across layers, error wrappers that lose information
- **(f) Inconsistency** — two ways to do the same thing, copy-paste drift between similar files, half-finished refactors (some callers updated, others not), naming drift (snake_case vs camelCase mixed, `mc_number` vs `mc` vs `mcNumber`)
- **(g) Magic / hardcoding** — magic numbers without a name, hardcoded text that should be a constant, hardcoded paths, secrets / tokens / URLs in source
- **(h) UI/UX leakage** (dashboard) — internal field names visible to users (`snake_case` in labels), raw JSON in tooltips, untranslated enum values, error states that show stack traces

For each, give a concrete `file:line` and a one-sentence rationale.

## 6. Goliath Sub-Agent Split

You are the parent agent. Spawn **5 sub-agents in parallel** (single message, multiple Agent tool calls), each with a dedicated lens. Use `subagent_type=Explore` for read-only review work. Each sub-agent returns a focused finding list; you merge, dedupe, and rank.

**Sub-agent 1 — Spec & Architecture Conformance**
- Read FDE spec end-to-end. For every requirement clause, locate the implementing code and verify it conforms.
- Cross-check every ADR against current code. Flag drift.
- Cross-check HR workflow contract (`docs/hr-architecture-map.md`) against API surface (`api/app/routers/**`). Flag mismatches in payload shape, auth, endpoint paths, response keys.
- Output: list of `[Severity] [file:line] finding — cites: FDE §X / ADR-N / map line`.

**Sub-agent 2 — API Code Quality (Python / FastAPI)**
- Walk `api/app/**`. Apply the full anti-AI-collapse hunt list (5a–5h).
- Check: router thinness, service purity, model boundaries, structlog discipline (no `print` / stdlib `logging`), bearer auth on every `/v1/*` route, contextvar binding, OTel span correctness.
- Check: pyproject.toml for unused deps, Dockerfile for layer cache hygiene, fly.toml for healthcheck correctness.
- Output: same format.

**Sub-agent 3 — Dashboard Code Quality (Next.js / TS / Tailwind)**
- Walk `dashboard/**`. Apply 5a–5h with extra weight on (h) UI/UX leakage.
- Check: `server-only` import guards on bearer-token paths, `useSearchParams` URL-state correctness, Recharts usage, shadcn primitive usage (NO Tremor / nuqs / react-day-picker / date-fns / Calendar / Popover per ADR-011), accessibility (alt text, aria-labels, keyboard nav, color contrast).
- Check: every user-visible label translates internal field names per memory `feedback_no_internal_field_names_in_ui`.
- Check: caching strategy matches ADR-007 (revalidate=30 + TTLCache(30s)).
- Output: same format.

**Sub-agent 4 — Security & Secrets**
- Hunt: hardcoded tokens, FMCSA web key in source, `API_BEARER_TOKEN` leakage to client bundle, `console.log` of sensitive data, SQL injection surface (Twin queries are parameterized?), CORS config, CSP, rate limiting absence (note as deferred per locked memory, not a blocker), input validation at boundaries, error messages that leak internals.
- Cross-check `.env*` files are gitignored and not committed.
- Output: same format.

**Sub-agent 5 — Tests, Docs, Infra**
- Coverage gaps: which routers / services have NO test? Which critical paths (auth, search filters, error handling) are untested?
- Doc rot: any ADR contradicted by current code? Any activity-log claim that doesn't match repo state? Any `docs/references/happyrobot/` claim that contradicts `docs/hr-architecture-map.md`?
- Infra: `Dockerfile`, `fly.toml`, `.github/workflows/**`, deploy scripts (per memory `reference_fly_deploy_scripts_2026_05_01` — bare `flyctl deploy` from root is a footgun; verify scripts are the only path).
- Output: same format.

After all 5 return, you (parent) **dedupe** (multiple agents may flag the same issue), **rank** by severity, and **trace** every Blocker/High back to its source-of-truth citation.

## 7. Output Format

Write to `docs/reviews/faang-qc-<YYYY-MM-DD>.md`. Two clearly separated sections:

### Section A — Executive (top of file, ultra-concise)

Skim-readable in under 2 minutes. No prose paragraphs. Pure structure:

```
# FAANG QC — <date>

## Verdict
<One line: ship-ready / ship after Blockers / not ready, with count of Blocker / High / Medium>

## Blockers (must-fix before Carlos email)
- [B1] file:line — short finding — cites: <source>
- [B2] ...

## Top-10 Fix List (ranked: Blockers first, then High by impact/effort ratio)
1. file:line — keyword-style: "Remove dead /v1/calls/log handler — ADR-005 says 410 Gone"
2. ...

## High-Bar Readability Findings (key points only)
- file:line — keyword finding
- file:line — keyword finding
...

## ADR Drafts Needed
- ADR-NNN: <title> — drift found: <one line>
- ADR-NNN: <title> — drift found: <one line>

## Nits (grouped, no detail)
- Typos: file:line, file:line, ...
- Whitespace / formatting: file:line, ...
```

### Section B — Per-File Deep Dive (appendix, navigated on demand)

For every file with at least one finding above Nit, an appendix entry the user can jump to:

```
### `path/to/file.ext`

**Findings:**
- [Severity] line N — finding
  - **Cites:** FDE §X / ADR-N / CLAUDE.md "Conventions" / contradicting `other_file:line`
  - **Why it matters:** one sentence
  - **Suggested fix:** one sentence (no code unless trivially short)

- [Severity] line M — ...
```

Order appendix entries by severity-weighted finding count (worst files first). Use markdown anchor links from Section A's Top-10 to the relevant appendix entry.

### Section C — ADR Drafts

For each architectural drift that warrants a permanent decision record, write a stub ADR (just title + context + decision + consequences, ~10 lines each) at the bottom of the report. The user will copy these into `docs/decisions/` if they accept.

## 8. Discipline Rules

- **Cite or drop.** Every finding above Nit has a citation. No "I think this could be cleaner" without a source.
- **No hedging.** "Consider possibly maybe refactoring" is banned. Either it's a finding or it isn't.
- **No restating known limits.** The user knows JSON-as-store is intentional (CLAUDE.md "What NOT to do" → "Don't add a database"). Don't flag it. Same for `data/loads.csv` content (locked deferred), Tier-2 infra (locked deferred), test scenarios for HR workflow (out of scope — it's UI-configured).
- **Read-only.** No Edit, no Write to source files, no git mutations, no `flyctl` calls. Only Write to `docs/reviews/faang-qc-<date>.md`.
- **Verify before claiming.** If you say "function X is dead," grep for X across the repo (including dashboard, scripts, tests) before flagging. False-positive dead-code claims destroy report credibility.
- **Match the user's bar.** This is a take-home for a Forward Deployed Engineer role. The reviewer (Carlos) wants to see judgment, taste, and ship-discipline — not a 500-finding lint dump. If your report is over 50 findings, you're including noise. Cut to signal.
- **Memory awareness.** Locked memories override default conventions. Examples: `project_dashboard_v2_locked_option_b` (no Tremor), `project_keep_all_languages` (do NOT narrow to English), `reference_calls_log_transcript_shape` (transcript is JSON role/content, no per-turn timestamps), `project_telemetry_widgets_locked` (RPM/TPM/latency p50–p99). Read MEMORY.md index first; pull individual memory files when a finding might conflict.

## 9. Stop Conditions

You're done when:
1. All 5 sub-agents have returned.
2. Findings are deduped, ranked, cited.
3. `docs/reviews/faang-qc-<date>.md` is written with Section A + B + C populated.
4. You've posted a single summary message to the user: "Verdict: <X>. <N> Blockers, <M> High, <K> Medium. Top-3 fixes: <one line each>. Full report at <path>." Nothing more.

Do not loop, do not re-review, do not start fixing. The user reviews the report and decides what to action.

==== PROMPT END ====

---

## Operator Notes (not part of the prompt)

- **Run mode.** Paste into a fresh Claude Code session at repo root. Auto-accept can stay on (read-only by construction), but watch for the parent agent attempting writes outside `docs/reviews/`.
- **Expected runtime.** 5 parallel sub-agents over a repo this size: ~10–20 min wall-clock.
- **Re-run trigger.** After any architectural change, before any external submission, or when a new ADR lands.
- **Failure mode to watch for.** Sub-agents inventing findings without citations. The parent's dedupe pass should drop any uncited finding above Nit.
- **Relationship to `faang-qc-prompt.md`.** That file is the dashboard-polish sign-off gate (narrow, deep on dashboard spec). This file is the whole-repo goliath (broad, multi-agent, anti-collapse focus). Run both before submission — they catch different things.
