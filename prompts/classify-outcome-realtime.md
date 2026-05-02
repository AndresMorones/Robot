---
title: Real-time Call Outcome Classifier
hr_node: Inbound Voice Agent → Real-time Classifier (Call Outcome)
workflow: inbound-carrier-v4
last_synced: 2026-04-25
classes: 8 (BOOKED, CARRIER_DECLINED_RATE, CARRIER_DECLINED_UNAVAILABLE, BROKER_DECLINED_INELIGIBLE, BROKER_DECLINED_NO_MATCH, NEGOTIATION_STALLED, CALLBACK_SCHEDULED, ABANDONED)
---

> Runs every turn during the live call. Output drives potential mid-call branching (none active in MVP) and is also captured post-call for cross-validation against the post-call Classify Outcome node.

## Prompt body

Classify the current call outcome based on how the conversation is progressing. Determine which of the following best describes the state of this call in real time. Pick exactly one tag.

## Class definitions

- **BOOKED** — The carrier has agreed to book the load and the deal is confirmed. The agent has stated the agreed rate and is initiating transfer to dispatch.
- **CARRIER_DECLINED_RATE** — The carrier explicitly declined the load because the rate was too low for them. They named a number that's below what we'll accept, and explicitly walked away.
- **CARRIER_DECLINED_UNAVAILABLE** — The carrier declined because they're already loaded, no equipment available, the lane doesn't fit them, or they need a different commodity / pickup date than what's on offer.
- **BROKER_DECLINED_INELIGIBLE** — The agent declined the carrier on FMCSA eligibility grounds (inactive MC, no authority, out-of-service, broker authority, etc.). The decline came from our side, not the carrier's.
- **BROKER_DECLINED_NO_MATCH** — The agent could not find a load matching the carrier's lane and equipment requirements. Inventory mismatch.
- **NEGOTIATION_STALLED** — The carrier and agent went through multiple rounds of counter-offering without reaching agreement, and the conversation broke down without explicit acceptance or decline.
- **CALLBACK_SCHEDULED** — The carrier requested a callback or the agent offered one for follow-up; phone number was captured. Either due to no current load match, compliance flag review, or a future load opening.
- **ABANDONED** — The call dropped, the caller hung up prematurely, there was technical failure, or no meaningful conversation took place (e.g., dead air, immediate disconnect).
