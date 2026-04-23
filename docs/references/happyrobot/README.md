# HappyRobot Platform Reference Documentation

This directory contains comprehensive research on the HappyRobot AI voice-agent platform, tailored for Andres's inbound-carrier freight-broker workflow implementation.

## File Index

| File | Purpose | Audience |
|------|---------|----------|
| **platform-concepts.md** | Core mental models: DAG workflows, immutable-publish, web-call triggers, AI-worker framing | Foundation; read first |
| **node-taxonomy.md** | Complete node type catalog with config fields, inputs/outputs, use patterns | Reference during build |
| **voice-agent-prompting.md** | Prompt-engineering patterns for US freight carriers; few-shot examples | Prompt engineering; carrier persona |
| **tool-calls/README.md** | Tool-call node overview and general patterns | Reference |
| **tool-calls/patterns.md** | Auth headers, timeout/retry semantics, variable mapping syntax, error handling | Technical integration |
| **webhooks/call-ended.md** | How HR fires `call.ended`, payload shape, auth, idempotency expectations | Webhook integration |
| **post-call-extraction.md** | HR's post-call LLM pass; forcing JSON schema output; handling malformed responses | Call data extraction |
| **transfer-mock.md** | Transfer node config for graceful mock call endings (no real SIP) | Call ending patterns |
| **testing.md** | HR test console, simulating calls, execution logs, quota implications | QA & testing |
| **gotchas.md** | 10-min duration cap, latency budgets, analytics UI restriction, quota traps | Pitfalls to avoid |
| **design-notes-for-our-workflow.md** | Concrete `inbound-carrier-v1` node graph recommendation with explicit HR UI references | **Start here when building** |

## Suggested Reading Order

1. **design-notes-for-our-workflow.md** — understand the big picture and your exact node graph
2. **platform-concepts.md** — ground yourself in DAG thinking and immutable publishing
3. **node-taxonomy.md** — know what each node type does
4. **voice-agent-prompting.md** — craft your agent prompt for carriers
5. **tool-calls/patterns.md** — configure API calls to your FastAPI backend
6. **webhooks/call-ended.md** — understand the post-call data flow
7. **transfer-mock.md** — configure the call-ending transfer node
8. **post-call-extraction.md** — extract structured data from the call
9. **testing.md** — test without burning minutes
10. **gotchas.md** — review before you deploy

## Key Constraints for This Project

- **Call Duration**: 10-min hard cap (default if unspecified)
- **Voice-Call Trigger**: Inbound web-call URL from HR (no phone number purchased; caller dials a link)
- **Authentication**: Bearer token via `Authorization` header (with `?token=` query-string fallback to our FastAPI backend on Fly.io)
- **Workflow Model**: DAG with immutable published state; changes require republishing
- **Tool Calls**: Stateless API endpoints to our negotiation logic (3 rounds, each round returns next step)
- **Call Ending**: Mock transfer node (not real SIP) that gracefully ends the call
- **Post-Call Data**: HR's webhook fires `call.ended` with transcript/extraction; we persist via our API

## Important Notes

- **HR Docs are Gated**: The official `https://docs.happyrobot.ai` requires an access code. This research synthesizes publicly available HR blog posts, API docs, examples, and industry patterns.
- **Some Details Require Confirmation**: Marked as "Unclear from public docs — needs Andres to confirm in his HR workspace" where the gated docs might have more specifics.
- **Analytics UI Not Used**: Per the take-home requirement, we do NOT use HR's analytics UI for monitoring—our own logging layer handles that.

---

**Last Updated**: 2026-04-23  
**For**: Andres, inbound-carrier voice-agent freight-broker take-home project  
**Source**: [HappyRobot blog](https://www.happyrobot.ai/blog), [HappyRobot AI workers for logistics](https://www.happyrobot.ai/blog/ai-workers-for-logistics), [HappyRobot Technical Overview](https://www.happyrobot.ai/blog/technical-overview), search results for workflow patterns, freight-broker best practices.
