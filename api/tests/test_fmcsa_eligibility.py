"""Contract tests for the FMCSA QCMobile eligibility gate.

The carrier verification gate runs inside the HappyRobot voice-agent prompt
(not in our Python service), so this module tests the *shape contract* we
rely on when interpreting FMCSA QCMobile responses. The helper below mirrors
the seven-check rule set the prompt enforces. Anyone forking this repo can
run these tests to catch a drift in the upstream FMCSA payload, in our
prompt logic, or in fixtures shipped with the project.

The seven checks (all must pass for an eligible carrier):
    1. ``content`` is non-null (MC was found in FMCSA's database)
    2. ``carrier.allowedToOperate == "Y"``
    3. ``carrier.statusCode == "A"`` (Active)
    4. ``carrier.oosDate`` is null (not Out of Service)
    5. ``carrier.safetyRating`` is null, "Satisfactory", or "Conditional"
    6. ``carrier.brokerAuthorityStatus != "A"`` (we don't dispatch to brokers)
    7. ``carrier.censusTypeId.censusType`` is "C" (Carrier) or null
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def evaluate_fmcsa_eligibility(response: dict) -> tuple[bool, str | None]:
    """Return ``(eligible, reason)`` for a raw FMCSA QCMobile response.

    ``reason`` is ``None`` when eligible and one of the documented reason
    codes otherwise. Reason codes are evaluated in priority order so the
    first failing check wins.
    """
    content = response.get("content")
    if content is None:
        return False, "MC_NOT_FOUND"

    carrier = content.get("carrier") or {}

    if carrier.get("allowedToOperate") != "Y":
        return False, "NOT_AUTHORIZED"

    status_code = carrier.get("statusCode")
    if status_code == "R":
        return False, "REVOKED"
    if status_code != "A":
        return False, "INACTIVE"

    if carrier.get("oosDate") is not None:
        return False, "OUT_OF_SERVICE"

    safety_rating = carrier.get("safetyRating")
    if safety_rating is not None and safety_rating not in {"Satisfactory", "Conditional"}:
        return False, "UNSAFE_RATING"

    if carrier.get("brokerAuthorityStatus") == "A":
        return False, "LIKELY_BROKER"

    census_type = (carrier.get("censusTypeId") or {}).get("censusType")
    if census_type is not None and census_type != "C":
        return False, "NOT_A_CARRIER"

    return True, None


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def eligible_response() -> dict:
    return _load_fixture("fmcsa_eligible_mc1234567.json")


@pytest.fixture
def inactive_response() -> dict:
    return _load_fixture("fmcsa_inactive_mc2986.json")


@pytest.fixture
def not_found_response() -> dict:
    return _load_fixture("fmcsa_not_found.json")


def test_eligible_carrier_passes(eligible_response: dict) -> None:
    eligible, reason = evaluate_fmcsa_eligibility(eligible_response)
    assert eligible is True, f"expected eligible carrier, got reason={reason!r}"
    assert reason is None


def test_inactive_carrier_fails_with_INACTIVE(inactive_response: dict) -> None:
    eligible, reason = evaluate_fmcsa_eligibility(inactive_response)
    assert eligible is False
    assert reason == "INACTIVE", f"expected INACTIVE, got {reason!r}"


def test_mc_not_found_fails_with_MC_NOT_FOUND(not_found_response: dict) -> None:
    eligible, reason = evaluate_fmcsa_eligibility(not_found_response)
    assert eligible is False
    assert reason == "MC_NOT_FOUND"


def test_not_authorized_synthetic(eligible_response: dict) -> None:
    payload = copy.deepcopy(eligible_response)
    payload["content"]["carrier"]["allowedToOperate"] = "N"
    assert evaluate_fmcsa_eligibility(payload) == (False, "NOT_AUTHORIZED")


def test_revoked_synthetic(eligible_response: dict) -> None:
    payload = copy.deepcopy(eligible_response)
    payload["content"]["carrier"]["statusCode"] = "R"
    assert evaluate_fmcsa_eligibility(payload) == (False, "REVOKED")


def test_out_of_service_synthetic(eligible_response: dict) -> None:
    payload = copy.deepcopy(eligible_response)
    payload["content"]["carrier"]["oosDate"] = "2025-01-15"
    assert evaluate_fmcsa_eligibility(payload) == (False, "OUT_OF_SERVICE")


def test_unsatisfactory_safety_synthetic(eligible_response: dict) -> None:
    payload = copy.deepcopy(eligible_response)
    payload["content"]["carrier"]["safetyRating"] = "Unsatisfactory"
    assert evaluate_fmcsa_eligibility(payload) == (False, "UNSAFE_RATING")


def test_likely_broker_synthetic(eligible_response: dict) -> None:
    payload = copy.deepcopy(eligible_response)
    payload["content"]["carrier"]["brokerAuthorityStatus"] = "A"
    assert evaluate_fmcsa_eligibility(payload) == (False, "LIKELY_BROKER")


def test_conditional_safety_passes(eligible_response: dict) -> None:
    payload = copy.deepcopy(eligible_response)
    payload["content"]["carrier"]["safetyRating"] = "Conditional"
    assert evaluate_fmcsa_eligibility(payload) == (True, None)


def test_null_safety_rating_passes(eligible_response: dict) -> None:
    payload = copy.deepcopy(eligible_response)
    payload["content"]["carrier"]["safetyRating"] = None
    assert evaluate_fmcsa_eligibility(payload) == (True, None)
