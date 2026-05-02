# v3 Prompt — Memory + Plan Reconciliation Audit (B)

**Subject:** `prompts/voice-agent-system-prompt-v3.md` (last_synced 2026-04-27, target workflow `inbound-carrier-v15`)
**Scope:** every piece of prompt-relevant guidance accumulated in user memory, plans, and `docs/`.
**Reviewer:** Sub-agent B, 2026-04-27.

---

## Section 1 — Relevant memory file inventory

| File | Type | 1-line summary | v3 relevance |
|---|---|---|---|
| `feedback_anti_jailbreak_negotiation.md` | feedback | Reactive, alternative-first, never predictable; genuine interest unlocks rounds | HIGH |
| `feedback_intent_over_hardcoded.md` | feedback | Describe human behavior; floor is the only hard line | HIGH |
| `feedback_edge_case_enumeration.md` | feedback | Enumerate null/zero/wrong-type/etc. before declaring done | HIGH |
| `feedback_lean_design.md` | feedback | Minimal comments, LLM generates lines, no unused params | HIGH |
| `feedback_track_requirements.md` | feedback | Maintain a Requirements Registry across multi-turn design | HIGH |
| `feedback_analytics_friendly_enums.md` | feedback | Enum-constrain any tool param persisted to analytics | HIGH |
| `feedback_tool_param_normalization.md` | feedback | Carrier-speech → canonical examples per structured field | HIGH |
| `feedback_hr_variable_resolution.md` | feedback | Use HR `@` picker; hand-typed `{{var}}` silently empties | HIGH |
| `feedback_spec_is_the_bible.md` | feedback | Every decision must cite an FDE-spec clause | HIGH |
| `feedback_diagram_principles.md` | feedback | Logic + data capture only; no dialogue, no style on diagrams | LOW |
| `feedback_ask_clarifying_questions.md` | feedback | Numbered (a)/(b)/(c) clarifiers on architectural calls | LOW (process) |
| `feedback_ask_platform_questions.md` | feedback | Ask Andres on HR ambiguity vs guess | LOW (process) |
| `project_chs_deduction_model.md` | project | CHS scoring driven by transcript-observable behaviors | HIGH (referenced indirectly) |
| `project_call_end_tool_pattern.md` | project | `finalize_call` terminal-tool pattern; superseded by §9 `book_load` | MEDIUM |
| `project_v14_loop_architecture.md` | project | v14 Loop+Extract array — SUPERSEDED by v15 two-table | MEDIUM (now stale) |
| `project_negotiation_prompt_driven_python_for_show.md` | project | Brain in prompt; `calculate_rate` Python sidecar is "for show" | HIGH |
| `project_post_mvp_prompt_improvements.md` | project | 7 post-MVP prompt enhancements | HIGH |
| `project_post_mvp_agentic_orchestration.md` | project | Module-Change sub-agent vision (post-MVP) | LOW |
| `project_post_mvp_format_discipline.md` | project | Versioned `format-contracts.md` + DDL CHECK constraints | MEDIUM |
| `project_post_mvp_field_design_research.md` | project | 4 sub-agent goliath for canonical enums | MEDIUM |
| `project_post_mvp_self_reflection_column.md` | project | `improvement_signal` column post-MVP | LOW (post-MVP) |
| `project_test_scenarios_phase2.md` | project | 10 lane-search reasoning scenarios for §6 | HIGH |
| `project_field_renames_pending.md` | project | `pitched_loadboard_rate→original_rate`, `agreed_rate→apply_rate` | MEDIUM |
| `project_mvp_scope_locked.md` | project | MVP shape; multi-option pitch when carrier vague | MEDIUM |
| `project_phase3_calls_log_v2.md` | project | calls_log v2 schema; partly superseded by v15 | MEDIUM |
| `reference_hr_create_popup_schema.md` | reference | Transfer Popup integration; phone_number minimum | MEDIUM |
| `reference_hr_post_call_webhook_schema.md` | reference | 48-field webhook catalog | LOW (legacy v3 wf) |
| `reference_hr_twin_empty_string_filter.md` | reference | `equals ""` is literal, not wildcard | MEDIUM |
| `reference_hr_extract_strict_schema_rules.md` | reference | Azure strict-mode rules — Extract not prompt | LOW |

---

## Section 2 — Guidance reconciliation

