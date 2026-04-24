# Activity Log

Running dev journal for the HappyRobot inbound-carrier take-home. Concise, chronological, scannable. New day = new `## YYYY-MM-DD` heading. Entries are appended newest-at-the-bottom within a day.

---

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
