# Activity Log

Running dev journal for the HappyRobot inbound-carrier take-home. Concise, chronological, scannable. New day = new `## YYYY-MM-DD` heading. Entries are appended newest-at-the-bottom within a day.

---

## 2026-05-01 — Wrong-image dashboard deploy regression + guardrail

**Incident.** Second occurrence: running `flyctl deploy --remote-only --app robot-dashboard-andres-morones` from the repo root cwd applied the root `fly.toml` (API config) and shipped the API image to the dashboard app. Symptom: `https://robot-dashboard-andres-morones.fly.dev/` returned 404, while `/dashboard` served the legacy server-rendered HTML from `api/app/routers/dashboard_view.py` (Tailwind CDN tag), not Next.js. Both Fly machines healthy — wrong image, right healthcheck.

**Fix.** Re-ran `flyctl deploy --remote-only --app robot-dashboard-andres-morones` from `dashboard/` cwd. Verified Next.js back online via `/api/health` returning `{"status":"ok","service":"robot-dashboard"}`. The signed-link middleware now (correctly) gates `/` with 401 — that is itself proof Next.js is serving (the legacy HTML had no middleware).

**Guardrail.** Added four wrapper scripts (bash + ps1 each for dashboard and API): `scripts/deploy-dashboard.{sh,ps1}` and `scripts/deploy-api.{sh,ps1}`. Each script: self-cd's based on its own location, asserts `fly.toml` contains the expected `app = "..."` line, runs `flyctl deploy --remote-only`, and post-deploy curls the healthcheck and asserts the response contains the right `"service":"..."` fingerprint. Added a `service` field to API `/healthz` (`api/app/routers/health.py`) so its image fingerprint is unambiguous, mirroring the dashboard's `/api/health`. Updated `api/tests/test_health.py` for the new shape. README `Deploy (Fly.io)` section rewritten to point at the scripts and warn against direct `flyctl deploy` from repo root.

---

## 2026-04-29 — Dashboard library minimization (Option Y)

**Dashboard library minimization (Option Y)** — cut nuqs, @tremor/react, react-day-picker, date-fns, @radix-ui/react-popover after visual A/B mockup at `dashboard/library-cut-comparison.html` confirmed cuts are visually justified. ~62 KB gz bundle savings; date-range picker now uses two native `<input type="date">` elements; Tremor BadgeDelta + SparkAreaChart replaced by custom span + bare Recharts. Captured in [ADR-011](decisions/ADR-011-dashboard-library-minimization.md).

---

## 2026-04-26 — v6 of Inbound Carrier Sales New works; baseline locked

After multi-hour debug, identified that **API PUT mutations on Voice Agent / Prompt nodes leave invisible runtime corruption that propagates through forks**. Saved learning to [memory/reference_hr_fork_corruption.md](../../.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/reference_hr_fork_corruption.md).

**Working baseline:** Inbound Carrier Sales New v6 (id `019dc8ae-a0e9-7946-83fc-a47d9be3e70c`, slug `676hu4keo9oz`)
- Forked via API directly from v2 (clean, never API-mutated)
- 9 nodes: Web call, Inbound Voice Agent, Prompt, verify_carrier, GET MC Number, find_available_loads, GET load (Read-from-Twin), search_loads_by_lane, [Fetch Loads]
- Voice answers, FMCSA verify works, load search works
- Published to development, missing_variables: 0

**Other versions on this workflow:**
- v1, v2: original UI-built, work
- v3: orphan group_id (`c1e69591-...mc_number`) on Initiate New Contact — broken
- v4: API-corrupted by Claude's earlier mutations — broken
- v5: forked from v4 — broken (inherited corruption, NO config-overwrite recovered it)
- v6: clean fork from v2 — works

**For next session — Carrier Sales workflow completion plan:**

User wants v6 to have parity with v5's intended setup BUT excluding Auditor + Computations. Components to add to v6 (in order, parents first):

1. `negotiate_evaluate` (tool, parent=Prompt) + `Calculate Carrier Cost` (Run Python child)
2. `Initiate New Contact` (action, Create Popup, parent=Inbound Voice Agent — fix orphan group_id at creation, hard-code `phone_number = "MC-pending"`)
3. `Classify` (Outcome — action, parent=Initiate New Contact)
4. `Extract` (action, parent=Classify) — paste schema from `prompts/ai-extract-schema.md`, MVP shape (14 fields, callback_phone Tier-2)
5. `Case Health Score` (action, parent=Extract — skip Computations)
6. `Classify Sentiment` (action, parent=Case Health Score — skip Auditor)
7. `Write to Twin` (action, parent=Classify Sentiment) — calls_log, 20 columns mapped per [scripts/add_write_twin_node.py](../../scripts/add_write_twin_node.py)

**Approach for next session:**
- Pull each node's config from v3 (configs are clean even though v3's runtime is corrupted)
- POST `/versions/{V6}/nodes` for each — that operation has been corruption-safe in our testing
- Skip Auditor + Computations entirely per user direction
- After all additions, force-publish to dev, user tests one happy-path call
- Capture resulting v6 node configs as IaC snapshots for ADR-002 reproduction

**Twin state ready:** loads table (15 cols + 25 seed rows + 2 indexes), calls_log table (23 cols + 3 indexes). All DDL in `data/twin_schema_*.sql`. Workflow vars exist on the workflow (5 incl. API_BEARER_TOKEN_).

**Memory files relevant for next session:**
- [reference_hr_fork_corruption.md](../../.claude/.../memory/reference_hr_fork_corruption.md) — DON'T API-mutate published Voice Agent / Prompt nodes
- [reference_hr_model_registry.md](../../.claude/.../memory/reference_hr_model_registry.md) — model.static.id is `turbo` (Inbound Carrier) or `turbo-one` (other workflows), NOT `gpt-4.1`
- [reference_hr_procedural_quirks.md](../../.claude/.../memory/reference_hr_procedural_quirks.md) — full API endpoint contracts, Plate JSON shape, etc.

