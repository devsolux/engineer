#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAMPLE="$ROOT/templates/plan.sample.json"
VALIDATOR="$ROOT/scripts/validate-plan.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

bash "$VALIDATOR" "$SAMPLE" >/dev/null

mutate() {
  local name="$1" expression="$2"
  python3 - "$SAMPLE" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if bash "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected plan complexity rejection: $name" >&2
    exit 1
  fi
}

mutate old_schema 'd["schema_version"]=1'
mutate invalid_status 'd["status"]="in-review"'
mutate invalid_origin 'd["origin"]="retroactive"'
mutate adopted_without_resume 'd["origin"]="adopted-mid-session"'
mutate bad_stream_slug 'd["stream"]="Signup Analytics"'
mutate empty_superseded_by 'd["superseded_by"]="  "'
mutate interrupts_without_sidequest 'd["interrupts"]="main-stream"'
mutate bad_interrupts_slug 'd["origin"]="sidequest"; d["interrupts"]="Main Stream"'
mutate integration_unknown_key 'd["integration"]={"branch":"plan/x","note":"y"}'
mutate bad_disposition 'd["integration"]={"branch":"plan/x","disposition":"kept"}'
mutate merged_without_commit 'd["integration"]={"branch":"plan/x","disposition":"merged"}'
mutate done_branch_dangling 'd["status"]="done"; d["integration"]={"branch":"plan/signup-activation-analytics","base":"main"}'
mutate bad_verification 'd["verification"]={"result":"passed","evidence":[]}'
mutate verification_unknown_key 'd["verification"]={"result":"passed","evidence":["typecheck green"],"receipt":"x"}'
mutate approved_without_receipt 'd["status"]="approved"; d.pop("complexity")'
mutate no_current_evidence 'd["complexity"]["evidence"]=[]'
mutate abstraction_without_pressure 'd["complexity"]["new_abstractions"]=["AnalyticsRepository"]'
mutate runtime_without_simpler_option 'd["complexity"]["new_runtime_components"]=["Kafka"] ; d["complexity"]["rejected_options"]=[]'
mutate irreversible_without_adr 'd["complexity"]["reversibility"]={"class":"irreversible","rollback":"Restore backup","decision_record":None}'
mutate invalid_solid 'd["complexity"]["solid_justifications"]=[{"principle":"DRY","observed_pressure":"duplicate","boundary":"module"}]'

# Lifecycle positives: new optional fields validate; stream must match plans/ slug.
mkdir -p "$TMP/repo/.engineer/plans"
python3 - "$SAMPLE" "$TMP/repo/.engineer/plans/second-stream.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d.update(stream="second-stream", origin="adopted-mid-session",
         resume_context="Auth middleware refactor already touched 3 files; typecheck green; next step: session cookie tests.",
         session_notes=["2026-07-16: adopted mid-session after engineer update landed"],
         verification={"result":"passed","evidence":["typecheck green","scan strict clean"],"verified_at":"2026-07-16"})
d.pop("integration", None)
json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
bash "$VALIDATOR" "$TMP/repo/.engineer/plans/second-stream.json" >/dev/null

python3 -c "
import json; d=json.load(open('$TMP/repo/.engineer/plans/second-stream.json'))
d['stream']='other-slug'; json.dump(d,open('$TMP/repo/.engineer/plans/second-stream.json','w'))
"
if bash "$VALIDATOR" "$TMP/repo/.engineer/plans/second-stream.json" >/dev/null 2>&1; then
  echo "expected stream/filename slug mismatch rejection" >&2
  exit 1
fi
python3 -c "
import json; d=json.load(open('$TMP/repo/.engineer/plans/second-stream.json'))
d['stream']='second-stream'; json.dump(d,open('$TMP/repo/.engineer/plans/second-stream.json','w'))
"

# Cancelled plans are terminal: their cancellation receipt validates and their
# file claims do not collide with active work.
mkdir -p "$TMP/cancel-repo/.engineer/plans"
python3 - "$SAMPLE" "$TMP/cancel-repo/.engineer/plans/active.json" "$TMP/cancel-repo/.engineer/plans/cancelled.json" <<'PY'
import json,sys
active=json.load(open(sys.argv[1]))
active.update(stream="active", status="approved", files_touch=["src/shared.py"])
active.pop("integration",None)
cancelled=dict(active)
cancelled.update(stream="cancelled", status="cancelled",
                 verification={"result":"cancelled","evidence":["Owner stopped before implementation"]})
