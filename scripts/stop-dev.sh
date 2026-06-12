#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .dev.env ]]; then
  echo "Missing .dev.env"
  exit 1
fi

echo "Stopping development stack..."
docker compose --env-file .dev.env -f docker-compose.dev.yml --profile all down

echo "Stopped."
