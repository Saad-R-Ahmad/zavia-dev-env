#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
  echo "Missing ${PROJECT_ROOT}/.env"
  exit 1
fi

docker compose --project-directory "${PROJECT_ROOT}" --env-file "${PROJECT_ROOT}/.env" -f "${PROJECT_ROOT}/docker-compose.yml" ps
