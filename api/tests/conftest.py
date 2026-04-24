"""Test fixtures.

Each test gets a fresh fixture loads.json in a tmp dir + a known bearer token.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.load_store import load_store

TEST_TOKEN = "test-bearer-token-do-not-use-in-prod"

_TEST_LOADS = [
    {
        "load_id": "L-T1",
        "origin": "Dallas, TX",
        "destination": "Houston, TX",
        "origin_state": "TX",
        "destination_state": "TX",
        "pickup_datetime": "2026-04-25T08:00:00Z",
        "delivery_datetime": "2026-04-25T18:00:00Z",
        "equipment_type": "DRY_VAN",
        "loadboard_rate": 2500,
        "notes": None,
        "weight": 42000,
        "commodity_type": "GENERAL_MERCHANDISE",
        "num_of_pieces": 24,
        "miles": 240,
        "dimensions": "53x8x9 ft",
    },
    {
        "load_id": "L-T2",
        "origin": "Atlanta, GA",
        "destination": "Miami, FL",
        "origin_state": "GA",
        "destination_state": "FL",
        "pickup_datetime": "2026-04-26T08:00:00Z",
        "delivery_datetime": "2026-04-27T12:00:00Z",
        "equipment_type": "REEFER",
        "loadboard_rate": 1800,
        "notes": "Frozen produce.",
        "weight": 38000,
        "commodity_type": "PRODUCE_FROZEN",
        "num_of_pieces": 18,
        "miles": 660,
        "dimensions": "53x8x9 ft",
    },
    {
        "load_id": "L-T3",
        "origin": "Los Angeles, CA",
        "destination": "Phoenix, AZ",
        "origin_state": "CA",
        "destination_state": "AZ",
        "pickup_datetime": "2026-04-25T14:00:00Z",
        "delivery_datetime": "2026-04-26T08:00:00Z",
        "equipment_type": "FLATBED",
        "loadboard_rate": 1450,
        "notes": "Construction materials.",
        "weight": 45000,
        "commodity_type": "BUILDING_MATERIALS",
        "num_of_pieces": 6,
        "miles": 372,
        "dimensions": "48x8.5x4 ft",
    },
]


@pytest.fixture(autouse=True)
def setup_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_path = tmp_path / "loads.json"
    fixture_path.write_text(json.dumps(_TEST_LOADS))
    monkeypatch.setattr(settings, "loads_json_path", str(fixture_path))
    monkeypatch.setattr(settings, "api_bearer_token", TEST_TOKEN)
    # Force a reload (lifespan also loads, but tests can call before lifespan runs).
    load_store.load(str(fixture_path))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def token() -> str:
    return TEST_TOKEN


@pytest.fixture
def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