---

## 2026-04-25 — Phase 6+7+9 completed via API; IaC contracts unlocked

Wired Write Twin (replacement for POST Call Data webhook), deleted the deprecated webhook, and published v4 to Development — all via REST after the user authorized autonomous API exploration.

**Landed today:**
- Write Twin node (`019dc6e1-b5a4-7c2d-a992-8562aeab34cc`), child of Classify Sentiment, 20 columns bound to calls_log. Created via [scripts/add_write_twin_node.py](../scripts/add_write_twin_node.py) (reproducible IaC artifact).
- POST Call Data deleted via `DELETE /versions/{id}/nodes/{id}` — Phase 7 done.
- calls_log schema hardened — 23 cols + 3 indexes (idx_created_at DESC, idx_mc_number, idx_call_outcome) + 5 analytics-richness columns (sentiment_start, sentiment_trajectory, final_offer_position, posted_price_increase, p90_latency_ms).
- loads schema hardened — 2 indexes (lane+equipment composite, pickup_datetime).
- v4 published to Development environment — `is_published: true, is_live: true`.

**Open warning from publish response:** `Initiate New Contact` node has unresolved variable reference `c1e69591-7877-4b09-b911-7f82d83c76de.mc_number` (group_id from a deleted node, likely forked-from-v3 leftover). Workflow published anyway; this branch may misbehave at runtime if hit. Fix in Phase 11 iteration after first test call surfaces what actually breaks.

**IaC contracts unlocked** (saved to memory + [iac-bundle.md](references/happyrobot/iac-bundle.md) "Future branch work"):
- `POST /versions/{id}/nodes` body: `{"nodes": [<node>]}` array-wrapped; uses `parent_node_id` not `parent_id`.
- Plate Paragraph[] variable reference shape (text bookends not optional).
- Write Twin `columnValues` items: `{columnName, type, isPrimary, value}`.
- HR action chains are LINEAR (new child auto-pushes existing child down).
- `POST /twin/sql` accepts arbitrary DDL; Cloudflare blocks `information_schema` queries — use `GET /twin/schema`.
- Endpoint corrections: `/runs` not `/runs/trigger`; `/available-vars` not `/available_variables`.
- 404'd: workflow-level webhooks CRUD, bulk row insert.

**Roadmap commitment:** full IaC rebuild script deferred to dedicated branch. Detailed design in [ADR-002 — IaC rebuild from zero](decisions/ADR-002-iac-rebuild-from-zero.md): hybrid manifest+snapshot toolchain at `scripts/iac/`, 9-step bootstrap orchestrator, idempotency strategy, smoke test fixture, CI integration, ~11-15 hr estimated effort. iac-bundle.md "Future branch work" section now points to the ADR.

**Next concrete action:** Phase 10 — first test web-call. Then `SELECT * FROM calls_log ORDER BY id DESC LIMIT 1` to verify Twin write.

## 2026-04-23

### 14:00 — Plan approved; kickoff files in place

**What I did**: Finalized the master plan at `C:\Users\Andre\.claude\plans\now-i-want-you-fizzy-eagle.md` as a strategic overview (not a frozen spec) — removed the pre-baked detailed Sections 6/7/8/11/12/13 that over-committed the project. Exited plan mode. Proceeding with minimum file kickoff plus background WS4 research on the HappyRobot platform.

**Files touched (created)**
- `CLAUDE.md` — project conventions in flexible-preference descriptive voice (~60 lines); pointers to plan, activity log, decision records, and HR reference directory.
- `docs/activity-log.md` — this file.
- `docs/decisions/ADR-001-python-formatter.md` — locked ruff-alone for formatting + linting (see ADR).

**Decisions made**
- ADR-001: ruff-alone for Python formatting + linting. One tool, Black-compatible, much faster. See `docs/decisions/ADR-001-python-formatter.md`.
- Confirmed Option B/C ordering (files + background research in parallel) from the pre-kickoff close.
- Activity log is first-person voice; commits keep `Co-Authored-By: Claude` attribution visible.

**Background work spawned**
- WS4 research agent — HappyRobot platform deep-dive. Running in background. Output will land in `docs/references/happyrobot/` organized per the folder skeleton from memory (`feedback_references_org.md`): `platform-concepts.md`, `node-taxonomy.md`, `tool-calls/`, `workflows/`, `webhooks/`, plus `README.md` index.

