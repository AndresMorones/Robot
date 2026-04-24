"""Bearer auth tests — header + ?token= fallback."""

from fastapi.testclient import TestClient


def test_missing_auth_returns_401(client: TestClient) -> None:
    r = client.post("/v1/loads/search", json={})
    assert r.status_code == 401


def test_wrong_bearer_returns_401(client: TestClient) -> None:
    r = client.post(
        "/v1/loads/search",
        json={},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 401


def test_correct_bearer_returns_200(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post("/v1/loads/search", json={}, headers=auth_headers)
    assert r.status_code == 200


def test_query_token_fallback_returns_200(client: TestClient, token: str) -> None:
    r = client.post(f"/v1/loads/search?token={token}", json={})
    assert r.status_code == 200


def test_wrong_query_token_returns_401(client: TestClient) -> None:
    r = client.post("/v1/loads/search?token=wrong-token", json={})
    assert r.status_code == 401


def test_header_wins_over_query_when_both_present(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Correct header + wrong query → 200 (header takes precedence)."""
    r = client.post(
        "/v1/loads/search?token=wrong-token",
        json={},
        headers=auth_headers,
    )
    assert r.status_code == 200


def test_malformed_authorization_header_returns_401(client: TestClient, token: str) -> None:
    """No 'Bearer' scheme prefix → not authenticated."""
    r = client.post(
        "/v1/loads/search",
        json={},
        headers={"Authorization": token},  # missing 'Bearer ' prefix
    )
    assert r.status_code == 401
