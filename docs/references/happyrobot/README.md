# HappyRobot Platform Reference

Working notes Andres uses while building the inbound-carrier voice-agent workflow in the HappyRobot UI. The voice-agent system prompt and post-call extraction prompt — both pasted into HR — are versioned here.

## Files

| File | Purpose | When to read |
|---|---|---|
| **design-notes-for-our-workflow.md** | The 15-step build guide for `inbound-carrier-v1` (incl. tool-call patterns, transfer mock, `call.ended` webhook spec) | When you sit down to build the workflow |
| **voice-agent-prompting.md** | Voice-agent system prompt design + few-shot transcripts + the post-call extraction prompt template | When configuring agent nodes + the post-call setting |
| **platform-essentials.md** | Platform concepts (DAG / immutable-publish / web-call trigger), node taxonomy, gotchas | First-time skim; reference during build |
| **testing.md** | Test console workflow, debugging during development | When something doesn't work |
| **README.md** | This index | First-time orientation |

## Suggested order

1. **platform-essentials.md** — get the mental model (~15 min)
2. **design-notes-for-our-workflow.md** — the build sequence (~20 min skim, hours during build)
3. **voice-agent-prompting.md** — the prompts you'll paste
4. **testing.md** — when iterating

## Source caveats

Some HR platform behavior wasn't fully resolvable from public docs (tool-call header support per tier, exact variable-substitution syntax, JSON-mode on post-call LLM, payload nesting on `call.ended`). These are flagged inline as "Unresolved — confirm in your workspace." Validate on first real-call testing and update these docs.