json.dump(active,open(sys.argv[2],"w"),indent=2)
json.dump(cancelled,open(sys.argv[3],"w"),indent=2)
PY
bash "$VALIDATOR" "$TMP/cancel-repo/.engineer/plans/cancelled.json" >/dev/null
CANCEL_OUT=$(bash "$VALIDATOR" "$TMP/cancel-repo/.engineer/plans/active.json" 2>&1)
if echo "$CANCEL_OUT" | grep -q "WARN: claims overlap"; then
  echo "cancelled plan must not contribute claim overlap" >&2
  exit 1
fi

# --all: default plan.json + plans/*.json in one pass; one broken member fails the run.
cp "$SAMPLE" "$TMP/repo/.engineer/plan.json"
bash "$VALIDATOR" --all "$TMP/repo" >/dev/null
bash "$VALIDATOR" --all "$TMP/repo/.engineer" >/dev/null
python3 -c "
import json; d=json.load(open('$TMP/repo/.engineer/plans/second-stream.json'))
d['status']='approved'; d.pop('complexity'); json.dump(d,open('$TMP/repo/.engineer/plans/broken.json','w'))
"
if bash "$VALIDATOR" --all "$TMP/repo" >/dev/null 2>&1; then
  echo "expected --all to fail on one broken plan" >&2
  exit 1
fi
rm -f "$TMP/repo/.engineer/plans/broken.json"

# Integration positives: merged and parked completions pass the completion gate;
# a sidequest plan validates with its interrupts parent link.
python3 - "$SAMPLE" "$TMP/merged_done.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d["status"]="done"
d["integration"]={"branch":"plan/signup-activation-analytics","base":"main",
                  "rebased_at":"2026-07-16","merge_commit":"abc1234","merged_at":"2026-07-16",
                  "disposition":"merged"}
json.dump(d,open(sys.argv[2],"w"))
PY
bash "$VALIDATOR" "$TMP/merged_done.json" >/dev/null
python3 - "$SAMPLE" "$TMP/parked_done.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d["status"]="done"
d["integration"]={"branch":"plan/signup-activation-analytics","base":"main","disposition":"parked"}
json.dump(d,open(sys.argv[2],"w"))
PY
bash "$VALIDATOR" "$TMP/parked_done.json" >/dev/null
python3 - "$SAMPLE" "$TMP/repo/.engineer/plans/hotfix-detour.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d.update(stream="hotfix-detour", origin="sidequest", interrupts="second-stream",
         resume_context="Sidequest opened by user; parent second-stream halted at cookie tests.")
d.pop("integration",None)
json.dump(d,open(sys.argv[2],"w"))
PY
bash "$VALIDATOR" "$TMP/repo/.engineer/plans/hotfix-detour.json" >/dev/null

# Verification-receipt nudge: a done/verified/completed plan without the formal
# verification object warns but stays valid (advisory, exit 0); a terminal plan
# carrying the object, and a non-terminal plan without it, stay silent.
python3 - "$TMP/merged_done.json" "$TMP/terminal_no_verification.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d.pop("verification",None)
json.dump(d,open(sys.argv[2],"w"))
PY
NUDGE_OUT=$(bash "$VALIDATOR" "$TMP/terminal_no_verification.json" 2>&1)
echo "$NUDGE_OUT" | grep -q "WARN: terminal plan lacks the formal verification object" || {
  echo "expected terminal-without-verification advisory warning" >&2
  exit 1
}
python3 - "$TMP/merged_done.json" "$TMP/terminal_with_verification.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d["verification"]={"result":"passed","evidence":["typecheck green"],"verified_at":"2026-07-17"}
json.dump(d,open(sys.argv[2],"w"))
PY
WITH_OUT=$(bash "$VALIDATOR" "$TMP/terminal_with_verification.json" 2>&1)
if echo "$WITH_OUT" | grep -q "WARN: terminal plan lacks"; then
  echo "unexpected verification warning on receipt-carrying terminal plan" >&2
  exit 1
fi
ACTIVE_OUT=$(bash "$VALIDATOR" "$SAMPLE" 2>&1)
if echo "$ACTIVE_OUT" | grep -q "WARN: terminal plan lacks"; then
  echo "unexpected verification warning on non-terminal plan" >&2
  exit 1
fi