| # | Source | Guidance summary | Status in v3 | Notes |
|---|---|---|---|---|
| 1 | `feedback_anti_jailbreak_negotiation.md` | Reactive only; lowballers get redirect, not rounds | ADDRESSED | §8.1 explicitly named "Anti-jailbreak negotiation discipline" |
| 2 | `feedback_anti_jailbreak_negotiation.md` | Alternative-first pivot when portfolio non-empty | ADDRESSED | §8.1 + §8.6 multi-load portfolio pivot |
| 3 | `feedback_anti_jailbreak_negotiation.md` | Pitch loadboard as confident fact; no pre-soften | ADDRESSED | §7 explicit "Default outcome is acceptance at loadboard_rate. Pitch the rate as a confident fact" |
| 4 | `feedback_intent_over_hardcoded.md` | No magic-number thresholds in prompt | PARTIALLY-ADDRESSED | §8.4 still uses `~3%`, `5-7%` band hints — defensible as illustrative; §8.3 80% lowball detection IS hardcoded → flag |
| 5 | `feedback_intent_over_hardcoded.md` | Floor is the only hard line | ADDRESSED | §8.5 hard rules 1+2 |
| 6 | `feedback_intent_over_hardcoded.md` | Sentiment + urgency drive strategy, not gap_pct | NOT-ADDRESSED | v3 §8 has no sentiment/urgency-modulated tactics. Persona arc is purely round-driven. |
| 7 | `feedback_edge_case_enumeration.md` | Enumerate nulls/zeros/duplicates per tool param | PARTIALLY-ADDRESSED | §3 covers MC well, §9.5 covers `book_load` failures, but `find_available_loads` null-result has 1 line; `search_loads_by_lane` has zero-match flow but no example of garbled-equipment / wrong-type carrier input |
| 8 | `feedback_edge_case_enumeration.md` | LLM responsibilities spelled out per tool | ADDRESSED | §6 + §9.1 + §9.6 explicit when-to-call / when-not-to |
| 9 | `feedback_lean_design.md` | Minimal comments, prompt is intent | ADDRESSED | v3 is structured but lean, no scripted lines beyond illustrative pitches |
| 10 | `feedback_lean_design.md` | LLM generates the lines, not template tables | ADDRESSED | §13 "Vary phrasing every call"; only one literal locked line (spec transfer wording) |
| 11 | `feedback_track_requirements.md` | Multi-turn requirements registry | NO-LONGER-RELEVANT-TO-PROMPT | Process directive; lives in plan files, not prompt body |
| 12 | `feedback_analytics_friendly_enums.md` | `equipment_type` 5-enum | ADDRESSED | §5 lists 5 with carrier-synonyms |
| 13 | `feedback_analytics_friendly_enums.md` | `pickup_window` ISO-canonical (per current MVP) | ADDRESSED | §0 calendar block + §5 "capture as ISO 8601 per §0" |
| 14 | `feedback_analytics_friendly_enums.md` | `call_outcome` 4-tag enum visibility | NOT-ADDRESSED | Failure tags in §3+§4 (`MC_NOT_FOUND`, `NOT_AUTHORIZED`…) are real-time outcome tags but not consolidated; agent doesn't know which final outcome label gets persisted |
| 15 | `feedback_tool_param_normalization.md` | `LOAD-NNNN` canonical + carrier-speech mappings | PARTIALLY-ADDRESSED | §6 says "preserve exact casing" + "do NOT call with random digits" but no mapping table for `find_available_loads`; v3 §9 covers `load_id` for `book_load`. Mapping examples are in `docs/v15-book-load-tool-spec.md` but not echoed in the prompt |
| 16 | `feedback_tool_param_normalization.md` | MC digits-only + readback | ADDRESSED | §3 thorough |
| 17 | `feedback_hr_variable_resolution.md` | All `{{ ... }}` via @ picker | ADDRESSED | Top of v3 has explicit "Paste rule for HR" |
| 18 | `feedback_spec_is_the_bible.md` | Spec literal transfer wording | ADDRESSED | §10 uses verbatim line; §14 final reminder repeats |
| 19 | `feedback_spec_is_the_bible.md` | "Handle up to 3 back and forths" → spec compliance | ADDRESSED | §8 explicit "up to {{ max_negotiation_rounds }} (3) rounds" |
| 20 | `project_chs_deduction_model.md` | CHS deductions tied to observable behaviors (tool leak −15, role-break −25, etc.) | ADDRESSED-INDIRECTLY | §1 + §12 forbid the leak/role-break behaviors that would deduct; v3 doesn't need to mention CHS itself |
| 21 | `project_chs_deduction_model.md` | "Booked without readback" is a soft −8 | ADDRESSED | §10 step 1 mandates the recap before any transfer line |
| 22 | `project_call_end_tool_pattern.md` | Terminal tool fires structured outcome at decision point | SUPERSEDED-BY-V3-§9 | `book_load` IS the terminal tool for booking outcome. Note: v3 has no terminal tool for the *non-booking* terminal states (FMCSA decline, walk-away, no-match) — those rely on post-call extraction |
| 23 | `project_v14_loop_architecture.md` | Extract a `bookings` array post-call | SUPERSEDED | v3 §9 explicitly notes "Dropped post-call load-array extraction" |
| 24 | `project_negotiation_prompt_driven_python_for_show.md` | `calculate_rate` is the demo sidecar; brain is in prompt | ADDRESSED | §8.3 calls `calculate_rate` once, only when pickup <24h |
| 25 | `project_negotiation_prompt_driven_python_for_show.md` | Time-of-day adjustment as the chosen Option-1 demo | ADDRESSED | §8.3 wires the 24-hour-pickup gate; consistent with Option-3 (pickup urgency) more than Option-1 (after-6pm) but spec-compliant |
| 26 | `project_post_mvp_prompt_improvements.md` #1 — generalize broker persona | ADDRESSED | §1 identity + §13 style pacing |
| 27 | `project_post_mvp_prompt_improvements.md` #2 — active narrowing (1-2 questions before search) | PARTIALLY-ADDRESSED | §2 + §5 collect equipment/origin/pickup but no explicit instruction to ASK before searching when carrier is vague (e.g., "what kind of load are you looking for?" question alternatives missing) |
| 28 | `project_post_mvp_prompt_improvements.md` #3 — off-topic redirect | ADDRESSED | §11 dedicated section, 3-strike pattern |
| 29 | `project_post_mvp_prompt_improvements.md` #5 — multi-state regional default | ADDRESSED | §6 has the regional-preference table + multi-option pitch example |
| 30 | `project_post_mvp_prompt_improvements.md` #7 — calendar context block | ADDRESSED | §0 with explicit translation table |
| 31 | `project_test_scenarios_phase2.md` (1-10) — agent reasons over non-filter fields (rate, miles, weight, notes) | NOT-ADDRESSED | §6 mentions returning loads but doesn't explicitly tell agent "filter the 20-row set in-context by miles/weight/notes". Carrier ask "highest paying" or "under 30k pounds" or "TWIC required" has no §6 instruction |
| 32 | `project_field_renames_pending.md` — `apply_rate` not `agreed_rate` | ADDRESSED | §9 + §14 use `apply_rate` |
| 33 | `project_field_renames_pending.md` — `original_rate` (Extract) | NO-LONGER-PROMPT-RELEVANT | Bookings table writes `original_rate`; prompt doesn't speak to it |
| 34 | `project_mvp_scope_locked.md` — multi-option pitch when carrier vague | ADDRESSED | §6 example "Atlanta to Charlotte at $850 …, or Memphis to Nashville at $620…" |
| 35 | `reference_hr_create_popup_schema.md` — Transfer Popup as warm handoff | NOT-ADDRESSED-IN-PROMPT | v3 §10 speaks the spec-literal wording then expects "the Transfer Popup integration fires; the call ends" — relies on workflow wiring, not prompt. Confirm Popup node exists in v15 wiring before publish |
| 36 | `reference_hr_twin_empty_string_filter.md` — empty string is literal in Twin filters | NOT-PROMPT-RELEVANT | Tool-config concern |
| 37 | `feedback_diagram_principles.md` — diagrams stay logic-only | NOT-PROMPT-RELEVANT | Output-format guidance for `docs/` |
| 38 | FDE spec §"verify carrier eligibility" | ADDRESSED | §4 7-check AND-gate covers all FMCSA columns |
| 39 | FDE spec §"transfer when agreed" | ADDRESSED | §10 mock literal; §9 fires `book_load` BEFORE transfer wording |
| 40 | FDE spec §"if they make a counter offer evaluate it" | ADDRESSED | §8 explicit |
| 41 | `docs/v15-architecture-2026-04-27.md` §4 — verbal-filler during `book_load` ~500ms-1s | ADDRESSED | §9.2 lists 3 example fillers |
| 42 | `docs/v15-book-load-tool-spec.md` — UNIQUE(call_id, load_id) idempotency | ADDRESSED | §9.6 hard NEVER #4 names "(call_id, load_id) idempotency key" |
| 43 | `docs/v15-book-load-tool-spec.md` Scenario 6 — ambiguous yes must NOT fire | ADDRESSED | §9.1 explicit "NOT 'uh-huh', NOT 'sure I guess', NOT silence"; ask one short confirm |
| 44 | `docs/v15-book-load-tool-spec.md` Scenario 7 — book_load must NOT fire after FMCSA fail | ADDRESSED | §9.6 hard NEVER #1 |
| 45 | `feedback_anti_jailbreak_negotiation.md` — never reveal floor/discount math | ADDRESSED | §8.5 #3 + §12 anti-injection |
| 46 | `project_post_mvp_format_discipline.md` — defense in depth (tool desc + Extract + DDL + API) | NOT-PROMPT-RELEVANT | Cross-layer concern; the prompt-side surface is in items 12-16 above |
| 47 | `project_post_mvp_self_reflection_column.md` | NOT-ADDRESSED | Post-MVP only — no prompt action needed |
| 48 | `project_post_mvp_agentic_orchestration.md` | NOT-ADDRESSED | Post-MVP only — single-prompt architecture is correct for MVP |

