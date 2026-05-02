"""Health endpoint (no auth)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    # `service` field is a deploy guardrail fingerprint: the deploy scripts in
    # `scripts/deploy-*.sh` curl this and assert the right image landed on the
    # right Fly app. Don't drop or rename without updating those scripts.
    return {"status": "ok", "service": "robot-api"}
