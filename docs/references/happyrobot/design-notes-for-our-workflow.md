# Design Notes for `inbound-carrier-v1`

**Start here** when you're actually building the workflow in HR. This is the prescriptive file; everything else in this directory is descriptive reference.

## Prerequisites before building

- FastAPI deployed to Fly.io with endpoints live: `/v1/fmcsa/verify`, `/v1/loads/search`, `/v1/negotiate/evaluate`, `/v1/calls/log`.
  - Alternative: local API + ngrok tunnel during dev; swap URLs to Fly before publish.
- `API_BEARER_TOKEN` generated and stored in (a) Fly secret on `robot-api`, (b) HR workflow secret (add at workflow level before configuring any tool-call node).
- FMCSA webKey stored in Fly secret `FMCSA_WEB_KEY`.
- You've skimmed `platform-concepts.md` and `node-taxonomy.md`.

## Step-by-step workflow construction

### Step 1 — Create the workflow
1. HR platform → New Workflow → Name: `inbound-carrier-v1`.
2. Workflow Settings → Secrets → Add `API_BEARER_TOKEN` (paste the token value; store it safely in your password manager — HR won't show it back).
3. Workflow Settings → Post-Call → configure later (Step 10).
4. Workflow Settings → Webhooks → configure later (Step 11).

### Step 2 — Add Web-Call Trigger
1. Add node → Web-Call Trigger → Name: `inbound_web_call`.
2. Test the node → copy the auto-generated URL → save to `docs/references/happyrobot/web-call-url.txt`.

### Step 3 — Greeting + MC-capture agent
1. Add Agent node → Name: `greet_and_capture_mc`.
2. System prompt: paste the "Greeting + MC Capture" section from `.claude/skills/happyrobot-agent-prompt/SKILL.md`.
3. Initial message: `"Hi, this is Acme Logistics. May I have your MC or DOT number?"`.
4. Voice: pick US-English professional (preview in Voice Playground first).
5. Extract variable: `mc_number` (normalize to `MC-123456` format).
6. Tools available: (none at this step).
7. Exit condition: `mc_number` extracted.
8. Test with a sample utterance → confirm `mc_number` output.

### Step 4 — Tool call: `fmcsa_verify`
1. Add Tool-Call node → Name: `fmcsa_verify`.
2. URL: `https://robot-api.fly.dev/v1/fmcsa/verify`.
3. Method: POST.
4. Headers:
   - `Authorization: Bearer {workflow_secret:API_BEARER_TOKEN}`
   - `Content-Type: application/json`
   - **If your tier rejects custom Authorization headers**: remove the Authorization header and change URL to `https://robot-api.fly.dev/v1/fmcsa/verify?token={workflow_secret:API_BEARER_TOKEN}`.
5. Body:
   ```json
   {"identifier": "{{mc_number}}", "identifier_type": "MC"}
   ```
6. Timeout: 2500 ms. Retries: 1.
7. Test with a real MC from `data/fmcsa-fixtures/`: paste the body, hit Test. Confirm response JSON has `eligible`, `reason_codes`, `carrier_name`, `manual_review_required`.

### Step 5 — Condition: eligibility gate
1. Add Condition node → Name: `eligibility_gate`.
2. Expression: route on `{eligible}` and `{manual_review_required}`:
   - If `{eligible} == true AND {manual_review_required} == false` → continue to lane-capture (Step 6).
   - If `{eligible} == true AND {manual_review_required} == true` → go to callback branch (Step 8a).
   - Else → polite decline (Step 8b).
3. If HR doesn't support compound expressions, chain two conditions: first `{eligible}`, then `{manual_review_required}`.
4. Test with sample variable values.

### Step 6 — Lane + equipment capture agent
1. Add Agent node → Name: `capture_lane_equipment`.
2. System prompt: `.claude/skills/happyrobot-agent-prompt/SKILL.md` section "Lane & Equipment".
3. Extract variables: `origin_state`, `destination_state`, `equipment_type` (enum), `earliest_pickup` (date).
4. Exit condition: all 4 variables extracted (or carrier says "anywhere" → extract as null).

### Step 7 — Tool call: `loads_search`
1. Add Tool-Call node → Name: `loads_search`.
2. URL + method + headers: same pattern as Step 4; URL = `/v1/loads/search`.
3. Body:
   ```json
   {
     "origin_state": "{{origin_state}}",
     "destination_state": "{{destination_state}}",
     "equipment_type": "{{equipment_type}}",
     "pickup_after": "{{earliest_pickup}}",
     "max_results": 3
   }
   ```
4. Timeout 2500 ms, 1 retry.
5. Test with a sample matching the seeded `data/loads.json`.

### Step 7b — Condition: match gate
1. Expression: `{matches.length} > 0` or equivalent (HR may express this differently).
2. True → pitch + negotiation (Step 8). False → no-match branch (Step 8c).

### Step 8 — Pitch + negotiation loop

This is the most complex branch. Build carefully.

**8a. Pitch agent**
- Agent node → Name: `pitch_and_round_1`.
- System prompt: "Pitch Load" section.
- Pitches `{matches[0]}` — includes loadboard_rate.
- Extracts: `carrier_interested` (bool), `carrier_offer` (int, if carrier counter-offered).
- Sets `round_number = 1` as a workflow variable.

**8b. Tool call: `negotiate_evaluate`**
- URL: `/v1/negotiate/evaluate`.
- Body:
  ```json
  {
    "load_id": "{{matches[0].load_id}}",
    "round_number": "{{round_number}}",
    "carrier_offer": "{{carrier_offer}}",
    "prior_broker_offers": "{{prior_broker_offers}}"
  }
  ```
- Response fields used downstream: `action`, `broker_counter`, `should_transfer`.

**8c. Condition: action branch**
- `{action} == "ACCEPT"` → confirmation agent (Step 9).
- `{action} == "REJECT"` → outcome = CARRIER_DECLINED_RATE → end (Step 10).
- `{action} == "ESCALATE_HUMAN"` → transfer mock (Step 11b).
- `{action} == "COUNTER"` → deliver-counter agent (next).

**8d. Deliver counter agent**
- Agent node → Name: `deliver_counter_round_N`.
- System prompt: "Deliver Counter" section; reads `broker_counter` to the carrier.
- Extracts: new `carrier_offer` (carrier's response).
- Appends to `prior_broker_offers` list.
- Increments `round_number`.

**8e. Round-cap condition**
- `{round_number} > 3` → outcome = NEGOTIATION_STALLED → end (Step 10).
- Else → loop back to Step 8b.

### Step 9 — Booking confirmation agent
- Reached only on ACCEPT.
- Agent says "Deal at $X. Let me have dispatch send the BOL."
- Extracts: dispatch email / phone.
- Then → transfer mock (Step 11).

### Step 10 — Polite-decline / callback branches
- **8a callback**: agent captures callback name + number → routes to end.
- **8b polite decline**: agent says "I'm sorry, we can't work with you right now" (without revealing why) → routes to end.
- **8c no-match**: agent says "Nothing in your lane right now — can I take a callback?" → captures callback info → routes to end.

### Step 11 — Transfer mock
See `transfer-mock.md`. Implement as an Agent node that says "Connecting you now..." and exits.

### Step 12 — Post-call extraction
- Workflow Settings → Post-Call → paste the prompt from `post-call-extraction.md`.
- Test with a sample transcript if HR supports offline testing.

### Step 13 — `call.ended` webhook
- Workflow Settings → Webhooks → add `call.ended`.
- URL: `https://robot-api.fly.dev/v1/calls/log`.
- Headers: same auth pattern as tool calls.
- See `webhooks/call-ended.md`.

### Step 14 — Publish
- Verify every node shows green-checked (tested).
- Click Publish.
- Confirm the web-call URL still works by hitting it in a browser.

### Step 15 — Smoke test
- Make one real web-call end-to-end with a known MC.
- Watch `fly logs -a robot-api` in another terminal.
- Verify: FMCSA verify fires, loads search fires, at least one negotiate round fires, call.ended webhook lands, CallRecord appears in `data/calls.json`.
- Capture the transcript + webhook payload → save to `docs/references/happyrobot/smoke-tests/2026-MM-DD-<scenario>.md`.

## Post-build: run the hr-workflow-critic subagent

Once the workflow is published and smoke-tested, invoke the `hr-workflow-critic` subagent (when we add it) against all the `docs/references/happyrobot/` files + the published workflow. It'll flag gaps: missing fallback branches, transfer wiring, timeout config, auth header usage.

## Common first-build issues

1. **Tool-call headers reject**: if your tier blocks custom Authorization, pivot every tool-call node to the `?token=` query-string URL. Update all four nodes consistently.
2. **Variable syntax mismatch**: if `{{mc_number}}` doesn't substitute, try `{mc_number}` or `${mc_number}`. Check HR's docs for exact syntax in your workspace.
3. **Condition compound-expression fail**: if `A AND B` isn't supported, chain two conditions.
4. **Response-field mapping breaks**: always test tool-call nodes before wiring downstream conditions. The test run is what tells HR the response schema.
5. **Publish blocks on orange-exclamation node**: click through each node looking for the warning. Usually means a required field is empty or a test wasn't run.

## Versioning reminder

After any material change to this workflow post-publish, create `inbound-carrier-v2`. Don't try to stop-edit-republish v1 during live demo traffic. Record the change in `docs/references/happyrobot/changelog.md`.
