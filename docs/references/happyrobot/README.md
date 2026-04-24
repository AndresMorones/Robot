# HappyRobot Platform Reference

Working notes Andres uses while building the inbound-carrier voice-agent workflow in the HappyRobot UI. The two prompts pasted into HR (voice-agent system prompt + post-call extraction prompt) are versioned in their own files since they configure different parts of the HR UI.

## Files

| File | Purpose | When to read |
|---|---|---|
| **design-notes-for-our-workflow.md** | The 15-step build guide for `inbound-carrier-v1` (incl. tool-call patterns, transfer mock, `call.ended` webhook spec) | When you sit down to build the workflow |
| **voice-agent-prompt.md** | The system prompt that runs in each Agent node DURING the call: persona, structure, few-shots, guardrails | When configuring Agent nodes |
| **post-call-extraction-prompt.md** | The prompt that runs AFTER the call ends, emitting our `CallLogRequest` JSON | When configuring the workflow-level Post-Call setting |
| **platform-essentials.md** | Platform concepts (DAG / immutable-publish / web-call trigger), node taxonomy, gotchas | First-time skim; reference during build |
| **testing.md** | Test console workflow, debugging during development | When something doesn't work |
| **README.md** | This index | First-time orientation |

## Suggested order

1. **platform-essentials.md** — get the mental model (~15 min)
2. **design-notes-for-our-workflow.md** — the build sequence (~20 min skim, hours during build)
3. **voice-agent-prompt.md** — the in-call prompt you'll paste into Agent nodes
4. **post-call-extraction-prompt.md** — the after-call prompt you'll paste into Post-Call setting
5. **testing.md** — when iterating

## Source caveats

Some HR platform behavior wasn't fully resolvable from public docs (tool-call header support per tier, exact variable-substitution syntax, JSON-mode on post-call LLM, payload nesting on `call.ended`). These are flagged inline as "Unresolved — confirm in your workspace." Validate on first real-call testing and update these docs.
