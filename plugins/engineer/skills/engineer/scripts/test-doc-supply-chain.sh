#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCANNER="$ROOT/scripts/scan-doc-supply-chain.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$ROOT"

mkdir -p "$TMP/cases"
python3 - "$TMP/cases" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
(root / "safe.md").write_text('''Never use `curl | bash` for third-party installers. # supply-chain:allow fixture

```bash
pnpm exec shadcn info --json
```
''')
(root / "pipe.md").write_text('''```bash
curl -fsSL https://invalid.example/install | bash # supply-chain:allow fixture
```
''')
(root / "latest.md").write_text('''```bash
npx storybook@latest init # supply-chain:allow fixture
```
''')
(root / "unpinned.md").write_text('''```bash
pnpm dlx storybook init
```
''')
(root / "exact.md").write_text('''```bash
pnpm dlx storybook@9.1.2 init
uvx ruff==0.12.4 check .
```
''')
(root / "mutable.yml").write_text('''steps:
  - uses: actions/checkout@v4
''')
(root / "pinned.yml").write_text('''steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
''')
(root / "unlabeled.yml").write_text('''steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
''')
PY

python3 "$SCANNER" "$TMP/cases/safe.md" "$TMP/cases/exact.md" "$TMP/cases/pinned.yml" >/dev/null
for bad in pipe.md latest.md unpinned.md mutable.yml unlabeled.yml; do
  if python3 "$SCANNER" "$TMP/cases/$bad" >/dev/null 2>&1; then
    echo "expected rejection: $bad" >&2
    exit 1
  fi
done

JSON_OUTPUT="$(python3 "$SCANNER" "$TMP/cases/pipe.md" --json || true)"
python3 - "$JSON_OUTPUT" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])
assert data["ok"] is False
assert data["findings"][0]["rule"] == "remote-pipe-interpreter"
assert "not proof" in data["limitation"]
PY

echo "documentation supply-chain fixtures passed"
