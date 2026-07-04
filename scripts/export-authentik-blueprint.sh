#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUTH_DIR="${PROJECT_ROOT}/appdata/authentik"
CONTAINER_NAME="${1:-zavia-authentik}"
TS="$(date +%Y-%m-%d_%H%M%S)"
EXPORT_DIR="${AUTH_DIR}/config-exports/blueprints/${TS}"
CURRENT_DIR="${AUTH_DIR}/config-exports/blueprints/current"

if ! docker ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
  echo "Container not running: ${CONTAINER_NAME}" >&2
  exit 1
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "${TMP_FILE}"' EXIT

# Export full blueprint. Authentik prepends startup logs, so keep only YAML from the first "context:" line.
docker exec "${CONTAINER_NAME}" ak export_blueprint -v 0 2>&1 \
  | awk 'found || /^context:/{found=1; print}' > "${TMP_FILE}"

if [[ ! -s "${TMP_FILE}" ]]; then
  echo "Blueprint export returned no content" >&2
  exit 1
fi

if ! grep -q '^entries:' "${TMP_FILE}"; then
  echo "Blueprint export missing entries section" >&2
  exit 1
fi

# Create destination with root helper because appdata/authentik may be root-owned.
docker run --rm -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "mkdir -p /target/config-exports/blueprints/${TS}"

# Copy blueprint and metadata.
cat "${TMP_FILE}" | docker run --rm -i -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "cat > /target/config-exports/blueprints/${TS}/authentik-blueprint.yaml"

# Refresh the stable blueprint path that compose mounts for auto-apply.
docker run --rm -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "mkdir -p /target/config-exports/blueprints/current"
cat "${TMP_FILE}" | docker run --rm -i -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "cat > /target/config-exports/blueprints/current/authentik-blueprint.yaml"

cat <<EOF | docker run --rm -i -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "cat > /target/config-exports/blueprints/${TS}/manifest.json"
{
  "exported_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_container": "${CONTAINER_NAME}",
  "artifact": "authentik-blueprint.yaml",
  "notes": [
    "Full tenant blueprint export from authentik",
    "Contains flows, stages, providers, applications, groups, and branding assets references"
  ]
}
EOF

cat <<'EOF' | docker run --rm -i -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "cat > /target/config-exports/blueprints/${TS}/README.md"
# Authentik Blueprint Snapshot

This folder contains a full Authentik blueprint exported from the running instance.

## Files
- `authentik-blueprint.yaml`
- `manifest.json`

## Apply to a new environment

1. Copy the blueprint into the target Authentik blueprints mount (for this stack, under `appdata/authentik/custom-templates/blueprints/` or another blueprints-import path you configure).
2. Trigger import from the Authentik admin UI Blueprints page, or run:

```bash
docker exec zavia-authentik ak apply_blueprint /path/to/authentik-blueprint.yaml
```

## Notes
- Keep source and target Authentik versions aligned when possible.
- Use staging first; this is a full-state export.
- Client secrets and cert/key references may require environment-specific adjustments.
EOF

echo "Blueprint export complete: ${EXPORT_DIR}"
echo "Blueprint auto-apply source updated: ${CURRENT_DIR}/authentik-blueprint.yaml"
