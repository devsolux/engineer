#!/usr/bin/env bash
# Fixture contract for scripts/plan-fleet-status.sh: policy-driven repo walk,
# non-terminal aggregation, claim-collision / stale-stream / orphaned-branch
# findings, --json shape, and graceful degrade without a control plane.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLEET="$ROOT/scripts/plan-fleet-status.sh"
SAMPLE="$ROOT/templates/plan.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

WS="$TMP/workspace"
# Control-plane repo name is parameterized (ENGINEER_CONTROL_PLANE_REPO, default control-plane)
CP="${ENGINEER_CONTROL_PLANE_REPO:-control-plane}"
mkdir -p "$WS/$CP/config" "$WS/alpha/.engineer/plans" "$WS/beta/.engineer"
cat > "$WS/$CP/config/workspace-policy.json" <<'JSON'
{
  "canonical_repositories": ["alpha", "beta", "missing-repo", "alpha-wt", "gamma"],
  "repo_ventures": {"alpha": "venture-a"}
}
JSON

mkplan() { # dest stream status extra-python
  python3 - "$SAMPLE" "$1" "$2" "$3" "$4" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
d["stream"] = sys.argv[3]
d["status"] = sys.argv[4]
d.pop("integration", None)
exec(sys.argv[5], {"d": d})
json.dump(d, open(sys.argv[2], "w"))
PY
}

mkplan "$WS/alpha/.engineer/plans/stream-one.json" stream-one approved 'd["files_touch"]=["src/app.ts","src/db.ts"]'
mkplan "$WS/alpha/.engineer/plans/stream-two.json" stream-two in_progress 'd["files_touch"]=["src/app.ts"]; d["integration"]={"branch":"plan/stream-two","base":"main"}'
mkplan "$WS/alpha/.engineer/plans/finished.json" finished done 'd["files_touch"]=["src/old.ts"]'
mkplan "$WS/alpha/.engineer/plans/cancelled.json" cancelled cancelled 'd["files_touch"]=["src/app.ts"]'
mkplan "$WS/beta/.engineer/plan.json" beta-work draft 'd["files_touch"]=["lib/x.py"]'
# stale stream: mtime 10 days ago
touch -t "$(date -v-10d +%Y%m%d%H%M 2>/dev/null || date -d '10 days ago' +%Y%m%d%H%M)" \
  "$WS/beta/.engineer/plan.json"
# orphaned plan/ branch in a git repo with no matching plan
git -C "$WS/alpha" init -q
git -C "$WS/alpha" -c user.email=t@t -c user.name=t commit -q --no-gpg-sign --allow-empty -m base
git -C "$WS/alpha" branch plan/ghost
git -C "$WS/alpha" branch plan/stream-two
git -C "$WS/alpha" remote add origin https://example.com/team/alpha.git
# linked worktree listed as its own canonical entry: must resolve to alpha's anchor,
# never aggregate its branch-checkout .engineer/ (no double-counting)
git -C "$WS/alpha" worktree add -q "$WS/alpha-wt" plan/stream-two
# duplicate full clone: same origin URL, different path, no shared common dir
mkdir -p "$WS/gamma"
git -C "$WS/gamma" init -q
git -C "$WS/gamma" -c user.email=t@t -c user.name=t commit -q --no-gpg-sign --allow-empty -m base
git -C "$WS/gamma" remote add origin https://example.com/team/alpha.git

OUT="$(bash "$FLEET" --root "$WS")"
echo "$OUT" | grep -q "stream-one" || { echo "missing stream-one row" >&2; exit 1; }
echo "$OUT" | grep -q "venture-a" || { echo "missing venture mapping" >&2; exit 1; }
echo "$OUT" | grep -q "plan/stream-two" || { echo "missing branch column" >&2; exit 1; }
echo "$OUT" | grep -q "finished" && { echo "terminal plan must not appear" >&2; exit 1; }
echo "$OUT" | grep -q "cancelled" && { echo "cancelled plan must not appear" >&2; exit 1; }
echo "$OUT" | grep -q "claim-collision" || { echo "missing claim-collision finding" >&2; exit 1; }
echo "$OUT" | grep -q "stale-stream" || { echo "missing stale-stream finding" >&2; exit 1; }
echo "$OUT" | grep -q "plan/ghost: no matching plan" || { echo "missing orphaned-branch finding" >&2; exit 1; }
echo "$OUT" | grep -q "plan/stream-two: no matching plan" && { echo "active branch wrongly orphaned" >&2; exit 1; }
echo "$OUT" | grep -q "STALE" || { echo "missing STALE freshness flag" >&2; exit 1; }
echo "$OUT" | grep -q "duplicate-clone" || { echo "missing duplicate-clone finding" >&2; exit 1; }
echo "$OUT" | grep -Eq "worktree-entry|shared-anchor" || { echo "missing worktree/shared-anchor finding" >&2; exit 1; }

# --json: parses, carries plans + findings, venture unknown fallback for beta
bash "$FLEET" --root "$WS" --json > "$TMP/fleet.json"
python3 - "$TMP/fleet.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["repos_scanned"] == ["alpha", "beta"], d["repos_scanned"]
assert len(d["active_plans"]) == 3, [p["stream"] for p in d["active_plans"]]
beta = [p for p in d["active_plans"] if p["repo"] == "beta"][0]
assert beta["venture"] == "unknown", beta["venture"]
kinds = {f["kind"] for f in d["findings"]}
assert {"claim-collision", "stale-stream", "orphaned-branch"} <= kinds, kinds
PY

# graceful degrade: no control plane → directory scan, ventures n/a
rm "$WS/$CP/config/workspace-policy.json"
bash "$FLEET" --root "$WS" --json > "$TMP/fleet-degraded.json"
python3 - "$TMP/fleet-degraded.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["policy_source"] is None
assert set(d["repos_scanned"]) == {"alpha", "beta"}, d["repos_scanned"]
assert all(p["venture"] == "n/a" for p in d["active_plans"])
PY

# read-only: table and --json modes must not write into the workspace
[ ! -f "$WS/$CP/data/plan-fleet.json" ] || { echo "non-snapshot mode wrote a file" >&2; exit 1; }

echo "plan fleet fixtures passed"