---

## Section 3 — Punch list (add to v3 immediately)

Ordered by importance. Each item names the source memory and the v3 §-target.

1. **§6 — non-lane reasoning rule** (source: `project_test_scenarios_phase2.md`). Add 2 bullets after the multi-state paragraph: (a) "When carrier specifies a non-lane attribute (rate threshold, weight cap, miles cap, hot/TWIC/lumper notes, commodity, equipment-detail), call `search_loads_by_lane` with lane-only filters, then reason over the returned rows in context to pick the best match. Don't fabricate a tool filter that doesn't exist." (b) "If no returned row matches the non-lane criteria, name the gap honestly + offer the 2-3 closest options." This unblocks the 10 Phase-2 test scenarios that v3 currently doesn't anchor.

2. **§5 — active-narrowing instruction** (source: `project_post_mvp_prompt_improvements.md` #2 + #6). When the carrier is vague along ≥2 dimensions, the agent should ask 1-2 narrowing questions BEFORE firing search, not search-and-widen. Add one paragraph after §5's "Origin from utterance ONLY" block: "If the carrier is vague along 2+ dimensions (no equipment + no destination, or no pickup-window + no rate sense), ask 1-2 short narrowing questions before searching. One narrow tool call beats three wide ones."

3. **§8.3 — soften the hardcoded 80%-lowball threshold** (source: `feedback_intent_over_hardcoded.md`). v3 §8.4 currently says "If carrier's counter is below 80% of L (lowball signal), HOLD firm." Replace with intent: "If the carrier's counter is well below the listed rate without engagement on the load, treat as testing — hold firm and pivot to portfolio if any." Trust the LLM to recognize "well below" without the magic number.

4. **§9 / §10 — non-booking terminal-state coverage** (source: `project_call_end_tool_pattern.md`, gap noted in this audit). v3 has `book_load` as the terminal tool for the booked branch only. The non-booked terminals (FMCSA decline, walk-away after R3, no-match after relaxations, off-topic third strike, 2+ injection attempts) currently end with "decline politely / end politely" — but no structured-state capture happens at the agent's decision moment. Add one paragraph at top of §10 (or new §10.5): "On any non-booking terminal state, speak the polite close natively (don't read a tag aloud), then stop. Post-call extraction reads the transcript to assign `call_outcome`." This makes explicit that the LLM's job is to deliver the outcome reason verbally cleanly enough that the post-call Extract can classify it.

