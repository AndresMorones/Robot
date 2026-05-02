---
title: Real-time Carrier Sentiment Classifier
hr_node: Inbound Voice Agent → Real-time Classifier (Carrier Sentiment)
workflow: inbound-carrier-v4
last_synced: 2026-04-25
classes: 4 (positive, neutral, negative, frustrated)
---

> Runs every turn during the live call. Output is consumed by the system prompt's Step 4 (Negotiation) to drive persona selection. Specifically, sentiment=`frustrated` shifts the agent's persona toward EMPATHETIC for de-escalation.

## Prompt body

Classify the overall sentiment of the **CARRIER** (not the agent) during this call in real time. Focus on the carrier's tone, word choice, and emotional state as the conversation unfolds. Pick exactly one tag.

## Class definitions

- **positive** — The carrier is friendly, enthusiastic, cooperative, or expresses satisfaction with the rate / process / agent. Examples: laughing, agreeing readily, expressing willingness, using upbeat language.
- **neutral** — The carrier is businesslike and matter-of-fact, with no strong positive or negative emotion. They're transactional — focused on getting the load, exchanging information factually. This is the default and most common sentiment in carrier calls.
- **negative** — The carrier expresses displeasure, annoyance, or dissatisfaction with the rate, process, or outcome. They may push back firmly, complain about market conditions, or sound disappointed.
- **frustrated** — The carrier shows clear frustration — raises objections repeatedly, expresses impatience, becomes confrontational, may use elevated tone or curt language. This is escalation territory: the agent should de-escalate (shift to EMPATHETIC persona) or risk losing the call entirely.
