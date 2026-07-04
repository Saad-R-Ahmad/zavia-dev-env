#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUTH_DIR="${PROJECT_ROOT}/appdata/authentik"
TS="$(date +%Y-%m-%d_%H%M%S)"
EXPORT_DIR="${AUTH_DIR}/config-exports/${TS}"

CONTAINER_NAME="${1:-zavia-authentik}"

if ! docker ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
  echo "Container not running: ${CONTAINER_NAME}" >&2
  exit 1
fi

# Create host directory with root helper, because appdata/authentik may be root-owned.
docker run --rm -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "mkdir -p /target/config-exports/${TS}"

# Write export files to /media (bind-mounted to appdata/authentik/media), then copy to config-exports.
docker exec "${CONTAINER_NAME}" mkdir -p "/media/config-exports/${TS}"
docker exec "${CONTAINER_NAME}" ak dumpdata --indent 2 -o "/media/config-exports/${TS}/groups.json" \
  auth.group authentik_core.group authentik_core.groupsourceconnection
docker exec "${CONTAINER_NAME}" ak dumpdata --indent 2 -o "/media/config-exports/${TS}/applications.json" \
  authentik_core.application authentik_core.applicationentitlement
docker exec "${CONTAINER_NAME}" ak dumpdata --indent 2 -o "/media/config-exports/${TS}/oidc_providers.json" \
  authentik_core.provider authentik_providers_oauth2.oauth2provider
docker exec "${CONTAINER_NAME}" ak dumpdata --indent 2 -o "/media/config-exports/${TS}/mappings.json" \
  authentik_core.propertymapping authentik_providers_oauth2.scopemapping

MANIFEST_JSON=$(cat <<EOF
{
  "exported_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_container": "${CONTAINER_NAME}",
  "files": ["groups.json", "applications.json", "oidc_providers.json", "mappings.json"]
}
EOF
)

printf '%s\n' "${MANIFEST_JSON}" | docker exec -i "${CONTAINER_NAME}" tee "/media/config-exports/${TS}/manifest.json" >/dev/null

docker run --rm -v "${AUTH_DIR}:/target" alpine:3.20 sh -lc "cp -a /target/media/config-exports/${TS}/. /target/config-exports/${TS}/"

echo "Export complete: ${EXPORT_DIR}"