**Memory state (for Claude-Code continuity)**: 7 feedback memories active under `C:\Users\Andre\.claude\projects\c--Users-Andre-OneDrive-Documentos-GitHub-Robot\memory\` — engagement style, terse step cues, closing-section format, auto-accept summary, activity-log discipline, HR platform manual actions, references org, and decision documentation. Index at `MEMORY.md`.

**Next**: Await (a) Andres's review of CLAUDE.md, activity log, and ADR-001, and (b) WS4 research completion. After both, decide whether to start Step 2 (FastAPI skeleton — API core) or invest more time in Claude Code env first. Default if Andres doesn't direct: start step 2 on the next session, gated on WS4 research having produced something usable.

### 14:15 — Kickoff commit landed

**What I did**: Staged and committed the three kickoff files with conventional-commit message `chore: kickoff — CLAUDE.md + activity log + ADR-001 (ruff-alone)`. Commit SHA `f11d223`. Git emitted LF→CRLF warnings on the three files — this is the default Windows `core.autocrlf` behavior on a cross-platform repo; benign for now, ADR-worthy if it causes diff-noise later.

**Files touched**: none new — just the commit on the three previously-created files.

**Next**: Wait for WS4 research agent to finish and populate `docs/references/happyrobot/`. When it does, commit that batch separately.

### 19:45 — HappyRobot MCP server wired (pending Andres env-var setup)

**What I did**: Discovered HR publishes `@happyrobot-ai/mcp` — an official MCP server built for Claude Code, Cursor, and VS Code Copilot. Provides tools for workflow management + integration setup + node config + testing, plus knowledge-base prompts (`platform-overview`, `workflow-building`, `voice-agent-config`, `integrations-guide`, `testing-evaluation`) that load HR platform docs directly into conversation context. This replaces the support-agent relay path for most architecture questions.

**Files touched (created/modified)**:
- `.mcp.json` — new at repo root. Config per HR docs. Uses `${HAPPYROBOT_API_KEY}` env-var reference — **no key committed**.
- `CLAUDE.md` — added "Developer setup" section listing Python 3.12 + uv, Node 18+ for MCP, and three env vars (`HAPPYROBOT_API_KEY`, `API_BEARER_TOKEN`, `FMCSA_WEB_KEY`).
- `docs/references/happyrobot/docs-sitemap.md` — new. Full 3-section HR docs map (Platform, TypeScript SDK, Platform V2 API) with reading priority list + candidate support-agent questions. Captured before MCP discovery; still useful as a map.
- `MEMORY.md` + `reference_hr_docs.md` — new memory pointer. `docs.happyrobot.ai` is authoritative; prefer over third-party blogs.

**Context**: The docs portal itself is access-gated — WebFetch returns the "Enter access code" screen for every page. So the `docs-sitemap.md` was populated from Andres's manual paste. The MCP server bypasses this entirely: once connected, I can load HR's knowledge-base prompts and call MCP tools to list/inspect workflows directly.

**Handoff to Andres**:
1. Go to HR Settings → API Keys → Create API Key. Copy it.
2. Open PowerShell and run (persistent for new terminals):
   ```
   [Environment]::SetEnvironmentVariable('HAPPYROBOT_API_KEY', 'hr_...<your-key>', 'User')
   ```
3. Restart Claude Code / the VS Code window so the env var + `.mcp.json` are picked up.
4. Say "MCP ready" and I'll load the platform-overview + voice-agent-config prompts and answer Q1–Q5 directly.

**Decisions baked in**:
- `.mcp.json` at **repo root** (not `.claude/`) — HR's docs prescribe this path; it's also the Claude Code convention for project-shared MCP servers so future collaborators pick it up automatically.
- `${HAPPYROBOT_API_KEY}` env-var reference (never inline) — HR docs explicitly warn against committing keys; matches our discipline on `API_BEARER_TOKEN` / `FMCSA_WEB_KEY`.

**Next**: Andres sets env var + restarts. Then I synthesize HR knowledge via MCP, revisit Architecture 1-vs-2 decision with real info, and resume WS2b (FMCSA endpoint) or pivot.

### 18:30 — WS2a: minimal FastAPI skeleton landed

**What I did**: Scaffolded the FastAPI backend's first slice. 20 source files + uv.lock. Bearer auth (header + `?token=` fallback), `/healthz` (no auth), `/v1/loads/search` (Bearer required), 10 seeded loads in `data/loads.json`. structlog JSON to stdout. No FMCSA / negotiate / calls-log / dashboard yet — those land in WS2b/WS2c/WS5.

**Files (21 total in commit, including uv.lock)**:
- Root: `.gitignore`, `.gitattributes` (eol=lf — resolves CRLF warnings going forward)
- `api/.env.example`, `api/pyproject.toml`, `api/uv.lock`
- `api/app/`: `main.py`, `config.py`, `deps.py`, `models.py`, `services/load_store.py`, `routers/health.py`, `routers/loads.py` (+3 `__init__.py`)
- `api/tests/`: `conftest.py`, `test_health.py`, `test_auth.py`, `test_loads.py` (+1 `__init__.py`)
- `data/loads.json` (10 loads, 4 equipment types, 17 states, rate range $850–$2500)

**Tooling installed**: `uv 0.11.7` via `pip install --user uv`. Lives at `C:\Users\Andre\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.9_qbz5n2kfra8p0\LocalCache\local-packages\Python39\Scripts\uv.exe`. **Add to PATH** for convenience: `export PATH="/c/Users/Andre/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.9_qbz5n2kfra8p0/LocalCache/local-packages/Python39/Scripts:$PATH"` (or the Windows equivalent).

**Verification (all green)**:
- `uv sync --extra dev` → 32 deps installed (fastapi 0.136, pydantic 2.13, structlog 25.5, ruff 0.15, pytest 9.0, …)
- `uv run pytest -q` → **15/15 passed in 0.28s**
- `uv run ruff check .` → all checks passed
- `uv run ruff format --check .` → 15/15 formatted (one file was formatted on first run; now clean)

**Run locally**: `cd api && uv run uvicorn app.main:app --reload` → :8000

**Decisions baked in (no separate ADR — captured in CLAUDE.md / inline / commit msg)**:
- pyproject.toml at `api/`, not repo root (cleaner monorepo boundary; dashboard will sit alongside at `dashboard/` later)
- Single `models.py` (not split per-domain) — split when count >10
- `B008` ruff rule ignored (FastAPI `Depends(...)`/`Header(...)` defaults are intentional)
- TestClient via context manager → properly exercises lifespan startup/shutdown
- Test fixtures monkeypatch `settings` attributes (pydantic v2 BaseModel allows mutation by default)

**Commit**: `2f81a6d` — `feat(api): WS2a minimal FastAPI skeleton with bearer auth and /v1/loads/search` — 21 files, +1394 lines (incl. ~1000 lines uv.lock).

**Next**: WS2.5 — Dockerize this skeleton + deploy to Fly.io. Once deployed, HR-side step 1 (Andres creates workflow + first tool-call node pointing at `https://robot-api.fly.dev/v1/loads/search`) can run in parallel with WS2b (FMCSA endpoint).