5. **§3 — explicit canonical-format example for `find_available_loads`** (source: `feedback_tool_param_normalization.md`). v3 §6 says "preserve exact casing" but doesn't echo the LOAD-NNNN canonical or 4-6 carrier-speech mappings the way `book_load` does in `docs/v15-book-load-tool-spec.md`. Add a 4-bullet mapping table in §6 under `find_available_loads`: "load 1" → `LOAD-0001`; "load forty-two" → `LOAD-0042`; "L-O-A-D dash zero one nine two" → `LOAD-0192`; "the first one you mentioned" → use the canonical id from your prior pitch, never invent.

6. **§14 — pickup-datetime-must-be-future invariant** (source: §0 already says "If computed datetime is older than `Time.Now`, recompute" — fine). Reinforce in §14 final reminders: explicit bullet "Never pass a past pickup_datetime to `search_loads_by_lane`. If carrier-stated time computes to past, ask one clarifier."

7. **§7 — equipment-mismatch escalation** (source: edge-case enumeration). v3 §5 says "If their equipment doesn't fit, tell them honestly." Doesn't say what happens next: end the call? offer email-back? In §5 add: "If the carrier's equipment isn't in our 5 supported types, decline politely + suggest they call back when they have a supported trailer. Tag: NOT_OUR_EQUIPMENT (post-call)."

