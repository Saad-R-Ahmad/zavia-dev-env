#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
  echo "Missing ${PROJECT_ROOT}/.env"
  exit 1
fi

PROFILE="${1:-core}"

if [[ "$PROFILE" != "core" && "$PROFILE" != "apps" && "$PROFILE" != "all" ]]; then
  echo "Usage: $0 [core|apps|all]"
  exit 1
fi

echo "Validating compose..."
docker compose --project-directory "${PROJECT_ROOT}" --env-file "${PROJECT_ROOT}/.env" -f "${PROJECT_ROOT}/docker-compose.yml" config >/dev/null

echo "Starting profile: $PROFILE"
docker compose --project-directory "${PROJECT_ROOT}" --env-file "${PROJECT_ROOT}/.env" -f "${PROJECT_ROOT}/docker-compose.yml" --profile "$PROFILE" up -d

echo "Stack started."
docker compose --project-directory "${PROJECT_ROOT}" --env-file "${PROJECT_ROOT}/.env" -f "${PROJECT_ROOT}/docker-compose.yml" ps
