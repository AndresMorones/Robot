"""POST /calls + POST /v1/calls/log deprecation tests.

After the Twin pivot, FastAPI no longer ingests calls — the HR Write-to-Twin
component owns the calls_log + bookings tables. These endpoints return 410 Gone
with a recovery hint so any HR workflow still pointing at the old URL fails
loudly (vs a silent 404).
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_post_calls_returns_410(client: TestClient, fake_twin: MagicMock) -> None:  # noqa: ARG001
    r = client.post("/calls", json={"call_id": "X-1"})
    assert r.status_code == 410
    body = r.json()
    assert "deprecated" in body["detail"].lower()
    assert "write-to-twin" in body["detail"].lower()


def test_post_v1_calls_log_returns_410(
    client: TestClient,
    fake_twin: MagicMock,  # noqa: ARG001
) -> None:
    r = client.post("/v1/calls/log", json={"call_id": "X-1"})
    assert r.status_code == 410
