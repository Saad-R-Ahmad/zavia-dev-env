#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .dev.env ]]; then
  echo "Missing .dev.env. Create it from .dev.env.example first."
  exit 1
fi

PROFILE="${1:-core}"

if [[ "$PROFILE" != "core" && "$PROFILE" != "apps" && "$PROFILE" != "all" ]]; then
  echo "Usage: $0 [core|apps|all]"
  exit 1
fi

echo "Validating compose..."
docker compose --env-file .dev.env -f docker-compose.dev.yml config >/dev/null

echo "Starting profile: $PROFILE"
docker compose --env-file .dev.env -f docker-compose.dev.yml --profile "$PROFILE" up -d

echo "Stack started."
docker compose --env-file .dev.env -f docker-compose.dev.yml ps
