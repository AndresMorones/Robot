# HappyRobot — Tool Calls

Tool-call nodes are the synchronous HTTP bridge between the HR voice agent and our FastAPI backend. During a call, when the agent decides to invoke a tool, HR makes an HTTP request to a configured URL, waits for the response, and passes response fields forward as variables.

## Files in this directory

| File | Purpose |
|---|---|
| [README.md](./README.md) | This index |
| [patterns.md](./patterns.md) | Auth headers, timeout/retry, variable mapping syntax, error handling |

## Our four tool calls (summary)

| Tool-call node | Method | Endpoint | When invoked |
|---|---|---|---|
| `fmcsa_verify` | POST | `/v1/fmcsa/verify` | Right after MC capture |
| `loads_search` | POST | `/v1/loads/search` | Right after lane + equipment capture |
| `negotiate_evaluate` | POST | `/v1/negotiate/evaluate` | Each negotiation round (up to 3) |
| `calls_log` (post-call webhook, not a tool-call node) | POST | `/v1/calls/log` | After call.ended |

For the full node specs (exact headers, body templates, response parsing) see `patterns.md` and the per-tool docs that will be added on first configuration.
