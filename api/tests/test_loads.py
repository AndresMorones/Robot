"""Load search filter tests."""

from fastapi.testclient import TestClient


def test_no_filter_returns_all_up_to_max_results(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    r = client.post("/v1/loads/search", json={}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total_in_store"] == 3
    assert len(body["matches"]) == 3  # default max_results=3


def test_filter_by_origin_state(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/v1/loads/search",
        json={"origin_state": "TX"},
        headers=auth_headers,
    )
    matches = r.json()["matches"]
    assert len(matches) == 1
    assert matches[0]["load_id"] == "L-T1"


def test_filter_by_destination_state(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/v1/loads/search",
        json={"destination_state": "FL"},
        headers=auth_headers,
    )
    matches = r.json()["matches"]
    assert len(matches) == 1
    assert matches[0]["load_id"] == "L-T2"


def test_filter_by_equipment_type(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/v1/loads/search",
        json={"equipment_type": "REEFER"},
        headers=auth_headers,
    )
    matches = r.json()["matches"]
    assert len(matches) == 1
    assert matches[0]["load_id"] == "L-T2"


def test_max_results_caps_returned_count(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/v1/loads/search",
        json={"max_results": 2},
        headers=auth_headers,
    )
    matches = r.json()["matches"]
    assert len(matches) == 2


def test_no_match_returns_empty_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/v1/loads/search",
        json={"origin_state": "ZZ"},  # no such state in fixtures
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["matches"] == []
    assert r.json()["total_in_store"] == 3  # store still has 3
