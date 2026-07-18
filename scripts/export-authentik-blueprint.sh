#!/usr/bin/env bash
set -euo pipefail

# Snapshot-only Authentik export for backup/audit purposes.
#
# IMPORTANT: This script NO LONGER overwrites appdata/authentik/blueprints/current/.
# The canonical auto-apply blueprint is a hand-maintained, minimal, secret-free,
# single-instance IaC file. A full runtime export contains live secrets, runtime
# UUIDs/tokens, and Authentik's own internal/default objects — it must never
# silently replace curated IaC (see Overview/Authentik_OIDC_Infrastructure.md).
#
# Snapshots produced by this script are NOT intended for git tracking; treat
# them as operational backups and store them outside the repository or in a
# path covered by .gitignore.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUTH_DIR="${PROJECT_ROOT}/appdata/authentik"
CONTAINER_NAME="${1:-zavia-authentik}"
TS="$(date +%Y-%m-%d_%H%M%S)"
EXPORT_DIR="${AUTH_DIR}/blueprints/snapshots/${TS}"

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
docker run --rm -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "mkdir -p /target/blueprints/snapshots/${TS}"

# Copy blueprint snapshot ONLY. The active/current blueprint is never touched
# by this script.
cat "${TMP_FILE}" | docker run --rm -i -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "cat > /target/blueprints/snapshots/${TS}/authentik-blueprint.yaml"

cat <<EOF | docker run --rm -i -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "cat > /target/blueprints/snapshots/${TS}/manifest.json"
{
  "exported_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_container": "${CONTAINER_NAME}",
  "artifact": "authentik-blueprint.yaml",
  "notes": [
    "Full Authentik configuration export (backup/audit snapshot only)",
    "Contains flows, stages, providers, applications, groups, and branding assets references",
    "Contains live secrets and runtime identifiers — do not commit to git",
    "Does NOT update blueprints/current/ (the auto-apply blueprint is hand-maintained IaC)"
  ]
}
EOF

cat <<'EOF' | docker run --rm -i -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "cat > /target/blueprints/snapshots/${TS}/README.md"
# Authentik Configuration Snapshot (Backup/Audit Only)

This folder contains a full Authentik configuration exported from the running
instance. It is a point-in-time backup/audit artifact, NOT the source of the
active auto-apply blueprint.

## Files
- `authentik-blueprint.yaml`
- `manifest.json`

## Security

This export contains live secrets (client secrets, keys) and runtime
identifiers. Do not commit it to git. Store it in protected, access-controlled
backup storage only.

## Restoring from a snapshot

Restoring from a full snapshot is a deliberate disaster-recovery action, not
a normal deployment step:

1. Review the snapshot for stale or unwanted objects (e.g. old groups/users)
   before applying it — a full export reflects whatever existed in the source
   instance at export time, including anything that should not be recreated.
2. Apply explicitly:

```bash
docker exec zavia-authentik ak apply_blueprint /path/to/authentik-blueprint.yaml
```

3. After restoring, verify the group/provider/application set matches the
   current single-instance model documented in
   `Overview/Authentik_OIDC_Infrastructure.md` before promoting to normal use.

## Notes
- Keep source and target Authentik versions aligned when possible.
- Use staging first; this is a full-state export.
EOF

echo "Snapshot export complete: ${EXPORT_DIR}"
echo "blueprints/current/ was NOT modified by this script."