---

### 17:50 — Split voice-agent-prompting (5 → 6 files)

**What I did**: Per Andres's pick, split `voice-agent-prompting.md` into `voice-agent-prompt.md` (the in-call Agent-node system prompt) and `post-call-extraction-prompt.md` (the workflow-level Post-Call setting). They were mixed-purpose in the combined file — different parts of the HR UI configure each. Updated cross-refs in `platform-essentials.md`, `design-notes-for-our-workflow.md`, and `README.md`.

**Files**: 1 rename (voice-agent-prompting → voice-agent-prompt), 1 new (post-call-extraction-prompt), 3 modifications (cross-ref updates), 0 deletions. HR ref dir now at 6 files.

**Commit**: `4c50935` — `docs(hr): split voice-agent-prompting into in-call vs post-call prompts`.

**Next**: still WS2a — minimal FastAPI skeleton.

---

### 17:30 — HR docs trim (12 → 5 files)

**What I did**: Coalesced the over-grown HR reference directory from 12 files in 3 directories down to 5 files at the top level. No content lost; merged for scannability per Andres's "concise + clean + modular; coalesce when appropriate" preference.

**Mapping**:
- platform-concepts + node-taxonomy + gotchas → `platform-essentials.md` (NEW)
- post-call-extraction → absorbed into `voice-agent-prompting.md`
- tool-calls/patterns + transfer-mock + webhooks/call-ended → absorbed into `design-notes-for-our-workflow.md`
- tool-calls/README.md (redundant index) → deleted
- README.md → regenerated for the new 5-file index
- testing.md → unchanged

**Files**: 8 deletions, 1 new file, 3 modifications, 2 empty subdirs removed (tool-calls/, webhooks/).

**Commit**: `4cfb209` — `docs(hr): coalesce 12 reference files into 5 (remove subdirs)` — net -342 lines (576 insertions, 918 deletions).

**Plan doc updated** earlier: `C:\Users\Andre\.claude\plans\now-i-want-you-fizzy-eagle.md` now has a "Current state + sequencing principle" section, the trim plan, and a "Next step in flight: WS2a" spec.

**Next**: WS2a — minimal FastAPI skeleton. 16 files: `.gitignore` + `.gitattributes` + `.env.example` + `api/` (pyproject.toml, app/main.py, app/config.py, app/deps.py, app/models.py, app/services/load_store.py, app/routers/health.py, app/routers/loads.py, tests/) + `data/loads.json`. Awaiting Andres review of the trim before scaffolding code.

---

### 16:30 — WS4 research landed, with a pivot

**What I did**: The backgrounded Explore agent hit a tool-permission wall — Explore subagents are read-only (no `Write`/`Edit`). It successfully drafted all research, created `docs/references/happyrobot/README.md` + empty `tool-calls/` + `webhooks/` subfolders via Bash, but couldn't save the 10 content files. Rather than re-spawn a general-purpose agent and redo the research, I wrote the 10 files myself using the comprehensive HR research I already had from the earlier (pre-plan-approval) Explore pass. Faster; no duplicate token spend on web-research.

**Files touched (created)**:
- `docs/references/happyrobot/platform-concepts.md` — DAG model, immutable-publish, web-call trigger, AI-worker-as-gatekeeper framing
- `docs/references/happyrobot/node-taxonomy.md` — 8 node types + config fields + our workflow's node count table
- `docs/references/happyrobot/voice-agent-prompting.md` — US freight-carrier persona + 3 few-shot transcripts (BOOKED / declined / FMCSA-fail)
- `docs/references/happyrobot/tool-calls/README.md` — index of 4 tool-call nodes
- `docs/references/happyrobot/tool-calls/patterns.md` — auth + timeout + retry + variable-mapping syntax + idempotency
- `docs/references/happyrobot/webhooks/call-ended.md` — payload shape, Bearer auth, no HMAC, idempotency by call_id
- `docs/references/happyrobot/post-call-extraction.md` — prompt template emitting `CallLogRequest` JSON + outcome/sentiment rules
- `docs/references/happyrobot/transfer-mock.md` — Agent-node-as-transfer pattern (no real SIP)
- `docs/references/happyrobot/testing.md` — Test tab, web-call-test quota cost, debugging checklist
- `docs/references/happyrobot/gotchas.md` — 10-min cap, tier-dependent Bearer support, no HMAC, no analytics-UI, autoscale constraint
- `docs/references/happyrobot/design-notes-for-our-workflow.md` — **the actionable file** — step-by-step 15-step build guide for `inbound-carrier-v1`

**Decisions made**: none new (everything follows prior architectural decisions from the plan).

**Lesson for future research tasks**: when spawning a research agent with an expected artifact (files), use `subagent_type: "general-purpose"` (has `*` tools including Write), not `"Explore"` (read-only). Candidate ADR-002 flagged in next-steps if this pattern repeats.

**Next**: Commit `docs/references/happyrobot/` as a `docs(hr):` batch. Then decide with Andres whether to (a) start Step 2 (API skeleton / WS2) or (b) prepare the FMCSA reference stub `docs/references/fmcsa/` since that's the other research-heavy area before API work.

## 2026-04-24

### 01:40 — HappyRobot full-platform KB extracted to `C:\Users\Andre\happyrobot-kb\` (outside repo)

**What I did**: Andres pasted the full HappyRobot platform docs (docs.happyrobot.ai, ~12k lines / 489 KB) into `docs/references/happyrobot/Happyrobot docs.txt`. That file doesn't belong in the repo (scraped vendor docs, large, noisy) but was too valuable to lose. Re-architected it into a scalable, searchable knowledge base outside the git tree.

