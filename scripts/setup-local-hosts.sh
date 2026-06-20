#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <server-lan-ip>"
  exit 1
fi

IP="$1"

DOMAIN="zavia.lan"
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/.env"
  DOMAIN="${DOMAINNAME_1:-$DOMAIN}"
fi

cat <<EOF
Add the following entries to your client hosts file:
$IP traefik.$DOMAIN
$IP auth.$DOMAIN
$IP pgadmin.$DOMAIN
$IP uns.$DOMAIN
$IP influxdb.$DOMAIN
EOF