8. **§8.6 — round counter reset on portfolio pivot must be explicit** (already in v3, double-check — confirmed present, low priority polish: tighten wording from "Reset round counter to 1" to "Counter resets to 1 on every portfolio pivot AND on every new load brought up by carrier mid-call.").

---

## Section 4 — Tier-2 wishlist (post-MVP)

| Source | Enhancement | Trigger to revisit |
|---|---|---|
| `project_post_mvp_agentic_orchestration.md` | Module Change → Receptionist + Search + Negotiation specialists | After ≥30 stable MVP calls |
| `project_post_mvp_format_discipline.md` | Versioned `docs/format-contracts.md` + DDL CHECK + API validators | When dashboard reveals first format drift OR before Phase 7 polish |
| `project_post_mvp_field_design_research.md` | 4 sub-agent goliath researching enum vocabularies (TIA, DAT, FreightWaves) | After MVP demo accepted; fork next workflow version |
| `project_post_mvp_self_reflection_column.md` | `improvement_signal` Twin column generated by post-call CHS | After ≥50 production calls so the rubric tunes against real failures |
| `project_post_mvp_prompt_improvements.md` #4 — re-review search architecture (Option 3a/3b/1/4) | Phase 5 dashboard build OR if load-count > 500 |
| `project_test_scenarios_phase2.md` Tier-2 | Add `gte`/`lte` operators to Twin Read for pickup_datetime / rate / miles | If 20-row in-context filtering proves insufficient |
| `feedback_intent_over_hardcoded.md` (extension) | Replace §8.4's `~3%`, `5-7%` band hints with a sentiment+urgency-driven micro-tactics block | Same trigger as the agentic-orchestration pivot |
| `project_call_end_tool_pattern.md` (extended) | `finalize_call` non-booked terminal tool | If post-call extract shows transcript-only outcome assignment is noisy |
| `reference_hr_create_popup_schema.md` (full config) | Promote Transfer Popup from MVP-minimum (phone_number) to fuller config (transfer_summary + location + transcript + data fields) | Phase 7 deliverables polish |
| `project_post_mvp_prompt_improvements.md` #5 — pre-emptive multi-state search | When latency budget allows 3 sequential search calls (~1.5s) OR Python pre-step lands |

---

## Section 5 — Conflicting guidance flags

1. **MVP scope locked vs spec-is-the-bible** — `project_mvp_scope_locked.md` (2026-04-26) says "negotiate_evaluate is post-MVP." `feedback_spec_is_the_bible.md` (2026-04-27) overrides: spec mandates 3-round negotiation, so it's MVP. **Follow:** `feedback_spec_is_the_bible.md`. v3 §8 already complies. **Action:** prune the scope-locked memory's "post-MVP" line during pruning pass.

