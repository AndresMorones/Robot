# Repo Cleanup Plan

Generated: 2026-04-30 by read-only sweep. **Nothing has been deleted or modified.** Every entry below is a recommendation only.

Scope: `api/`, `dashboard/src/`, `dashboard/` (root files), `data/`, `docs/`, `prompts/`, `scripts/`, `tests/`, repo-root scratch files.

Excluded from this sweep: `~/.claude/`, `node_modules/`, `dashboard/.next/`, `api/.venv/`, anything currently gitignored, plus the live-edit zones for sibling sub-agents (`dashboard/branding-preview.html`, `docs/rollouts/notes-column-rollout.md`).

---

## Total candidates by category

| Category | Files | Est. on-disk size |
|---|---|---|
| Definitely safe to delete | 21 | ~1.9 MB |
| Likely safe to delete | 13 | ~330 KB |
| Needs review | 9 | ~140 KB |
| **Total** | **43** | **~2.4 MB** |

If only the green tier is removed, the repo loses ~1.9 MB (mostly the 1.65 MB of `scripts/iac/snapshots/` + `scripts/snapshots/hr-iac-2026-04/` IaC pre-cutover JSON dumps).

---

## Top 5 most-confident deletions to start with

1. **`dashboard/src/components/call-detail.tsx`** — explicit "legacy monolith" called out in `dashboard/src/app/dashboard/calls/[call_id]/page.tsx` lines 6-9; replaced by `call-detail/` directory; zero importers.
2. **`scripts/iac/snapshots/v3_nodes.json`, `v5_nodes.json`, `v6_nodes.json`, `v7_nodes.json`, `v8_nodes.json`, `v6_phase_a_remap.json`, `calculate_carrier_cost.py`** (~800 KB) — pre-v15 IaC API-mutation experiments; the `apply_*.py` scripts that read them are themselves dead per ADR-002 + memory `reference_hr_post_batch_corruption.md` ("API POST corrupts voice — UI-only for workflow nodes").
3. **`scripts/snapshots/hr-iac-2026-04/`** entire directory (~860 KB) — same era as above, includes empty `v6_editor_data.json` and 404-error stub `extract_node.json` / `classify_node.json`.
4. **`data/calls_log.sql`** — superseded 24-col DDL draft; live Twin schema is 15 cols (per `api/app/services/calls_store.py` docstring "Live schema (probed 2026-04-29 — 15 columns")). Documents a column set (`agent_version`, `dot_number`, `legal_name`, `dba_name`, `caller_name`, `caller_role`, …) that was never created.
5. **`data/calls_log_review_2026-04-27.json` + `.ndjson`** (208 KB) — one-off review snapshot; created by `scripts/split_calls_log.py`; not referenced by any runtime code or test.

---

## Definitely safe to delete (zero risk)

Files explicitly marked legacy/deprecated in their own header, files no other file imports/references, scratch artifacts, or DDL for tables that no longer exist.

