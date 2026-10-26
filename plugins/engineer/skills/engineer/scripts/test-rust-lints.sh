#!/usr/bin/env bash
# Prove that every lint in templates/rust/lints.toml fires, and nothing else, on the check crate.
# Usage: bash scripts/test-rust-lints.sh
#
# The crate is assembled in a temporary directory from scripts/fixtures/rust-lints/ plus the
# template files, so the fixture can never drift from the template. cargo clippy runs offline
# on a crate without dependencies. Without a Rust toolchain that has clippy the suite prints a
# skip notice and exits 0; that is not a pass for the fixture, only an honest absence.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIX="$ROOT/scripts/fixtures/rust-lints"
TPL="$ROOT/templates/rust"

echo "engineer test-rust-lints — lint template fixture"
echo "---"

if ! command -v cargo >/dev/null 2>&1 || ! cargo clippy --version >/dev/null 2>&1; then
  echo "  ⚠ cargo clippy unavailable; skipped the lint-fire fixture (install rustup with the clippy component to run it)"
  exit 0
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/crate/src"
cp "$FIX/src/lib.rs" "$WORK/crate/src/lib.rs"
cp "$TPL/clippy.toml" "$WORK/crate/clippy.toml"
{ cat "$FIX/Cargo.toml"; echo; cat "$TPL/lints.toml"; } > "$WORK/crate/Cargo.toml"
export CARGO_TARGET_DIR="$WORK/target"

if ! (cd "$WORK/crate" && cargo clippy --offline --all-targets --message-format=json \
      >"$WORK/clippy.json" 2>"$WORK/clippy.log"); then
  echo "  ✗ cargo clippy failed on the check crate"
  tail -20 "$WORK/clippy.log"
  exit 1
fi
echo "  ✓ cargo clippy ran offline ($(cargo clippy --version 2>/dev/null))"

python3 -I - "$WORK/clippy.json" "$FIX/src/lib.rs" "$TPL/lints.toml" <<'PY'
import json
import re
import sys
from pathlib import Path

out, src, table = (Path(p) for p in sys.argv[1:4])
NOTE = re.compile(r"#\[(?:warn|deny|forbid|expect)\(([^)]+)\)\]")


def lint_name(msg: dict) -> str | None:
    for child in msg.get("children", []):
        hit = NOTE.search(child.get("message", ""))
        if hit:
            return hit.group(1).strip()
    hit = NOTE.search(msg.get("rendered") or "")
    if hit:
        return hit.group(1).strip()
    code = (msg.get("code") or {}).get("code")
    if code == "E0133" and msg.get("level") == "warning":
        # rustc reports the unsafe_op_in_unsafe_fn lint under the E0133 error code.
        return "unsafe_op_in_unsafe_fn"
    return code


fired: dict[str, set[int]] = {}
for line in out.read_text(encoding="utf-8").splitlines():
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        continue
    if record.get("reason") != "compiler-message":
        continue
    msg = record["message"]
    if msg.get("level") not in {"warning", "error"} or not (msg.get("code") or {}).get("code"):
        continue
    name = lint_name(msg)
    if not name:
        continue
    spans = [s for s in msg.get("spans", []) if s.get("is_primary")]
    fired.setdefault(name, set()).add(spans[0]["line_start"] if spans else 0)

tagged = set(re.findall(r"// LINT: (\S+)", src.read_text(encoding="utf-8")))

# Every lint the template turns on must be covered by a tagged violation (drift check).
enabled: set[str] = set()
section = ""
for raw in table.read_text(encoding="utf-8").splitlines():
    head = re.match(r"^\[lints\.(rust|clippy)\]", raw)
    if head:
        section = head.group(1)
        continue
    item = re.match(r'^([a-z0-9_]+)\s*=\s*"warn"', raw)
    if item and section:
        enabled.add(("clippy::" if section == "clippy" else "") + item.group(1))

failures = 0
for name in sorted(enabled - tagged):
    print(f"  ✗ template enables {name} but the fixture has no tagged violation for it")
    failures += 1
for name in sorted(tagged - set(fired)):
    print(f"  ✗ tagged lint did not fire: {name}")
    failures += 1
for name in sorted(set(fired) - tagged):
    print(f"  ✗ untagged diagnostic fired: {name} at lines {sorted(fired[name])}")
    failures += 1
if failures == 0:
    print(f"  ✓ exactly the {len(tagged)} tagged lints fired; all {len(enabled)} enabled lints are covered")
    print("  ✓ allowed lints (expect_used, must_use_candidate, enum_glob_use, …) stayed silent")
sys.exit(1 if failures else 0)
PY
STATUS=$?
echo "---"
if [[ "$STATUS" -eq 0 ]]; then
  echo "OK — lint template fixture passed"
  exit 0
fi
echo "FAILED — lint template fixture"
exit 1