2. **Phase 3 calls_log v2 (Classify nodes) vs v14 single CHS node vs v15 two-table** — three successive architectures. v3 prompt is silent on which post-call chain runs (correct — that's wiring not prompt). **Follow:** `docs/v15-architecture-2026-04-27.md` for wiring; v3 prompt doesn't conflict.

3. **`pitched_loadboard_rate` vs `original_rate` vs structurally-bound from Twin row** — three sources of truth in flight. `project_field_renames_pending.md` says "rename done in Extract; Twin column rename DEFERRED." `project_post_mvp_field_design_research.md` says "should ideally bind from Twin row not transcript." **Follow:** v15 spec — `bookings.original_rate` is written by `book_load` tool param (structural), not Extract. v3 prompt doesn't speak to this — correct.

4. **Round band specifics (`L − ~3%`, `L − 5%-7%`, F)** vs **intent-over-hardcoded** — minor self-conflict inside v3 §8.4. **Follow:** intent rule; soften §8.4 to band hints as illustrative not prescriptive (see Punch list #3).

5. **§9.1 booking precondition #4 ("clean yes" required)** vs **§8.5 hard rule #6 ("Carrier accepts then renegotiates → treat as new round")** — both correct but adjacent. Worth a one-line cross-reference in §9.1 — "If carrier renegotiates after a clean-seeming yes, do NOT fire `book_load`; loop back to §8 round logic." Low-severity polish.

6. **`call_outcome` enum** — `feedback_analytics_friendly_enums.md` lists 4-tag MVP (`load_booked / no_match / carrier_not_qualified / call_abandoned`); v3 emits richer in-call tags (`MC_NOT_FOUND`, `NOT_AUTHORIZED`, `OUT_OF_SERVICE`, `LIKELY_BROKER`, `NOT_A_CARRIER`, `IDENTITY_MISMATCH`, `NOT_DOMESTIC_CARRIER`, `NO_MC_PROVIDED`, `FMCSA_LOOKUP_FAILED`, `DECLINED_NO_AGREEMENT`, `NO_MATCH`). v3's tags are the *failure-reason* enum (closer to `fmcsa_eligibility_failure_reason`), not `call_outcome`. **Follow:** keep both but rename in §3 + §4 + §6 + §8 from "Tag:" to "Failure reason:" so it's clear those are eligibility-failure / decline-reason tags, distinct from the 4-tag `call_outcome`. Avoids the §B audit confusion.

---

## Section 6 — No-longer-relevant items to PRUNE from memory

| Memory entry | Reason | Recommended `MEMORY.md` action |
|---|---|---|
| `project_v14_loop_architecture.md` | v14 architecture explicitly superseded by v15 (per ADR-005, `docs/v15-architecture-2026-04-27.md`) | Mark in `MEMORY.md` index as `(SUPERSEDED — v15 replaces; kept for context only)`; do NOT delete (audit trail) |
| `project_call_end_tool_pattern.md` (booking branch) | `book_load` is the terminal tool for booking. Remaining value is the non-booking branch — keep the memory but annotate "booked branch resolved by §9" | Annotate with link to v3 §9 |
| `reference_hr_post_call_webhook_schema.md` (Version 3) | v3 webhook architecture replaced by Twin Write-to-Twin chips. Field catalog still useful as a checklist | Annotate "Version 3 architecture; v15 uses Twin direct write — field catalog still valuable as inspiration" |
| `project_phase3_calls_log_v2.md` (24-col plan) | Schema partially superseded by v15 two-table split (calls_log lost per-load fields to bookings) | Annotate "calls_log shape REVISED in `docs/v15-architecture-2026-04-27.md` §3.2" |
| `project_mvp_scope_locked.md` (negotiate_evaluate post-MVP line) | Overridden by `feedback_spec_is_the_bible.md` 2026-04-27 | Annotate "negotiate_evaluate moved to MVP critical path per spec" |
| `project_field_renames_pending.md` | Renames done in Extract + v15 spec — only DDL/API grep-replace pending | Annotate "Extract done; Twin DDL + dashboard code remain" |
| `feedback_engagement_style.md` / `feedback_closing_section_format.md` / `feedback_auto_accept_summary.md` / `feedback_terse_step_cues.md` / `feedback_proactive_memory_save.md` / `feedback_user_time_vs_claude_time_scope.md` / `feedback_analytical_foundation_before_dashboard.md` / `feedback_document_decisions.md` / `feedback_references_org.md` / `feedback_activity_log.md` / `feedback_hr_platform_manual.md` / `feedback_ask_clarifying_questions.md` / `feedback_ask_platform_questions.md` | Process / agent-engagement directives — not prompt-relevant | NO ACTION (out of scope for prompt audit) |

No memory file should be deleted — annotate via `MEMORY.md` index entries so the audit trail stays intact.

---

## Audit footer

- Total guidance items reviewed: **48** in Section 2 + **8** in Section 3 + **10** in Section 4 + **6** in Section 5 = **72**
- Status counts (Section 2): ADDRESSED 28, ADDRESSED-INDIRECTLY 1, PARTIALLY-ADDRESSED 5, NOT-ADDRESSED 5, SUPERSEDED 2, NOT-PROMPT-RELEVANT 7
- Punch-list items: **8** (all small additions/clarifications, no architectural rework)
- Conflicts: **6** (all resolvable with text-level edits or annotations)
- Memory items to annotate: **6** (no deletions)

v3 is in strong shape. The dominant gap is **non-lane in-context filtering** (Punch #1) — the 10 Phase-2 test scenarios cannot pass without it. Second-largest is **active narrowing** (Punch #2). Everything else is polish.