| Path | Reason | Size |
|---|---|---|
| `dashboard/src/components/call-detail.tsx` | Called out in `[call_id]/page.tsx` as "the old `call-detail.tsx` (legacy monolith)"; replaced by the `call-detail/` directory; zero importers in dashboard; `CallDetail` symbol unused. | 14 KB |
| `data/calls_log.sql` | Superseded 24-col DDL draft; live Twin `calls_log` is 15 cols. Only referenced by docs that already cite the v15 cleanup script. | 3.7 KB |
| `data/calls_log_review_2026-04-27.json` | Snapshot from 2026-04-27 review session. No code references. | 70 KB |
| `data/calls_log_review_2026-04-27.ndjson` | Same snapshot, ndjson form. No code references. | 136 KB |
| `data/load-policies.json` | Per CLAUDE.md "What NOT to do": the `negotiation.py` state machine + `load-policies.json` were removed from the architecture (activity-log line 272, 306 confirms). HR `negotiate_evaluate` sidecar replaced it. Zero code references. | 3.6 KB |
| `data/fmcsa-fixtures/` (8 JSON files) | Per cleanup task, "unused if no test uses them" — confirmed: `Grep` for `fmcsa-fixtures` returns hits only in README and `execution-plan-2026-04-29.md`. No test imports them. | 12 KB |
| `data/twin_seed_loads.sql` | v1 seed (25 rows, past-dated). Superseded by `twin_seed_loads_v2.sql` (150 rows, May 2026+). README §"data/" already lists the v2 file as canonical. | 4.9 KB |
| `scripts/iac/snapshots/v3_nodes.json` | 211 KB pre-cutover IaC dump. Read only by the dead `analyze_v5.py` / `apply_phase_a.py` scripts. Per memory `reference_hr_post_batch_corruption.md` API-POST mutation path is abandoned. | 211 KB |
| `scripts/iac/snapshots/v5_nodes.json` | Same era. | 168 KB |
| `scripts/iac/snapshots/v6_nodes.json` | Same era. | 159 KB |
| `scripts/iac/snapshots/v7_nodes.json` | Same era. | 157 KB |
| `scripts/iac/snapshots/v8_nodes.json` | Same era. | 101 KB |
| `scripts/iac/snapshots/v6_phase_a_remap.json` | Output of `apply_phase_a.py`; same dead path. | 1.8 KB |
| `scripts/iac/snapshots/calculate_carrier_cost.py` | Misplaced sidecar copy of legacy v5 cost calculator (current canonical is `scripts/hr-tools/calculate_rate.py`). | 4.7 KB |
| `scripts/snapshots/hr-iac-2026-04/` (entire directory, 22 files) | Pre-v15 IaC dumps including `v6_editor_data.json` (empty), `extract_node.json` + `classify_node.json` (404 error stubs from API probes), and 18 other one-off node dumps used during the abandoned API-mutation effort. | 860 KB |
| `scripts/iac/analyze_v5.py` | Reads `v5_nodes.json`. Dead path. | 4.5 KB |
| `scripts/iac/analyze_v6.py` | Reads `v6_nodes.json`. Dead path. | 3.3 KB |
| `scripts/iac/apply_one_node.py` | API mutation prototype. Per memory, this path corrupts voice. | 3.0 KB |
| `scripts/iac/apply_one_node_fixed_model.py` | Same path. | 2.4 KB |
| `scripts/iac/apply_phase_a.py` | Same path. | 8.7 KB |
| `scripts/iac/snapshot_version.py` | Helper for the IaC API-mutation effort. | 2.8 KB |
| `scripts/iac/diagnose_import.py` | Diagnostic for the abandoned `import-from-template` flow per memory `reference_hr_import_breaks_references.md`. | 6.0 KB |
| `scripts/iac/bootstrap_minimal.sh` | Bash bootstrap for the abandoned IaC. | 2.2 KB |
| `scripts/hr-tools/apply_demo_adjustment.py` | Only mention in active code is in `case_health_score.py` as a regex pattern to flag the agent improperly invoking the tool. The script itself is unused in v15 (HR `negotiate_evaluate` Python sidecar replaced this concept; v2-DRAFT prompt was the only place that wired it in). | 3.5 KB |
| `scripts/build_logic_tree.py` | Renders the `core.mmd` + `negotiation.mmd` mermaid sources to PNG. The `agent-logic-tree/rendered/` PNGs already exist on disk. Not in CI. Single use script — keep ONLY if you plan to re-render. | 7.4 KB |
| `scripts/add_write_twin_node.py` | Documented as "verified working 2026-04-25" — but the architecture shifted to UI-build-only. Per memory `reference_hr_post_batch_corruption.md` this path corrupts voice on forks. | 5.7 KB |
| `prompts/voice-agent-prompt-v1.md` | 1.7 KB v1 prompt. Zero references in any active doc. Superseded by v2 → v3 → v4 → v5.1. | 1.7 KB |
| `prompts/voice-agent-system-prompt-v2.txt` | Plain-text duplicate of `voice-agent-system-prompt-v2.md` — no markdown header, never updated. Only the .md is referenced in docs. | 36 KB |
| `prompts/voice-agent-system-prompt-v2-DRAFT.md` | "DRAFT" in filename; superseded by the non-DRAFT `voice-agent-system-prompt-v2.md`. Only mentions `apply_demo_adjustment` (also dead). | 40 KB |
| `prompts/ai-extract-schema.md` | v1 (16 fields). Superseded by `ai-extract-schema-v3.md` (v3.2, 2 fields, current canonical per `docs/hr-architecture-map.md` line 127 + `docs/rollouts/notes-column-rollout.md` line 51). | 11 KB |
| `sess_messages.json` (repo root) | 26 KB raw HR messages-API export from a 2026-04-28 test call. Scratch; no code references; should never have been committed at the root. | 26 KB |
| `scripts/hr-key-monitor.log` | Already gitignored per memory; appears in `git status` as untracked because of a fresh write. Not committed; nothing to delete. *(Listed only to confirm it stays excluded.)* | — |

