#!/usr/bin/env bash
# Deploy the FastAPI backend to Fly.
# Self-cd's to the repo root so the API fly.toml + Dockerfile context resolve correctly.
# WHY: symmetric with deploy-dashboard.sh — keeps a single sanctioned path per app.
set -euo pipefail

APP="robot-api-andres-morones"
URL="https://${APP}.fly.dev"
HEALTH_FINGERPRINT='"service":"robot-api"'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

[[ -f "${REPO_ROOT}/fly.toml" ]] || { echo "ERR: ${REPO_ROOT}/fly.toml missing"; exit 1; }
grep -q "app = \"${APP}\"" "${REPO_ROOT}/fly.toml" || { echo "ERR: ${REPO_ROOT}/fly.toml is not the API config"; exit 1; }

echo ">> Deploying ${APP} from ${REPO_ROOT}"
cd "${REPO_ROOT}"
flyctl deploy --remote-only --app "${APP}"

echo ">> Verifying ${URL}/healthz serves the API image"
HEALTH_BODY="$(curl -sk --max-time 15 "${URL}/healthz" || true)"
if [[ "${HEALTH_BODY}" == *"${HEALTH_FINGERPRINT}"* ]]; then
  echo "OK: API image confirmed (${HEALTH_BODY})"
else
  echo "ERR: wrong image deployed to ${APP}!"
  echo "     expected fingerprint: ${HEALTH_FINGERPRINT}"
  echo "     got: ${HEALTH_BODY}"
  exit 2
fi
