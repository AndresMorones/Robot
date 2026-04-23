# Transfer Node — Mock Configuration

Per the take-home spec, transfer is explicitly allowed to be mocked:

> "Transfer is out of scope as it won't work with the web call, you can mock a message like 'Transfer was successful and now you can wrap up the conversation'."

So our transfer node doesn't call real SIP. It says a short "connecting you" line and ends the call gracefully.

## Configuration

**Node type**: Transfer (or Agent node with an end-call exit — see "two ways to implement" below).

**Our chosen pattern** (simplest): use an **Agent node with a single utterance + exit-on-completion**, not a real Transfer node. Reason: a real Transfer node with "mock" destination may try to dial and fail with an error shown in the call log. An Agent node that just speaks a line and ends the call produces clean log output.

**Alternative** (if your HR workspace exposes a "mock" or "disconnect" transfer mode): use the Transfer node with that mode set.

## Agent-node mock config

- **System prompt**: `"Say exactly: 'Great, I've got everything I need. I'm connecting you now to our dispatch team to finalize the paperwork. Please hold for a moment.' Then stop speaking and exit this node."`
- **Initial message**: (leave empty — the system prompt drives it)
- **Voice**: same as the main agent (continuity)
- **Extracted variables**: none
- **Exit condition**: "after single utterance complete" or similar — look for a "say-and-end" or "one-shot" option

After this Agent node, the workflow should reach a terminal state. HR ends the call. The `call.ended` webhook fires. Our API records `outcome: TRANSFERRED_TO_REP` (or `BOOKED` if the BOOKED→transfer path; the post-call extraction disambiguates via transcript).

## What the HR call log shows

A mock transfer through an Agent-node produces a clean log with:
- Final agent utterance
- Normal call-end status
- Duration recorded
- No failed-dial error

A mock transfer through an actual Transfer node with a dummy SIP URI may produce:
- Transfer-attempted status
- Potentially a "transfer failed" error
- Still fires `call.ended` afterwards

**For the demo video**: the Agent-node approach is cleaner. For the broker build doc, we document honestly: "transfer is wired at the workflow level as a graceful end-call; real SIP transfer is out of scope for the take-home demo but would slot into the same workflow position."

## Real-transfer-in-production path (noted for the broker doc)

If Acme Logistics wanted real SIP transfer in production:
- HR supports SIP-based transfer via their SIP gateway (Twilio / Telnyx / direct trunk).
- We'd configure a Transfer node with a real SIP URI or phone number.
- Warm vs cold transfer is a node-level setting.
- No code changes on our side — purely an HR config change.

This is worth a paragraph in the broker doc's "what we'd do with another sprint" section.

## Unresolved / needs confirmation

- Whether HR's Transfer node has a built-in "mock" or "end-call-gracefully" mode that does what we want without using an Agent node.
- Whether the Agent-node approach actually triggers the `call.ended` webhook the same way — test on first build.