**Subtotal: ~21 distinct entries / ~1.9 MB.**

---

## Likely safe to delete (low risk, recommend confirming)

Files referenced only by docs that are themselves stale, schemas superseded by newer versions, review/snapshot files older than current state.

| Path | Reason | Risk |
|---|---|---|
| `data/twin_schema_calls_log.sql` | 22-col DDL — but live Twin `calls_log` is 15 cols (post-v15 cleanup). Only referenced by `dashboard-metric-catalog.md` and `iac-bundle.md`. The v15 cleanup script (`twin_schema_v15_calls_log_cleanup.sql`) is the actual ALTER path; this older file documents an intermediate state. | Confirm whether anyone reseeds from this file; if no, delete. |
| `data/twin_schema_loads.sql` | 15-col DDL is *still* current (live Twin matches). But `data/twin_seed_loads.sql` (v1 seed) has been superseded. Keep the schema file, drop the v1 seed. | Schema file: KEEP. (Listed for symmetry — easy to confuse with the `_v15_` files.) |
| `data/calls.json` | Already gitignored per `.gitignore` line 25. CLAUDE.md says "no longer the canonical store." If the local copy on disk is stale, the gitignore protects the repo; no action needed for committed state. | Already gitignored — no repo action; can delete the local file at user's discretion. |
| `data/twin_mirror/` directory | Already gitignored per `.gitignore` line 30. Generated by `scripts/sync_twin_loads.py`. Same story — local cache, not in repo. | Already gitignored — no repo action. |
| `api/app/routers/dashboard_view.py` | Server-rendered HTML at `/dashboard`. Per CLAUDE.md the Next.js dashboard is the production deliverable; this file is "legacy / fallback." Still mounted in `api/app/main.py:168`. The router is intact and tested; removing it requires unmounting + adjusting `main.py` docstring. | If keeping as fallback, leave; if not, full removal saves 46 KB and one router. |
| `prompts/voice-agent-system-prompt.md` | Untagged version (no v-suffix). Superseded by the v-numbered chain — current canonical is `voice-agent-system-prompt-v5.1.md` per `docs/hr-architecture-map.md`. Still referenced by `iac-bundle.md` line 65, 81 and `ui-build-guide.md` line 87 (both stale docs). | Update those two refs first. |
| `prompts/voice-agent-system-prompt-v2.md` | Earlier prompt iteration. Referenced by stale `v3-prompt-audit/` files only. | Bundle with the v2-DRAFT/v2.txt removal once those are gone. |
| `prompts/voice-agent-system-prompt-v3.md` | v3 audit predecessor. Referenced only by `v3-prompt-audit/` audit files (themselves likely deletable per below) and `v15-book-load-tool-spec.md` line 56. | Confirm v15 spec doesn't still pin to v3; if it does, refresh that ref to v5.1 first. |
| `prompts/voice-agent-system-prompt-v4.md` | v4 predecessor. Referenced by `v15-query-loads-tool-spec.md` line 135 + `execution-plan-2026-04-29.md`. | Confirm v15 spec doesn't still pin to v4. |
| `prompts/voice-agent-system-prompt-v5.md` | v5 (32 KB) — superseded by v5.1 (40 KB) per `hr-architecture-map.md` line 69 + `notes-column-rollout.md` line 170. | Likely safe; confirm v5.1 is the *only* prompt referenced by the live workflow. |
| `prompts/v5-rlhf-tuning-2026-04-29.md` | One-off RLHF tuning artifact (dated in filename). Zero references found in repo. | Confirm not needed for any future audit. |
| `docs/v3-prompt-audit/A-diff-capability.md`, `B-memory-reconciliation.md`, `C-tool-workflow-sync.md`, `D-edge-cases.md` | Audit of v3 prompt vs v15 spec from 2026-04-27. v3 prompt has been superseded by v4 → v5 → v5.1. Only referenced by `execution-plan-2026-04-29.md`. | Confirm audit findings have been incorporated into v5.1 / `hr-architecture-map.md`; if yes, delete the audit docs. |
| `docs/handoffs/2026-04-26-twin-search-architecture.md` | Single handoff doc from before ADR-004 was finalized. ADR-004 supersedes it. Referenced only by ADR-004 ("see also") + `execution-plan-2026-04-29.md`. | Likely safe once ADR-004's "see also" link is cut. |
| `docs/dashboard-v2-research/01-09` (9 markdown files, ~120 KB total) | 9-agent metric-discovery output from 2026-04-28. Findings consolidated into ADR-011 + `dashboard-metric-catalog.md` + `dashboard-chart-review.md`. Only `04-engineering-feasibility.md` line 56 + `02-ux-ia.md` line 243 referenced by anything else, and only internally. | Likely safe; confirm by spot-checking that `dashboard-chart-review.md` is the canonical synthesis. |

