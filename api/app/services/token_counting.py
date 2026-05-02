"""Token counting helpers for transcript-derived telemetry.

Uses tiktoken when available; falls back to char-len/4 when not. Both paths
return integers so callers don't have to special-case None outputs. Counts are
approximate but consistent — what matters is that a 500-token call and a
2000-token call are visibly different in the dashboard.
"""

from __future__ import annotations

from typing import Any

try:  # tiktoken is an optional dep — production has it, local dev may not.
    import tiktoken

    _ENCODER = tiktoken.get_encoding("o200k_base")

    def _count(text: str) -> int:
        return len(_ENCODER.encode(text))

    TOKEN_METHOD = "tiktoken_o200k_base"
except Exception:  # noqa: BLE001
    _ENCODER = None

    def _count(text: str) -> int:
        # Rough proxy: 1 token ≈ 4 chars for English. Off by ~10% on natural
        # language; close enough for "is this call cheap or expensive".
        return max(0, len(text) // 4)

    TOKEN_METHOD = "char_count_fallback"


def _coerce_text(value: Any) -> str:
    """Render any transcript value as a plain string for tokenizing.

    Tool args/results arrive as nested dicts/lists; the model still sees them
    serialized when they go in/out of the prompt, so we serialize too.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        import json

        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def count_role_tokens(timeline: list[dict]) -> dict[str, int]:
    """Sum tokens by role family across the parser's event timeline.

    Returns: {agent_input, agent_output, tool_input, tool_output}

    Convention (mirrors how the model actually sees tokens):
      - agent_output  → assistant_message text + assistant_tool_call preamble
      - tool_input    → assistant_tool_call args (the model produced these as
                        a structured output, but they're "input" to the tool)
      - tool_output   → tool_result content (becomes input to the next agent
                        turn, which is why we surface it as tool_output here —
                        downstream consumers add input + output to get total
                        prompt+completion volume).
      - agent_input   → user_message text (carrier speech the model consumes)
    """
    totals = {
        "agent_input": 0,
        "agent_output": 0,
        "tool_input": 0,
        "tool_output": 0,
    }
    for e in timeline or []:
        kind = e.get("kind")
        if kind == "user_message":
            totals["agent_input"] += _count(_coerce_text(e.get("text")))
        elif kind == "assistant_message":
            totals["agent_output"] += _count(_coerce_text(e.get("text")))
        elif kind == "assistant_tool_call":
            preamble = e.get("text")
            if preamble:
                totals["agent_output"] += _count(_coerce_text(preamble))
            for tc in e.get("tool_calls") or []:
                totals["tool_input"] += _count(_coerce_text(tc.get("arguments")))
        elif kind == "tool_result":
            tr = e.get("tool_result") or {}
            totals["tool_output"] += _count(_coerce_text(tr.get("result")))
    return totals
