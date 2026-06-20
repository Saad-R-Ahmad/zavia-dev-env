#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Compatibility wrapper: keep this script name working.
exec "${SCRIPT_DIR}/start-dev.sh" "${1:-all}"