---

## Needs review (medium risk)

Files that LOOK unused but might be load-bearing (importlib, runtime config, HR webhook targets, tests-only references, etc.).

| Path | Reason | Why it might be load-bearing |
|---|---|---|
| `api/app/config.py` field `calls_json_path` | Only reference in code is its own definition (`api/app/config.py:20`). No runtime reader. | Defensive: removing also requires editing `.env.example` line(s). Once removed, `calls.json` truly is dead. |
| `api/app/config.py` field `loads_csv_path` + `LOADS_CSV_PATH` env var + `data/loads.csv` (file) + `Dockerfile` `COPY data/loads.csv ./loads.csv` (line 57) + `Dockerfile` `LOADS_CSV_PATH=/app/loads.csv` (line 48) + `fly.toml` line 28 | NO code reader — `load_store.py` reads from Twin only via `twin_client`. The CSV is bundled into the Docker image but never opened at runtime. | Risk: if Twin ever goes down and someone wants to flip a feature flag back to CSV reads, the file is the fallback. But `load_store.py` does NOT have such a flag — it would need to be added. **Cleanup is multi-file** (config + Dockerfile + fly.toml + data/loads.csv + docs). |
| `dashboard/src/components/carrier-rollup-table.tsx` | `dashboard-chart-review.md` line 362 explicitly says "the carriers rollup table has no home. The component is built and unused in any page." | Likely-near-future use: chart-review M-3 recommends wiring it to `/dashboard/carriers/page.tsx`. Defer deletion — likely to be USED, not deleted. |
| `dashboard/src/components/charts/trend-line.tsx` | No importers anywhere in the dashboard. Zero references outside its own file. | Possibly intended for a future chart slot. Either wire it in or delete. |
| `dashboard/src/components/ui/select.tsx`, `dashboard/src/components/ui/separator.tsx` | Both unused — zero imports of `@/components/ui/select` or `@/components/ui/separator` in `dashboard/src`. | Future-proofing for shadcn primitive use. ADR-011 explicitly cut Popover; but these two were not on the cut list. Low priority. |
| `dashboard/library-cut-comparison.html` | One-off design comparison artifact. No references anywhere. | Sub-agent territory? `branding-preview.html` is being edited live; `library-cut-comparison.html` is a SIBLING but not in the protected scope — confirm with user before touching. |
| `docs/iac/ui-build-guide.md` | Per memory `project_ui_build_guide.md` "REBUILD trigger keyword". Pinned to v5_nodes.json (deleted in 🟢 above) and references the pre-v15 architecture extensively. | Load-bearing for a manual workflow rebuild. Either rewrite for v15 or scope down. **Do NOT delete; flag for refresh.** |
| `docs/agent-logic-tree.md` + `docs/agent-logic-tree/` directory (3 files) | Mermaid sources + rendered PNGs of the agent decision logic. Last touched 2026-04-25. | Likely useful for the technical write-up / loom. Keep unless write-up is finalized. |
| `tests/integration/v15/` (5 shell scripts + README) | Twin REST + dashboard SQL integration tests. Not in pytest; bash-driven. | Run-on-demand smoke tests. Keep if you plan to re-run; else flag for archival. |

---

## What NOT to delete (load-bearing despite looking suspect)

A short list of files that *might* trigger a deletion instinct but are actually live:

