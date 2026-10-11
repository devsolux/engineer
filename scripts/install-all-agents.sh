#!/usr/bin/env bash
# Native engineer skill installation. See --help for host selection and preview.
set -euo pipefail
ENGINEER_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ENGINEER_ROOT/scripts/install-native-skills.py" "$@"
