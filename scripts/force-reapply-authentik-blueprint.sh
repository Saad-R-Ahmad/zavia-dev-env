#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
  echo "Missing ${PROJECT_ROOT}/.env" >&2
  exit 1
fi

AUTHENTIK_CONTAINER="${1:-zavia-authentik}"

if ! docker ps --format '{{.Names}}' | grep -Fxq "${AUTHENTIK_CONTAINER}"; then
  echo "Container not running: ${AUTHENTIK_CONTAINER}" >&2
  exit 1
fi

echo "Removing blueprint hash marker from /media/.authentik-blueprint.sha256 ..."
docker exec "${AUTHENTIK_CONTAINER}" rm -f /media/.authentik-blueprint.sha256

echo "Re-running authentik-blueprint-apply service ..."
docker compose --project-directory "${PROJECT_ROOT}" --env-file "${PROJECT_ROOT}/.env" -f "${PROJECT_ROOT}/docker-compose.yml" up -d --force-recreate authentik-blueprint-apply

echo "Waiting for apply job to finish ..."
docker compose --project-directory "${PROJECT_ROOT}" --env-file "${PROJECT_ROOT}/.env" -f "${PROJECT_ROOT}/docker-compose.yml" wait authentik-blueprint-apply >/dev/null || true

echo "Apply service logs (tail):"
docker logs zavia-dev-env-authentik-blueprint-apply-1 2>&1 | tail -n 80

echo "Apply service state:"
docker inspect -f '{{.State.Status}} (exit {{.State.ExitCode}})' zavia-dev-env-authentik-blueprint-apply-1

echo "Current blueprint hash marker:"
docker exec "${AUTHENTIK_CONTAINER}" cat /media/.authentik-blueprint.sha256

echo "Force reapply completed."
