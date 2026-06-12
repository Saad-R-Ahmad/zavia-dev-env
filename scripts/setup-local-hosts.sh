#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <server-lan-ip>"
  exit 1
fi

IP="$1"

cat <<EOF
Add the following entries to your client hosts file:
$IP traefik.zavia.local
$IP auth.zavia.local
$IP pgadmin.zavia.local
$IP uns.zavia.local
$IP influxdb.zavia.local
EOF
