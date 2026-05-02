# HappyRobot docs sitemap

This file is superseded by the full-platform knowledge base at `C:\Users\Andre\happyrobot-kb\` (outside the repo, vendor-docs mirror + topic-sharded reference + searchable via `topics:` frontmatter tags).

**Start any platform lookup at** [happyrobot-kb/MANIFEST.md](file:///C:/Users/Andre/happyrobot-kb/MANIFEST.md) — it has the file index, topic-tag inverted index, and a verb-first "Where do I find…" quick-lookup table.

## Companion anchors at the KB root

- [`GLOSSARY.md`](file:///C:/Users/Andre/happyrobot-kb/GLOSSARY.md) — every platform term, 1-line def + link.
- [`GOTCHAS.md`](file:///C:/Users/Andre/happyrobot-kb/GOTCHAS.md) — consolidated "never do X" rules across all domains.
- [`OPEN-QUESTIONS.md`](file:///C:/Users/Andre/happyrobot-kb/OPEN-QUESTIONS.md) — what the scrape doesn't answer; ask Andres, log resolutions here.
- [`source/happyrobot-docs-full.txt`](file:///C:/Users/Andre/happyrobot-kb/source/happyrobot-docs-full.txt) — frozen raw dump used for `(source:L####)` citations.

## What's in the KB (16 subfolders, ~57 files)

`platform/` `authoring/` `voice/` `channels/` `knowledge-bases/` `integrations/` `data-storage/` `contacts/` `experimentation/` `quality/` `runs-ops/` `api-sdk/` `ui/` `security/` `showcase/` `source/`.

## Reading priority for this project

Critical path (grounds architecture decisions):
1. [voice/voice-agents.md](file:///C:/Users/Andre/happyrobot-kb/voice/voice-agents.md) — voice-agent internals
2. [voice/prompting-guide.md](file:///C:/Users/Andre/happyrobot-kb/voice/prompting-guide.md) — prompt structure + anti-patterns
3. [authoring/triggers.md](file:///C:/Users/Andre/happyrobot-kb/authoring/triggers.md) — web-call trigger URL + env-specific hooks + auth
4. [authoring/nodes-integration.md](file:///C:/Users/Andre/happyrobot-kb/authoring/nodes-integration.md) — tool-call / webhook node config
5. [authoring/variables.md](file:///C:/Users/Andre/happyrobot-kb/authoring/variables.md) — `{{group_id.var}}` rules, `response.` prefix, `iteration_element`
6. [authoring/nodes-core.md](file:///C:/Users/Andre/happyrobot-kb/authoring/nodes-core.md) — AI Extract (JSON Schema strict-mode rule), AI Classify
7. [data-storage/webhooks-outbound.md](file:///C:/Users/Andre/happyrobot-kb/data-storage/webhooks-outbound.md) — `call.ended`, retry, no HMAC
8. [api-sdk/rest-endpoints.md](file:///C:/Users/Andre/happyrobot-kb/api-sdk/rest-endpoints.md) — Runs / Sessions / Artifacts API if we need HR-side reads

Showcase beyond requirements:
- [showcase/demo-capabilities.md](file:///C:/Users/Andre/happyrobot-kb/showcase/demo-capabilities.md) — A/B experiments, northstars, adversarial suites, Twin DB, MCP.
