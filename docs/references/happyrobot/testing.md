# Testing HappyRobot Workflows

How to verify the workflow without making real phone calls, and how to debug when something misbehaves.

> **Platform-level references**:
> - Runs table + filters + custom columns + export → [happyrobot-kb/runs-ops/runs-monitoring.md](file:///C:/Users/Andre/happyrobot-kb/runs-ops/runs-monitoring.md)
> - Debugging (graph tab, tool-call inspection, quality flags) → [happyrobot-kb/runs-ops/debugging.md](file:///C:/Users/Andre/happyrobot-kb/runs-ops/debugging.md)
> - Custom evals + northstars (eval-gated publish patterns) → [happyrobot-kb/quality/custom-evals.md](file:///C:/Users/Andre/happyrobot-kb/quality/custom-evals.md), [northstars.md](file:///C:/Users/Andre/happyrobot-kb/quality/northstars.md)
> - Adversarial suites for red-team regression → [happyrobot-kb/quality/adversarial.md](file:///C:/Users/Andre/happyrobot-kb/quality/adversarial.md)

## Test console (workflow-level)

HR provides a **Test** tab on each workflow. This is how you validate the workflow before publishing, and how you can simulate calls afterward.

### Per-node testing (required before publish)

- On each node (agent, tool-call, condition), click **Test**.
- For tool-call nodes: provide a sample JSON body; HR fires the request, shows the response, and infers the output schema.
- For agent nodes: HR may simulate an utterance or let you preview the initial message.
- For condition nodes: test with sample input variables; verify the branch taken matches expectation.

**This is not optional**. If any node hasn't been tested, the workflow typically refuses to publish with an orange-exclamation indicator.

### Full-workflow web-call test

Once published:
- Open the web-call trigger URL in a browser. HR serves a WebRTC client. Click "Start call."
- Speak to the agent. It runs the full workflow.
- Watch the HR **execution log** panel (usually available in the platform UI) for per-node status + variable values.

This **does** consume a real call-minute (platform-tier dependent). For iterative testing, prefer HR's **Chat Playground** (text-only, no audio, no minute cost — exercises the Prompt + tool logic without STT/TTS/turn-taking), and use full web-call tests sparingly. The `negotiate_evaluate` Python Code sidecar can be unit-tested with the Test button on the node itself (HR passes sample inputs).

## Tailing our API logs during a test

```
fly logs -a robot-api
```

Every tool-call request shows as a structured-JSON log with `request_id`, `call_id` (HR passes this if we configure body mapping), event name, duration. Grep by `call_id` to reconstruct a single call's tool-call sequence.

## Verifying the `call.ended` webhook lands

After hanging up:
1. HR runs post-call extraction (a few seconds).
2. HR POSTs to our `/v1/calls/log`.
3. Our API logs `calls.log.received` with `call_id`, `outcome`.
4. The new record appears in `data/calls.json` (on Fly, under `/data/calls.json`).
5. Dashboard's `/v1/dashboard/*` endpoints reflect it on next fetch.

Failure modes to check:
- No `calls.log.received` log → webhook didn't fire. Check HR config (URL, auth). Check Fly is up.
- Log shows 401/403 → auth mismatch. Verify `API_BEARER_TOKEN` matches between HR secret and Fly secret.
- Log shows 422 → post-call extraction produced invalid JSON. Read the request body; iterate extraction prompt.
- Log shows 200 but `data/calls.json` didn't update → file-lock or write error. Check Fly volume mount.

## Avoiding real-call quota burn

- Use HR's **Chat Playground** for prompt iteration — no audio, no minute cost, exercises the tool logic end-to-end.
- Click **Test** on every node individually before running a full web call.
- Unit-test the Extract JSON schema offline: feed sample transcripts to a local LLM with the same prompt, verify JSON matches our strict schema. Saves HR minutes.
- Only use full web-call test at the end of a change + for the demo video.

## Debugging tips

### HR variable resolution silently fails → "Missing mc_number parameter" style errors
- Symptom: tool fires with a variable reference in its URL/body but HR's webhook layer returns `{"error":"Missing X parameter"}`, even though the upstream tool extracted the value correctly.
- Root cause: the variable reference uses a name (`{{trigger.x}}`, `{{verify_carrier.x}}`) or lacks a group_id prefix (`{{mc_number}}`). Those silently render as empty string at runtime.
- Fix: delete the existing variable reference; re-insert it using HR's `@` picker. HR inserts the correct `{{<persistent_id_uuid>.var}}` form automatically.
- Verify: click the variable chip/token in the field → HR shows what it's bound to. Should point at a specific upstream node output, not a placeholder.

### "The agent sounds slow / awkward pauses"
- Check tool-call latencies. `verify_carrier` (HR demo FMCSA) typically ~300ms. Our `/v1/loads/*` endpoints target <50ms. `negotiate_evaluate` Python Code is in-platform (<100ms).
- Check the system-prompt length — > 800 tokens and responsiveness degrades.

### "The agent didn't follow instructions"
- Check the system prompt is up-to-date in HR (did you republish after editing?).
- Try few-shot transcripts — LLMs anchor hard on examples.
- Check if the condition node routed correctly — its config is often the culprit when the agent "skips" a step.

### "Webhook fires but dashboard doesn't update"
- Step through: HR log → our API log (`fly logs`) → `/data/calls.json` on Fly → `/v1/dashboard/funnel` response. The break point is where the record first becomes invisible.

## Unresolved / needs confirmation

- **Whether HR's Test tab supports fully text-mode call simulation** (no audio) — would be ideal for rapid iteration. Some voice platforms have this; HR's status unconfirmed.
- **Call-minute quota on your HR tier** — Andres should check his plan before running 50 iterative voice tests.
- **Whether published-workflow test runs use a different quota bucket** than live traffic.
