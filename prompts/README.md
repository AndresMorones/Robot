# Workflow Prompts (canonical copies)

GitHub-version-controlled copies of every prompt and schema configured in the HappyRobot workflow `inbound-carrier-v4`. The HR platform is the runtime source of truth; these files are the canonical reference for review, audit, and re-paste in case of workflow rebuild.

## Files

| File | Where it runs in HR | Last synced |
|---|---|---|
| [voice-agent-system-prompt.md](voice-agent-system-prompt.md) | Inbound Voice Agent → Prompt node | 2026-04-25 |
| [classify-outcome-realtime.md](classify-outcome-realtime.md) | Inbound Voice Agent → Real-time Classifier (Call Outcome) | 2026-04-25 |
| [classify-sentiment-realtime.md](classify-sentiment-realtime.md) | Inbound Voice Agent → Real-time Classifier (Carrier Sentiment) | 2026-04-25 |
| [ai-extract-schema.md](ai-extract-schema.md) | Post-call AI Extract node | 2026-04-25 |

## Sync rule

When you change a prompt in HR, update the corresponding file here with the same content + bump the "Last synced" date in this README and in the file's header. When you change a file here, paste the change into HR.

If they drift, **HR wins** (it's what the live agent uses), but this directory should match within minutes of any HR edit.

## Why version-control prompts

- **Reproducibility**: rebuild the workflow from scratch from these files
- **Diff history**: see how prompts evolved across iterations
- **Code review**: prompts get pull-request scrutiny like code
- **Audit trail**: regulators / customers can review the agent's instructions
- **Rollback**: if a prompt change breaks production, restore from git

## Variable references

Every prompt that uses HR workflow variables shows them as `{{ variable_name }}` placeholders in these files. **In HR, you must insert each one via the `@` picker** — typing the literal `{{ ... }}` text causes HR to silently render it as empty at runtime. The `@` picker resolves the variable to its persistent_id UUID, which is what HR's template engine needs.

The 4 + 1 workflow variables referenced across prompts:
- `agent_name` (string, default "Paul")
- `company_name` (string, default "Acme Logistics")
- `negotiation_floor_pct` (number, default 0.20)
- `max_negotiation_rounds` (integer, default 3)
- `agent_version` (string, default "v4") — added in build-plan Step E