**Research phase** (two rounds, 9 parallel Explore agents): produced domain-scoped content maps — platform & authoring · voice/integrations/KB/data · quality & ops · API/SDK · UI click-paths · voice prompting · webhooks+deploy+CI-CD · channels+contacts+assets · security/limits gap-fill. All maps line-range-anchored against the raw dump.

**Execution phase** (parallel + serial): moved the dump to `C:\Users\Andre\happyrobot-kb\source\happyrobot-docs-full.txt`; created a 16-folder tree; fanned out 7 parallel writer agents owning 2–10 files each (52 body files total); wrote 5 synthesis files myself (MANIFEST, GLOSSARY, GOTCHAS, OPEN-QUESTIONS, showcase/demo-capabilities) after the synthesizer sub-agent hit a sandbox-scope wall on the external path.

**Files touched**
- **Moved out of repo**: `docs/references/happyrobot/Happyrobot docs.txt` → `C:\Users\Andre\happyrobot-kb\source\happyrobot-docs-full.txt`
- **Created outside repo**: 57 markdown files under `C:\Users\Andre\happyrobot-kb\` across `platform/`, `authoring/`, `voice/`, `channels/`, `knowledge-bases/`, `integrations/`, `data-storage/`, `contacts/`, `experimentation/`, `quality/`, `runs-ops/`, `api-sdk/`, `ui/`, `security/`, `showcase/`, plus 4 root anchor files (`MANIFEST.md`, `GLOSSARY.md`, `GOTCHAS.md`, `OPEN-QUESTIONS.md`). 9,231 total lines. Every file carries `title/slug/topics/source_lines/see_also` frontmatter + TL;DR + Gotchas + Open questions sections. Every claim cites `(source:L####)` against the frozen dump.
- **CLAUDE.md**: added KB pointer under "Where things live" + new "ask Andres anytime about the HR platform" rule.
- **.gitignore**: added `docs/references/happyrobot/Happyrobot docs.*` as belt-and-suspenders.
- **Memory** (persistent across sessions): `reference_hr_kb.md` (KB location + navigation) + `feedback_ask_platform_questions.md` (Andres explicitly invites questions → log resolutions in OPEN-QUESTIONS.md). `MEMORY.md` index updated.

**Decisions made**
- **KB root outside the repo** at `C:\Users\Andre\happyrobot-kb\` — never commit vendor docs. Absolute path keeps it reference-friendly from CLAUDE.md and memory. Repo's existing 6-file `docs/references/happyrobot/` stays project-scoped (our workflow, our prompts, our tests); new KB is vendor-scoped.
- **Topic-sharded tree + `topics:` frontmatter as search index** — Grep on `topics:` finds every file touching a tag. Each file ≤ ~340 lines; MANIFEST 169 lines (< 200 cap so it doesn't get auto-truncated). 
- **Synthesizer owns MANIFEST / GLOSSARY / GOTCHAS / OPEN-QUESTIONS** — single source of truth for the index, glossary, and cross-domain gotchas; all pull from body files' frontmatter + sections.
- **Writer sub-agents pin to `general-purpose` not `Explore`** — writer phase needs Write access. (Same lesson as WS4; confirmed it applies here.)

**Verification**
- 57 .md files, 9,231 lines total.
- No file > 500 lines (max 339).
- Citation round-trip: spot-checked L1870 (iteration_element), L820 (webhook URL), L5899 (northstars) — all match the frozen dump.
- Topic tags: ~180 unique, covering every domain.
- `git status` on repo: only intentional edits (.gitignore, CLAUDE.md, activity-log). Raw dump confirmed removed from repo.

**Lessons**
- Sub-agents have a narrower filesystem scope than the main agent. The synthesizer was blocked from `C:\Users\Andre\happyrobot-kb\` even though the same path worked for the writer sub-agents' `Write` calls (writers needed only to create new files; the synthesizer needed to Glob + Read existing ones). Workaround: the main agent did it directly.
- 7 parallel writers in one message worked cleanly and produced consistent output — the content-map-in-prompt pattern kept each agent focused without re-reading the 12k-line dump.
- Research-agent saturation point hit fast. 9 agents across 2 rounds produced strongly overlapping summaries on secondary topics. More research would have been diminishing returns — the bottleneck moves to synthesis + execution after the first 3 well-scoped agents.

**Next**: Commit the CLAUDE.md + .gitignore + activity-log changes as `docs(hr): extract full-platform KB outside repo`. Then decide with Andres whether to (a) pick up WS2b (remaining FastAPI endpoints), (b) start WS3 (negotiation engine), or (c) do WS2.5 (Dockerize + deploy to Fly so HR-side step 1 can run in parallel with the API work).

### 12:00 — Final v4 architecture lock + project doc consolidation

**What I did** (end-of-long-day summary): locked the `inbound-carrier-v4` HR workflow architecture after ~4 rounds of scope iteration with Andres, and consolidated all the project docs to match. The v4 architecture is now the single source of truth — prior plan iterations (external `/v1/negotiate/evaluate`, `/v1/fmcsa/verify`, `data/load-policies.json`, server-side negotiation state machine, 10-outcome enum, Tier A/B/C sophistication framework) are all superseded.

**Final locked decisions**
- **Workflow**: fork Version 3 → `inbound-carrier-v4`. Version 3 stays as rollback baseline.
- **Tools under Prompt (4)**: `verify_carrier` (HR demo FMCSA direct, not our API), `find_available_loads` (our API), `search_loads_by_lane` (our API), `negotiate_evaluate` (HR Python Code **security sidecar** — main Prompt never sees floor/target/discount; prompt injection can't extract what's not in the context).
- **Workflow variables (4)**: `negotiation_floor_pct` (0.10), `max_negotiation_rounds` (3), `company_name`, `agent_name`. Plus `API_BEARER_TOKEN` workflow secret.
- **Post-call chain**: Classify Outcome (8 tags) → Classify Sentiment (4 tags) → Extract (full CallLogRequest incl. `room_name` / `case_health_score` / `max_buy` / `discount_pct` / `audit_remarks` / `enrichment_data`) → Computations → Case Health Score (int 0–100) → Carrier Sales Auditor → Transfer Popup (BOOKED only) → Enrichment group (Split-up + From Past Capacity + Find Matching Carriers + From Truckstop, outcome-gated) → POST `call.ended` → our `/v1/calls/log`.
- **Our FastAPI**: 3 core endpoints (`GET /v1/loads/{ref}`, `GET /v1/loads/search`, `POST /v1/calls/log`) + 4 dashboard aggregate endpoints + optional `GET /v1/policy/defaults` + `GET /v1/carrier-profile/{mc}`. No `/v1/negotiate/evaluate`, no `/v1/fmcsa/verify`.
- **Storage**: our JSON files only (`data/loads.json`, `data/calls.json`, optional `data/policy.json`). HR Twin DB stays unused — dashboard is a graded deliverable and belongs on our infra. HR Contact Intelligence STAYS enabled in-call for complementary context recall.
- **Outcome enum (8 tags, industry-standard)**: BOOKED / CARRIER_DECLINED_RATE / CARRIER_DECLINED_UNAVAILABLE / BROKER_DECLINED_INELIGIBLE / BROKER_DECLINED_NO_MATCH / NEGOTIATION_STALLED / CALLBACK_SCHEDULED / ABANDONED.
- **Sentiment enum (4 tags)**: POSITIVE / NEUTRAL / NEGATIVE / FRUSTRATED.
- **FMCSA eligibility rule**: `allowedToOperate == "Y"` AND `statusCode == "A"` AND `censusType == "C"`. Manual review flag on `safetyRating == "CONDITIONAL"` or `isPassengerCarrier == "Y"`. Baked into the Prompt's Step 2.
- **MC number validation**: numeric-only, any length (5–8 digits is typical but not enforced; FMCSA returns `content: null` for unknown MCs).
- **Transfer Popup** added on BOOKED path for production-ready warm-handoff context (even though actual transfer is mocked per spec).
- **No Closer Agent node** — main Inbound Voice Agent handles acceptance + outro + mock transfer inline per spec literal wording.
- **Dynamic prompt / DB-backed variables**: declined for MVP (scope creep, latency cost, no day-1 data). One minimal compromise if wanted: `GET /v1/policy/defaults` as a single tool called at call start to pull the 4 workflow-variable values from our DB. Tier-2 roadmap otherwise.

**Step 0 — FMCSA schema captured (live)**

Andres ran `GET https://mobile.fmcsa.dot.gov/qc/services/carriers/738144?webKey=...` → returned full TRAVIS INC record. Schema locked:

```
content.carrier: { legalName, dotNumber, allowedToOperate, statusCode,
  carrierOperation: {carrierOperationCode, carrierOperationDesc},
  censusTypeId: {censusType, censusTypeDesc, censusTypeId},
  safetyRating, isPassengerCarrier, insurance fields, phy* address fields,
  crash + OOS metrics, totalDrivers, totalPowerUnits }
retrievalDate: ISO 8601
```

Unknown MC → `content: null`. Eligibility rule above locks the 3-field AND gate.

**Files touched (consolidation pass)**

- `CLAUDE.md` — updated Stack (now lists v4 workflow name + 3-endpoint API surface), Auth/Observability/Data stores/HR variable references sections, What NOT to do (removed stale rules about `/v1/negotiate/evaluate`, `/v1/fmcsa/verify`, `data/load-policies.json`, `negotiation.py` state machine; added new rule on `@` picker use and no DB-backed prompts for MVP).
- `docs/references/happyrobot/design-notes-for-our-workflow.md` — full rewrite for v4. 14-step build plan, architecture diagram, negotiate_evaluate Python stub, Transfer Popup reference, `call.ended` webhook reference, architectural decisions log, unresolved questions.
- `docs/references/happyrobot/voice-agent-prompt.md` — updated with the canonical v4 Prompt body (paste-ready), 4-workflow-variable references, FMCSA handling (null / allowedToOperate / statusCode / censusType / safetyRating), prompt-injection defense rules, 3 few-shot examples incl. injection-attempt case.
- `docs/references/happyrobot/post-call-extraction-prompt.md` — rewritten for the 8-tag Outcome + 4-tag Sentiment + full CallLogRequest schema with `room_name`, `case_health_score`, `max_buy`, `discount_pct`, `audit_remarks`, `enrichment_data`. Full JSON Schema with `additionalProperties: false` everywhere (strict mode).
- `docs/references/happyrobot/platform-essentials.md` — rewrite; node taxonomy now lists only the nodes used in v4; new "HR variable references — use @ picker" gotcha; FMCSA eligibility rule; Transfer Popup + Enrichment group added.
- `docs/references/happyrobot/testing.md` — removed stale references to server-side negotiation-engine tests and `fmcsa.fetch` cache warming; added the variable-resolution debugging pattern we hit today; updated to reference Chat Playground for iteration.
- **Memory** (persistent): new `feedback_hr_variable_resolution.md` — HR's `@` picker is mandatory; hand-typed templates silently fail at runtime. `MEMORY.md` index updated.
- `C:\Users\Andre\.claude\plans\view-docs-references-happyrobot-happyrob-fuzzy-boot.md` — plan file updated with final-scope-locked architecture; older Tier A/B/C + 15-step iterations kept in-file for history but superseded.

**Consolidation pattern used**

3 parallel writer agents for the big HR reference rewrites (design-notes, voice-agent-prompt, post-call-extraction-prompt), main agent did CLAUDE.md + platform-essentials + testing + memory + activity-log + plan file. All agents ran in the repo working dir without sandbox issues. No rate-limit blowups this time.

**Lessons captured**

- HR's variable-resolution gotcha is load-bearing — saved to memory so future sessions start with it in context.
- Scope iteration is costly but productive: we locked a better architecture (HR-native negotiation via security sidecar, Transfer Popup for warm handoff, enrichment group for A/B analysis + broker-team outreach) than the original plan had.
- Sub-agents work cleanly when scope is tight and paths are inside the repo working dir. The earlier sandbox issue was specific to the external `C:\Users\Andre\happyrobot-kb\` path.

**Next**

Continue the 14-step v4 build plan — Andres works through HR-side steps, I hold Part B (API) until Step 14 publish. Active step: Step 1 (fork Version 3 → `inbound-carrier-v4`).

### 03:30 — Live-console inspection pass: IA correction + 10 new intel drops

Andres paused workstreams and switched me into "platform inspector" mode. Over two screenshot batches he dropped ~12 independent pieces of intel from his live HR console. Major corrections + discoveries vs the scraped docs (which were from an older UI revision):

**IA corrections (scraped docs → live truth)**
- Left sidebar: two buckets (Workflows, Integrations), NOT the 13-item top-nav I had. Under Workflows: Open Workflows / Apps / Twin / Resources. Under Integrations: Open Integrations / Knowledge Bases / Voices / Telephony / Components / Channels / Contacts.
- Workflow tabs: Editor / Runs / Experiments / **Evals** (Northstars, Custom Tests, Adversarial) / **Monitor** (Analytics, Errors, Flags, Northstar Audits) / Workflow settings (General, Variables, Approval Process, Out of Office, Webhooks). The "Build/Evaluate/Audits/Analytics/Experiments/Settings" tab list from scraped docs is stale.
- Quality is split across *two* tabs: **Evals** authors, **Monitor** reads.
- Channels/Voices/Telephony/KBs/Contacts live under Integrations (not "Assets" — that label doesn't exist in the live console).

**New intel (not in scraped docs)**
- **Apps**: left-sidebar frontend-scaffolder. Create dialog: Name / Description / Template (Next.js, Vite static, maybe more). Likely pairs with HappyRobotChatClient/VoiceClient. Documented in new `platform/apps.md`.
- **Twin table modes**: Empty Table / **Polling Table** (syncs external REST API on a schedule — entirely new, wasn't anywhere in the dump) / Workflow Dump.
- **Resources page categories**: All / CRM / HRIS / ATS / Accounting / Ticketing / File Storage / **Authentication** / Communications / Data / **MCP** / **Social**. Authentication / MCP / Social are new categories.
- **Merge integration** (UUID `019db864-...`, "Connect 200+ SaaS providers via Merge unified API") is what backs Accounting / ATS / CRM / HRIS / Ticketing / File Storage — via Merge.dev's unified API. Single credential fans out to 200+ SaaS providers.
- **Custom LLM Server integration** — "Bring your own OpenAI-compatible endpoint for headless voice agents." Almost certainly what the `Use Custom LLM: Yes` toggle on prompt nodes hooks into.
- **KB source types include audio + images** (not just docs/URL/text as scraped docs implied). Max 10 MB each.
- **Components system**: two types (Prompt Component, Node Component). Documented in new `integrations/components.md`.
- **Integration UUIDs** harvested from Components picker — 31 integration UUIDs including Auditor `bb0d1f9b-...`, Merge `019db864-...`, Capacity `01933c77-...`, Negotiation `c752c861-...`, Twin `ebd81a7b-...`, etc.
- **Auditor clarification**: generic integration UUID `bb0d1f9b-...` ("Audit your agents"); "Carrier Sales Auditor" is an event/action under it, not a standalone node type. Other auditor events likely exist; submenu not yet mapped.
- **LLM catalog confirmed**: GPT-only in standard dropdown on Andres's org (`gpt-4.1`, `gpt-4.1-mini`, `gpt-5`, `gpt-5-mini`, `gpt-5-think`). No Claude/Gemini in standard dropdown. The `Use Custom LLM: Yes` toggle is the suspected gateway — not yet clicked.
- **Andres's in-progress workflow "d"** shows the take-home target shape: Inbound Voice Agent → Prompt with two tools (`verify_carrier` → webhook "GET MC Number", `find_available_loads` → webhook "GET load") → AI Classify + AI Extract. Roughly what we're targeting for `inbound-carrier-v1`.

**Files touched this pass**
- KB additions: `experimentation/a-b-testing.md` (draft-form UI section), `integrations/data-stores.md` (Table creation modes — Empty / Polling / Workflow Dump), `integrations/catalog.md` (Resources-page categories, Merge, Custom LLM Server, Google Calendar / MongoDB / Notion, integration UUIDs), `knowledge-bases/knowledge-bases.md` (audio + images), `authoring/nodes-builtin.md` (Auditor clarification), `voice/voice-agents.md` (LLM catalog verified, Use Custom LLM pending), `voice/prompting-guide.md` (Prompt node fields corrected incl. Prompt Issues button), `ui/navigation-map.md` (full IA rewrite), `authoring/nodes-core.md` (Add-node menu structure).
- KB new: `authoring/nodes-builtin.md`, `integrations/components.md`, `platform/apps.md`, `showcase/demo-capabilities.md` (added Tier-0 Carrier Sales Auditor).
- KB updates: `OPEN-QUESTIONS.md` — 4 resolutions logged, then 8 more this pass, plus 12 new opens.
- Repo HR files (cross-linked): README.md, platform-essentials.md, design-notes-for-our-workflow.md, voice-agent-prompt.md, post-call-extraction-prompt.md, testing.md, docs-sitemap.md — each now points to the KB for platform depth.

**Session reminders (Andres's explicit requests)**
- When selecting the voice for `inbound-carrier-v1`, remind him to use the **Voices playground** to preview candidates (live-tested during voice selection).
- When designing the repeat-carrier / callback flow, remind him to **try Contact Intelligence** (beta, on his org).

**Still pending (no commit yet; no WS work yet)**
- Task 1: **Carrier Sales Auditor** setup panel + whether it ships pre-built northstars. This is the highest-leverage remaining unknown — shapes the Tier-0 demo.
- Task 6: Flip `Use Custom LLM: Yes` to see what providers appear.
- Task 7: Click Prompt Issues button to see what it surfaces.
- Task 8: Monitor tab sub-sections tour.
- Screen-check A: Bearer header on tool-call (WS2 blocker but WS is paused).
- Screen-check B: Trigger URL format (paste).

**KB state**: ~60 files, ~10k lines, MANIFEST still 169 lines. No file > 500 lines. Background agent running a stale-content audit.

## 2026-04-25

### Current state — Phase 5 complete, Phase 6 next

**Where we are** (HR-first plan, 11 phases total):
- Phase 1 ✓ Twin schema verified (loads=25, calls_log=0)
- Phase 2 ✓ HR `search_loads_by_lane` tool params + Read-from-Twin filters configured (LOAD-0001 returns successfully)
- Phase 3 — `find_available_loads` configured but not full-tested (count=0 in schema view; will validate during Phase 10 test call)
- Phase 4 — `@` picker depth check deferred (can only validate in full workflow run); Plan B flatten-Code-node ready if needed
- Phase 5 ✓ Create Popup node configured at MVP minimum (`phone_number = "MC-{{mc_number}}"`, all other fields default — clears Incomplete validation)
- **Phase 6 NEXT** — HR Workflow Dump → Twin `calls_log` (16 column mappings via `@` picker)
- Phase 7 — delete old POST Call Data webhook
- Phase 8 — sanity check (prompt + 4 `@` vars + Extract/Classify/Auditor)
- Phase 9 — publish v4 to Development
- Phase 10 — first test call (HP-02 sequential intake)
- Phase 11 — iterate based on Phase 10
- (Then Phase 12-14: Fly redeploy + dashboard validation + Phase D deliverables)

**Locked decisions this session**:
- Negotiation discipline rule added to prompt §9 (reactive, alternative-first, never predictable; pasted into HR)
- equipment_type tool param = enum of 5 values (matching seed data); 11-category expansion is Tier-2
- pickup_window tool param = ISO 8601 datetime (NOT enum) per Andres's "enterprise grade" direction
- Cities = free-form for MVP; alias normalization (LA → Los Angeles) is Tier-2
- Multi-call search = sequential 3-call max; parallel fan-out is Tier-2
- HR learnings live in MY memory only, not repo (relocated 2 files this session)
- IaC for HR workflow added to Tier-2 plan (post-MVP Phase D deliverable)
- Tool description vs prompt boundary cleanup = Tier-2 (equipment_type + verify_carrier descriptions both have agent-behavior text)

**Memory files added this session**:
- `feedback_proactive_memory_save.md` — auto-save without asking
- `feedback_anti_jailbreak_negotiation.md` — reactive negotiation discipline
- `feedback_analytics_friendly_enums.md` — enum-constrain any persisted tool param
- `feedback_diagram_principles.md` — logic-only diagrams, no dialogue acts
- `feedback_intent_over_hardcoded.md` — real human behavior over magic numbers
- `reference_hr_component_learnings.md` — meta-rule for HR knowledge auto-save
- `reference_hr_create_popup_schema.md` — full Create Popup field schema
- `reference_hr_procedural_quirks.md` — @ picker / Twin SQL / webhook patterns

**Repo files updated this session**: `prompts/voice-agent-system-prompt.md` (Step 3 + Step 4 + §12 Style + Examples), `docs/test-scenarios.md` (10 edge cases + 3 happy paths + Tier-2 deferrals + IaC), `docs/agent-logic-tree/core.mmd` + `negotiation.mmd` + rendered PNGs, `docs/references/fmcsa/decline-reasons.md`, `scripts/build_logic_tree.py`.

**Next concrete action**: Phase 6 Workflow Dump column mappings. Full instructions in the Phase 6 message at end of this conversation — re-paste below in case compaction loses detail.

---

## 2026-04-30 — ADR-013 operational vs analytical store separation

Locked the data-architecture decision behind the "FAANG-level production architecture: DB or live API?" question raised this session. Captured in [ADR-013](decisions/ADR-013-operational-vs-analytical-store-separation.md).

- **Option A (chosen for MVP):** Operational Twin (`calls_log` + `bookings`) is source of truth. FastAPI `dashboard_aggregations.py` cache + HR REST API drilldown layer on top. No analytical warehouse, no CDC. $0 incremental.
- **Option B (FAANG canonical, deferred):** Operational Twin → CDC stream → warehouse. Tier-2 = self-hosted Postgres replica (~$50-100/mo); Tier-3 = full warehouse + CDC + dbt (~$500-2000/mo). Triggers documented (>100k calls/mo, multi-tenancy, p95 dashboard latency >5s, etc.).
- **Option C (rejected):** Live HR REST API only, no Twin write. Fails on SLA, N+1 cost, idempotency anchor, contradicts ADR-005.

Pairs with ADR-005 (Twin canonical), ADR-007 (caching), ADR-009 (webhook+SSE), ADR-012 (latency compute), and `memory/project_twin_production_lock_in.md`.