- `api/app/routers/calls.py` — keeps the deprecation 410 Gone route (hit by any HR workflow still pointing at the old URL); also the live read-only GET endpoints. **Keep.**
- `api/tests/test_calls_deprecated.py` — guards the 410 contract. **Keep.**
- `api/app/routers/calls_active.py` — `/v1/calls/active` is hit live by `dashboard/src/app/api/calls/active/route.ts`. **Keep.**
- `api/app/routers/dashboard_view.py` — flagged as 🟡 above; if kept as fallback, document its status in CLAUDE.md (already noted). The unmount + decision is a deliberate call.
- `data/twin_seed_loads_v2.sql` — current loads seed. **Keep.**
- `data/twin_schema_v15_bookings.sql` + `_calls_log_cleanup.sql` — current DDL migration scripts. **Keep.**
- `scripts/hr-tools/calculate_rate.py` + `case_health_score.py` — referenced by HR Run Python sidecar via copy-paste; mentioned in `hr-architecture-map.md`. **Keep.**
- `scripts/sync_twin_loads.py` — operational tool for refreshing the local mirror. **Keep.**
- `scripts/generate_signed_link.py` + `scripts/monitor_hr_key.py` — operational utilities still useful. **Keep.**
- `scripts/split_calls_log.py` — created the `_review_2026-04-27` snapshots above. If those snapshots get deleted, this script becomes a candidate too. **Tied.**
- `scripts/snapshots/` (parent directory after `hr-iac-2026-04/` is removed) — keep the parent so any future snapshot work has a home.

---

## "Wait, this LOOKS dead but actually..." warnings

1. **`data/loads.csv`**: Bundled into the Docker image. Even though no code reads it, removing the COPY line in `api/Dockerfile` + `LOADS_CSV_PATH` env var requires a coordinated multi-file edit and a Fly redeploy. The CSV is *also* what most reviewers / spec-readers will look at first ("loads.csv" is the literal phrasing in the FDE spec). Recommend KEEPING `loads.csv` as the human-readable spec artifact even though the runtime reads from Twin.

2. **`data/loads.json`**: Per CLAUDE.md "is the read-only seed for the `loads` table." Not loaded by code (Twin is the runtime), but it IS the canonical reference for what's in the seed. Mirrored by `twin_seed_loads_v2.sql`. Recommend keeping for human readability.

3. **`docs/iac/ui-build-guide.md`**: User memory `project_ui_build_guide.md` says: "trigger on keyword `REBUILD`". This file IS load-bearing — it's how you rebuild the workflow from scratch when HR's UI corrupts or you fork from broken state. But it's currently pinned to a pre-v15 architecture (references `v5_nodes.json`). **Refresh, don't delete.**

4. **`docs/handoffs/2026-04-26-twin-search-architecture.md`**: Looks superseded by ADR-004 — but ADR-004 is the *decision*, the handoff is the *context*. If ADR-004 ever needs to be re-litigated, the handoff is the source of options considered + rejected. Low-cost to keep.

5. **`scripts/hr-tools/apply_demo_adjustment.py`**: ALSO appears in the v2-DRAFT prompt as a tool the agent could call. v2-DRAFT is dead (recommended delete) but if someone reinstates that prompt, the script + the regex in `case_health_score.py:62` flag it as forbidden. The regex will keep working with or without the .py file. **Safe to delete.**

6. **`prompts/voice-agent-system-prompt.md` (untagged)**: Some docs in `docs/references/happyrobot/iac-bundle.md` still link to this *unprefixed* filename. If the iac-bundle ever gets executed, those refs break. Cleanup means a docs sweep first.

---

## Recommended sequencing

If the user wants to actually execute deletions, suggested order:

1. **Wave 1 (zero-friction green tier):** the 5 top-confidence items + `data/calls_log.sql` + `data/load-policies.json` + `data/calls_log_review_2026-04-27.{json,ndjson}`. ~230 KB. No follow-up edits needed.
2. **Wave 2 (IaC snapshots):** `scripts/iac/snapshots/` + `scripts/snapshots/hr-iac-2026-04/` + the 6 dead `scripts/iac/*.py` scripts. ~1.7 MB. After this, `scripts/iac/` is empty — also delete the directory.
3. **Wave 3 (prompt graveyard):** v1, v2-DRAFT, v2.txt, `ai-extract-schema.md`, `v5-rlhf-tuning-2026-04-29.md`. After this, refresh `prompts/README.md` to list only v5.1 + ai-extract-schema-v3 + classify-* as canonical.
4. **Wave 4 (docs sweep):** retire `v3-prompt-audit/`, `dashboard-v2-research/`, `handoffs/2026-04-26-*.md` after confirming each has been incorporated into a higher-level doc. Update inbound links from active docs first.
5. **Wave 5 (multi-file architectural cleanup):** decide on `api/app/routers/dashboard_view.py` (keep as fallback or remove entirely). Decide on `loads.csv` Docker bundling (keep for spec readability or remove for hygiene).
