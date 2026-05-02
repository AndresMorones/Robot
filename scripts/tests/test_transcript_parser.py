import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transcript_parser import parse_transcript


def _parse_iso_to_ms(iso_str: str) -> int:
    s = iso_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def test_empty_transcript():
    result = parse_transcript([])
    assert result["events"] == []
    assert result["turn_count"] == 0
    assert result["tool_call_count"] == 0
    assert result["call_started_at"] is None
    assert result["duration_ms"] is None


def test_uuidv7_wall_clock_decode():
    uuid_str = "019dd327-1289-7de4-8a5b-ca96ebd5323e"
    expected_ms = int("019dd3271289", 16)
    turns = [{"id": uuid_str, "role": "assistant", "content": "hi"}]
    result = parse_transcript(turns)
    wall_clock = result["events"][0]["wall_clock"]
    assert wall_clock is not None
    assert _parse_iso_to_ms(wall_clock) == expected_ms


def test_uuidv4_id_no_decode():
    turns = [{
        "id": "97cf17e9-f9ac-4a65-ace6-0598fdcc8326",
        "role": "user",
        "content": "Hello",
    }]
    result = parse_transcript(turns)
    assert result["events"][0]["wall_clock"] is None


def test_null_id_tool_turn():
    turns = [{
        "id": None,
        "role": "tool",
        "content": "{}",
        "tool_call_id": "c1",
        "name": "foo",
    }]
    result = parse_transcript(turns)
    assert result["events"][0]["wall_clock"] is None


def test_language_prefix_stripped():
    turns = [{
        "id": "019dd327-1289-7de4-8a5b-ca96ebd5323e",
        "role": "assistant",
        "content": "[en] Hello",
    }]
    result = parse_transcript(turns)
    event = result["events"][0]
    assert event["text"] == "Hello"
    assert event["raw_content"] == "[en] Hello"


def test_tool_call_args_parsed():
    turns = [{
        "id": "019dd327-764e-7077-b781-6fe35d490bfa",
        "role": "assistant",
        "tool_calls": [{
            "id": "call_x",
            "function": {
                "name": "verify_carrier",
                "arguments": '{"mc_number":"250819"}',
            },
        }],
    }]
    result = parse_transcript(turns)
    event = result["events"][0]
    assert event["tool_calls"][0]["arguments"] == {"mc_number": "250819"}


def test_tool_result_pairs_with_call():
    turns = [
        {
            "id": "019dd327-764e-7077-b781-6fe35d490bfa",
            "role": "assistant",
            "tool_calls": [{
                "id": "call_x",
                "function": {
                    "name": "verify_carrier",
                    "arguments": "{}",
                },
            }],
        },
        {
            "id": None,
            "role": "tool",
            "content": '{"ok":true}',
            "tool_call_id": "call_x",
            "name": "verify_carrier",
        },
    ]
    result = parse_transcript(turns)
    assistant_events = [e for e in result["events"] if e["kind"] == "assistant_tool_call"]
    tool_result_events = [e for e in result["events"] if e["kind"] == "tool_result"]
    assert len(assistant_events) == 1
    assert len(tool_result_events) == 1
    assert assistant_events[0]["tool_calls"][0]["result"] == {"ok": True}


def test_assistant_with_content_and_tool_calls():
    turns = [{
        "id": "019dd327-764e-7077-b781-6fe35d490bfa",
        "role": "assistant",
        "content": "preamble",
        "tool_calls": [{
            "id": "call_x",
            "function": {
                "name": "verify_carrier",
                "arguments": "{}",
            },
        }],
    }]
    result = parse_transcript(turns)
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert event["kind"] == "assistant_tool_call"
    assert event["text"] == "preamble"
    assert event["tool_calls"] is not None
    assert len(event["tool_calls"]) == 1


def test_user_offset_ms_preserved():
    turns = [{
        "id": "97cf17e9-f9ac-4a65-ace6-0598fdcc8326",
        "role": "user",
        "content": "Hello",
        "start": 4500,
        "end": 8280,
    }]
    result = parse_transcript(turns)
    assert result["events"][0]["offset_ms"] == {"start": 4500, "end": 8280}


def test_user_missing_offsets():
    turns = [{
        "id": "97cf17e9-f9ac-4a65-ace6-0598fdcc8326",
        "role": "user",
        "content": "Hello",
    }]
    result = parse_transcript(turns)
    assert result["events"][0]["offset_ms"] is None


def test_malformed_tool_args_kept_raw():
    turns = [{
        "id": "019dd327-764e-7077-b781-6fe35d490bfa",
        "role": "assistant",
        "tool_calls": [{
            "id": "call_x",
            "function": {
                "name": "verify_carrier",
                "arguments": "not-json{",
            },
        }],
    }]
    result = parse_transcript(turns)
    event = result["events"][0]
    assert event["tool_calls"][0]["arguments"] == "not-json{"


def test_malformed_tool_result_kept_raw():
    turns = [{
        "id": None,
        "role": "tool",
        "content": "not-json{",
        "tool_call_id": "call_x",
        "name": "verify_carrier",
    }]
    result = parse_transcript(turns)
    tool_result_events = [e for e in result["events"] if e["kind"] == "tool_result"]
    assert len(tool_result_events) == 1
    assert tool_result_events[0]["tool_result"]["result"] == "not-json{"


def test_tool_call_count_aggregate():
    turns = [
        {
            "id": "019dd327-764e-7077-b781-6fe35d490bfa",
            "role": "assistant",
            "tool_calls": [
                {"id": "c1", "function": {"name": "f", "arguments": "{}"}},
                {"id": "c2", "function": {"name": "f", "arguments": "{}"}},
            ],
        },
        {
            "id": "019dd327-764e-7077-b781-6fe35d490bfb",
            "role": "assistant",
            "tool_calls": [
                {"id": "c3", "function": {"name": "f", "arguments": "{}"}},
            ],
        },
    ]
    result = parse_transcript(turns)
    assert result["tool_call_count"] == 3


def test_full_call_sample():
    sample = [
        {"id": "019dd327-1289-7de4-8a5b-ca96ebd5323e", "role": "assistant", "content": "Thank you for calling Acme Logistics, how can I help?"},
        {"id": "97cf17e9-f9ac-4a65-ace6-0598fdcc8326", "role": "user", "content": "Hello", "start": 4500, "end": 8280},
        {"id": "019dd327-764e-7077-b781-6fe35d490bfa", "role": "assistant", "tool_calls": [{"id": "call_x", "function": {"name": "verify_carrier", "arguments": "{\"mc_number\":\"250819\"}"}}]},
        {"id": None, "role": "tool", "content": "{\"content\":{\"carrier\":{\"legalName\":\"GLK TRUCKING LLC\"}}}", "tool_call_id": "call_x", "name": "verify_carrier"},
    ]
    result = parse_transcript(sample)
    assert result["turn_count"] == 4
    assert result["tool_call_count"] == 1

    assistant_tool_events = [e for e in result["events"] if e["kind"] == "assistant_tool_call"]
    assert len(assistant_tool_events) == 1
    args = assistant_tool_events[0]["tool_calls"][0]["arguments"]
    assert isinstance(args, dict)
    assert args["mc_number"] == "250819"

    tool_result_events = [e for e in result["events"] if e["kind"] == "tool_result"]
    assert len(tool_result_events) == 1
    result_payload = tool_result_events[0]["tool_result"]["result"]
    assert result_payload["content"]["carrier"]["legalName"] == "GLK TRUCKING LLC"
