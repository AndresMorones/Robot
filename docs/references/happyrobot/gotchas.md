# HappyRobot — Gotchas & Pitfalls

Things that'll bite you if you don't know. Skim before building; re-skim before publishing.

## Platform mechanics

### Published workflows are immutable
- Once you hit **Publish**, you cannot edit nodes. To change a node, click **Stop**, edit, **Publish** again.
- Stopping a workflow may interrupt in-flight calls (behavior unconfirmed — don't stop during a demo).
- For material changes, create `inbound-carrier-v2` instead of stop-edit-republish. Preserves the v1 call log uncorrupted.

### 10-minute call duration default
- Calls default to a 10-minute hard cap.
- Configurable per workflow, but longer calls cost more and user attention degrades.
- For our flow (greet → verify → search → pitch → negotiate × 3 → close), target < 5 minutes.
- If a call approaches the cap, the agent should wrap: "Let me call you back to finish this."

### Tool-call timeout budget is tight
- HR's default tool-call timeout is often 10s — way too long for conversational flow.
- **Set to 2500 ms**. Beyond 3s of silence the agent sounds broken to the carrier.
- Our API must hit p95 < 1500 ms on every endpoint; we alert on regressions.

### Workflow test tab is required
- Every node must be tested before publish (defines output schema for downstream).
- Untested nodes surface orange exclamation marks and block publish.

## Auth + secrets

### Secrets in HR are workflow-scoped
- `API_BEARER_TOKEN` is stored as an HR workflow secret, referenced via `{workflow_secret:API_BEARER_TOKEN}` in headers/URLs.
- Secret is scoped to the workflow; if you duplicate the workflow to create `-v2`, the secret doesn't auto-copy. Re-add it.
- Secrets are never shown back in plaintext after saving. If you lose the value, rotate (generate new, update both HR + Fly).

### Bearer header support is tier-dependent (rumored)
- Some HR tiers may not expose custom `Authorization` header config on tool-call nodes.
- Our API accepts `?token=` as a fallback for this reason. Test on your tier on first tool-call node.
- If forced to fallback, rotate the token faster (URL-based tokens leak into logs more easily).

### No HMAC webhook signing
- HR's `call.ended` webhook is Bearer-auth only, not HMAC-signed.
- We can't cryptographically verify the caller is HR. Mitigations: idempotency by `call_id`, token rotation, monitoring for anomalous `call.ended` volumes.

## Data + analytics

### "We're NOT allowed to use HR's analytics UI"
- Take-home requirement: do not use HR's built-in analytics dashboard. Build our own.
- Our dashboard reads from `data/calls.json` via `/v1/dashboard/*`. Completely independent of HR.
- This is a scoring signal — the take-home wants to assess our product vision, not rebrand HR's UI.

### Recording URLs are pre-signed + expiring
- HR returns recording URLs as pre-signed cloud-storage URLs.
- These expire (duration unconfirmed — possibly 24h, possibly 7 days).
- If our dashboard links to them, the drilldown must handle expired-URL state gracefully (show "recording archived" instead of broken link).
- For the take-home, fresh recordings from the demo period will work. For a real production use, mirror to our storage.

### Transcript quality: online vs offline-enhanced
- HR provides both an online (real-time, slightly worse) and offline-enhanced (post-call, better) transcript.
- The post-call extraction runs on the offline transcript. Use that version in `transcript_summary`.

## Voice / audio

### Voice selection affects perception
- HR offers 100+ voices. Pick a US-English voice appropriate for freight-broker tone (professional, warm, slight casualness). Avoid overly-robotic or overly-soft voices.
- Preview voices in HR's Voice Playground before committing.

### Interruption handling
- HR's voice-agent pipeline handles interruptions, but the agent's response to interruption is prompt-dependent. Your system prompt should explicitly say "yield immediately if interrupted."

## Versioning hygiene

### No native version UI
- HR doesn't have a built-in "v1/v2/v3 switcher" for workflows.
- Use naming convention: `inbound-carrier-v1`, `inbound-carrier-v2`, etc.
- Maintain `docs/references/happyrobot/changelog.md` recording: date, version, what changed, why.
- Old versions' call data still flows into our `/v1/calls/log`. Our `agent_metadata.workflow_version` field distinguishes them.

## Latency + reliability

### FMCSA cold-cache is the tightest latency pinch
- First call to `fmcsa_verify` for a new MC has to hit QCMobile (200–500ms typical, up to 2s if FMCSA is slow).
- HR's tool-call timeout is 2500ms. Very little margin.
- **Mitigation**: on API startup, pre-warm the cache with the top ~20 MCs we've seen historically. (Implement in `api/app/services/fmcsa_client.py` when we build that service.)

### Don't autoscale Fly beyond 1 machine
- Our `calls.json` lives on a Fly volume mounted to one machine. Multiple machines = split-brain writes.
- Set Fly autoscaling to max 1. Scale via Postgres migration if/when we outgrow the JSON store (future-sprint item).

## Submission-specific

### Carlos Becker expects an email
- Final deliverable is an email to Carlos Becker (`c.becker@happyrobot.ai`) with recruiter in cc.
- Draft in `docs/submission-email.md`; don't send without human review.
- Subject line + first sentence are what gets read — everything else is skim territory.

### Video must be ≤ 5 minutes
- The take-home specifies 5 minutes. Hard cap.
- Don't exceed 5:30. Record a dry run first; budget 2 real takes.

## Unresolved / needs confirmation

Most of the above has "confirm in your HR workspace" flags — platform-specific behavior isn't fully public-documented. Treat this file as a working set of hypotheses that Andres validates on first real-call testing.
