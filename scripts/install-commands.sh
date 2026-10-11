#!/usr/bin/env bash
# Install native Engineer command aliases. Use --help for hosts and scope.
set -euo pipefail
ENGINEER_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ENGINEER_ROOT/scripts/install-command-aliases.py" "$@"
