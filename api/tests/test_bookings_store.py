"""bookings_store tests — Twin-backed reads with twin_client mocked."""

from unittest.mock import MagicMock

import pytest

from app.services import bookings_store


@pytest.mark.asyncio
async def test_list_bookings_returns_normalized_rows(fake_twin: MagicMock) -> None:
    fake_twin.query.return_value = [
        {
            "id": 1,
            "created_at": "2026-04-27T10:00:00Z",
            "call_id": "C-1",
            "mc_number": "123456",
            "load_id": "L-1",
            "apply_rate": "2500.0",  # Twin returns string-encoded floats
        }
    ]
    rows = await bookings_store.list_bookings(limit=50)
    assert len(rows) == 1
    assert rows[0]["apply_rate"] == 2500.0
    # SQL was issued with limit/offset interpolated.
    sql, params = fake_twin.query.call_args.args
    assert "FROM bookings" in sql
    assert params["limit"] == 50
    assert params["offset"] == 0


@pytest.mark.asyncio
async def test_list_bookings_with_since_ts(fake_twin: MagicMock) -> None:
    fake_twin.query.return_value = []
    await bookings_store.list_bookings(since_ts="2026-04-27T00:00:00Z")
    sql, params = fake_twin.query.call_args.args
    assert "WHERE created_at >= :since_ts" in sql
    assert params["since_ts"] == "2026-04-27T00:00:00Z"


@pytest.mark.asyncio
async def test_bookings_by_mc_filters(fake_twin: MagicMock) -> None:
    fake_twin.query.return_value = [
        {"id": 1, "call_id": "C-1", "mc_number": "999", "load_id": "L-1", "apply_rate": 1500}
    ]
    rows = await bookings_store.bookings_by_mc("999")
    assert len(rows) == 1
    sql, params = fake_twin.query.call_args.args
    assert "WHERE mc_number = :mc_number" in sql
    assert params["mc_number"] == "999"


@pytest.mark.asyncio
async def test_bookings_by_mc_empty_string_returns_empty(fake_twin: MagicMock) -> None:
    rows = await bookings_store.bookings_by_mc("")
    assert rows == []
    assert fake_twin.query.call_count == 0


@pytest.mark.asyncio
async def test_bookings_for_call_filters(fake_twin: MagicMock) -> None:
    # WAF workaround: query pulls all rows + filters Python-side because
    # Cloudflare blocks `WHERE call_id = '<uuid-with-dashes>'`. Test asserts
    # the no-WHERE shape + that only the matching call_id rows survive.
    fake_twin.query.return_value = [
        {"id": 1, "call_id": "C-42", "load_id": "L-1", "apply_rate": 2000},
        {"id": 2, "call_id": "OTHER", "load_id": "L-2", "apply_rate": 1750},
        {"id": 3, "call_id": "C-42", "load_id": "L-3", "apply_rate": 1900},
    ]
    rows = await bookings_store.bookings_for_call("C-42")
    assert len(rows) == 2
    assert {r["load_id"] for r in rows} == {"L-1", "L-3"}
    sql_arg = fake_twin.query.call_args.args[0]
    assert "WHERE" not in sql_arg
    assert "FROM bookings" in sql_arg


@pytest.mark.asyncio
async def test_apply_rate_null_resilient(fake_twin: MagicMock) -> None:
    fake_twin.query.return_value = [
        {"id": 1, "call_id": "C-1", "load_id": "L-1", "apply_rate": None}
    ]
    rows = await bookings_store.list_bookings()
    assert rows[0]["apply_rate"] is None


@pytest.mark.asyncio
async def test_apply_rate_garbage_string_becomes_none(fake_twin: MagicMock) -> None:
    fake_twin.query.return_value = [
        {"id": 1, "call_id": "C-1", "load_id": "L-1", "apply_rate": "not-a-number"}
    ]
    rows = await bookings_store.list_bookings()
    assert rows[0]["apply_rate"] is None