# Claims check: two active plans claiming the same file warn (advisory, exit 0).
CLAIM_OUT=$(bash "$VALIDATOR" "$TMP/repo/.engineer/plans/second-stream.json" 2>&1)
echo "$CLAIM_OUT" | grep -q "WARN: claims overlap" || {
  echo "expected advisory claims-overlap warning" >&2
  exit 1
}

# Drift gate: out-of-scope changes fail --completion; --warn-only stays advisory.
GITREPO="$TMP/gitrepo"
mkdir -p "$GITREPO/.engineer"
git -C "$GITREPO" init -q
git -C "$GITREPO" -c user.email=t@t -c user.name=t commit -q --no-gpg-sign --allow-empty -m base
echo a > "$GITREPO/a.txt"
echo b > "$GITREPO/b.txt"
python3 - "$SAMPLE" "$GITREPO/.engineer/plan.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d["files_touch"]=["a.txt"]
d.pop("integration",None)
json.dump(d,open(sys.argv[2],"w"))
PY
if bash "$VALIDATOR" --completion "$GITREPO/.engineer/plan.json" >/dev/null 2>&1; then
  echo "expected --completion drift-gate failure on out-of-scope b.txt" >&2
  exit 1
fi
bash "$VALIDATOR" --completion "$GITREPO/.engineer/plan.json" --warn-only >/dev/null
rm "$GITREPO/b.txt"
bash "$VALIDATOR" --completion "$GITREPO/.engineer/plan.json" >/dev/null

# Staleness: non-terminal plan approved long before the newest commit warns.
python3 - "$GITREPO/.engineer/plan.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d["status"]="approved"; d["approved_at"]="2020-01-01T00:00:00+00:00"
json.dump(d,open(sys.argv[1],"w"))
PY
STALE_OUT=$(bash "$VALIDATOR" "$GITREPO/.engineer/plan.json" 2>&1)
echo "$STALE_OUT" | grep -q "WARN: stale plan" || {
  echo "expected stale-plan warning for ancient approved_at" >&2
  exit 1
}

# Coordination anchor: from a linked worktree or subdirectory, plans resolve to the
# PRIMARY worktree's .engineer/; a linked worktree's .engineer/ is a branch checkout.
WTREPO="$TMP/wtrepo"
mkdir -p "$WTREPO/.engineer/plans" "$WTREPO/sub"
cp "$SAMPLE" "$WTREPO/.engineer/plan.json"
git -C "$WTREPO" init -q
git -C "$WTREPO" -c user.email=t@t -c user.name=t add .engineer
git -C "$WTREPO" -c user.email=t@t -c user.name=t commit -q --no-gpg-sign -m base
git -C "$WTREPO" worktree add -q "$TMP/linked-wt" -b side
python3 - "$SAMPLE" "$WTREPO/.engineer/plans/anchor-stream.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
d["stream"]="anchor-stream"; d.pop("integration",None)
json.dump(d,open(sys.argv[2],"w"))
PY
# a plan created at the anchor (even uncommitted) is visible when validating from
# the linked worktree and from a subdirectory cwd
ANCHOR_OUT=$(bash "$VALIDATOR" --all "$TMP/linked-wt" 2>&1)
echo "$ANCHOR_OUT" | grep -q "coordination anchor resolved" || {
  echo "expected anchor-resolution note from linked worktree" >&2
  exit 1
}
echo "$ANCHOR_OUT" | grep -q "anchor-stream.json" || {
  echo "expected anchor plan visible from linked worktree" >&2
  exit 1
}
SUB_OUT=$(bash "$VALIDATOR" --all "$WTREPO/sub" 2>/dev/null)
echo "$SUB_OUT" | grep -q "anchor-stream.json" || {
  echo "expected anchor plan visible from subdirectory cwd" >&2
  exit 1
}
# validating the linked worktree's own .engineer checkout warns: branch state, not
# coordination state
WT_WARN=$(bash "$VALIDATOR" "$TMP/linked-wt/.engineer/plan.json" 2>&1)
echo "$WT_WARN" | grep -q "outside the repo's coordination anchor" || {
  echo "expected outside-anchor warning for linked-worktree plan file" >&2
  exit 1
}

# Hygiene: --all warns on non-plan junk files but still exits 0.
echo scratch > "$TMP/repo/.engineer/notes.txt"
HYGIENE_OUT=$(bash "$VALIDATOR" --all "$TMP/repo" 2>&1)
echo "$HYGIENE_OUT" | grep -q "WARN: non-plan junk" || {
  echo "expected non-plan junk hygiene warning" >&2
  exit 1
}

echo "plan complexity fixtures passed"
