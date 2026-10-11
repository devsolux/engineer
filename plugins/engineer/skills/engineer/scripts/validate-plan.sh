#!/usr/bin/env bash
# Validate engineer plan artifacts (Plan → Validate → Execute).
# Usage: bash scripts/validate-plan.sh path/to/plan.json     # single plan (CI-stable)
#        bash scripts/validate-plan.sh --all [repo-root]     # every plan under .engineer/
#                                                            # (plan.json + plans/*.json)
#        bash scripts/validate-plan.sh --completion <plan> [--warn-only]
#                                                            # drift gate: changed files vs
#                                                            # declared files_touch
# Host-neutral: bare shell + python3 + plain git only; no host features, no network.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA="$ROOT/templates/plan-artifact.schema.json"

validate_one() {
  local plan="$1"
  python3 - "$plan" "$SCHEMA" <<'PY'
import datetime, json, re, subprocess, sys
from pathlib import Path

plan_path, schema_path = sys.argv[1], sys.argv[2]
plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
# Lightweight structural validation (no jsonschema dep required)
errors = []

def req(obj, *keys, path=""):
    for k in keys:
        if k not in obj or obj[k] in (None, "", []):
            errors.append(f"missing or empty: {path}{k}")

VALID_STATUS = {"draft", "approved", "executing", "in_progress", "done", "verified", "completed", "cancelled", "abandoned", "superseded"}
TERMINAL = {"done", "verified", "completed", "cancelled", "abandoned", "superseded"}

req(plan, "schema_version", "kind", "title", "status")
if plan.get("schema_version") != 2:
    errors.append("schema_version must be 2")
kind = plan.get("kind")
if kind not in ("feature", "schema", "scan-fix", "ship"):
    errors.append(f"invalid kind: {kind}")
status = plan.get("status")
if status and status not in VALID_STATUS:
    errors.append(f"invalid status: {status} (allowed: {', '.join(sorted(VALID_STATUS))})")

# Lifecycle fields (all optional/additive; validated only when present)
stream = plan.get("stream")
if stream is not None:
    if not isinstance(stream, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", stream):
        errors.append("stream must be a lowercase slug ([a-z0-9-])")
    else:
        p = Path(plan_path)
        if p.parent.name == "plans" and stream != p.stem:
            errors.append(f"stream {stream!r} must equal the plans/ file slug {p.stem!r}")
origin = plan.get("origin")
if origin is not None and origin not in ("planned", "adopted-mid-session", "sidequest"):
    errors.append("origin must be 'planned', 'adopted-mid-session', or 'sidequest'")
resume = plan.get("resume_context")
if resume is not None and (not isinstance(resume, str) or len(resume.strip()) < 10):
    errors.append("resume_context must be a meaningful string (>=10 chars)")
if origin == "adopted-mid-session" and (not isinstance(resume, str) or len(resume.strip()) < 10):
    errors.append("adopted-mid-session plan requires resume_context capturing the work already done")
interrupts = plan.get("interrupts")
if interrupts is not None:
    if not isinstance(interrupts, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", interrupts):
        errors.append("interrupts must be the parent stream's lowercase slug")
    if origin != "sidequest":
        errors.append("interrupts is valid only with origin 'sidequest' (general plan hierarchy is unsupported)")
if origin == "sidequest" and interrupts is None:
    print("WARN: sidequest plan does not name the halted parent stream in 'interrupts'", file=sys.stderr)
notes = plan.get("session_notes")
if notes is not None and (not isinstance(notes, list) or any(not isinstance(x, str) or not x.strip() for x in notes)):
    errors.append("session_notes must be a list of non-empty strings")
superseded_by = plan.get("superseded_by")
if superseded_by is not None and (not isinstance(superseded_by, str) or not superseded_by.strip()):
    errors.append("superseded_by must name the successor plan (path or slug)")
acceptance = plan.get("acceptance_criteria")
if acceptance is not None and (not isinstance(acceptance, list) or not acceptance or any(not isinstance(x, str) or not x.strip() for x in acceptance)):
    errors.append("acceptance_criteria must be a non-empty list of strings")
for ts in ("verified_at", "completed_at"):
    if plan.get(ts) is not None and not isinstance(plan.get(ts), str):
        errors.append(f"{ts} must be a string timestamp")
verification = plan.get("verification")
if verification is not None:
    if not isinstance(verification, dict):
        errors.append("verification must be an object {result, evidence[, verified_at, notes]}")
    else:
        if verification.get("result") not in ("passed", "failed", "partial", "cancelled"):
            errors.append("verification.result must be passed|failed|partial|cancelled")
        ev = verification.get("evidence")
        if not isinstance(ev, list) or not ev or any(not isinstance(x, str) or not x.strip() for x in ev):
            errors.append("verification.evidence must be a non-empty list of strings")
        if verification.get("notes") is not None and (not isinstance(verification["notes"], list) or any(not isinstance(x, str) for x in verification["notes"])):
            errors.append("verification.notes must be a list of strings")
        unknown = set(verification) - {"result", "evidence", "verified_at", "notes"}
        if unknown:
            errors.append(f"verification unknown keys: {sorted(unknown)}")
# Legacy improvised spellings (verification_result/verification_results/verification_notes/
# verification_evidence/top-level evidence) still validate but are deprecated; write
# the canonical verification object going forward.
# Advisory adoption nudge (measured: 0 of 78 valid control-plane terminal plans carried the formal
# object as of 2026-07-16; evidence was scattered across ad-hoc keys). Warning only - a
# terminal plan without the receipt stays valid. Abandoned/superseded plans claim no
# completed work, so only the completion statuses are nudged.
if status in ("done", "verified", "completed") and verification is None:
    alternates = [k for k in ("verification_result", "verification_results", "verification_evidence", "verification_notes", "evidence") if plan.get(k) is not None]
    hint = f" (non-canonical spelling(s) present: {', '.join(alternates)})" if alternates else ""
    print(f"WARN: terminal plan lacks the formal verification object {{result, evidence[, verified_at, notes]}}{hint} - record the completion receipt (advisory, never a failure)", file=sys.stderr)

# Branch-per-plan integration state (optional; workflows.md owns the rules)
integration = plan.get("integration")
if integration is not None:
    if not isinstance(integration, dict):
        errors.append("integration must be an object {branch, worktree, base, rebased_at, merge_commit, merged_at, disposition}")
    else:
        known = {"branch", "worktree", "base", "rebased_at", "merge_commit", "merged_at", "disposition"}
        unknown = set(integration) - known
        if unknown:
            errors.append(f"integration unknown keys: {sorted(unknown)}")
        for k in known:
            if integration.get(k) is not None and (not isinstance(integration[k], str) or not integration[k].strip()):
                errors.append(f"integration.{k} must be a non-empty string")
        disposition = integration.get("disposition")
        if disposition is not None and disposition not in ("merged", "parked", "discarded"):
            errors.append("integration.disposition must be merged|parked|discarded")
        if disposition == "merged" and not integration.get("merge_commit"):
            errors.append("integration.disposition 'merged' requires merge_commit")
        branch = integration.get("branch")
        if isinstance(branch, str) and isinstance(stream, str) and branch != f"plan/{stream}":
            print(f"WARN: integration.branch {branch!r} does not follow the plan/<stream> convention", file=sys.stderr)
        # Completion gate: a terminal plan may not leave its branch dangling.
        if status in ("done", "verified", "completed") and branch:
            if not (integration.get("merge_commit") or disposition in ("parked", "discarded")):
                errors.append("completion gate: terminal plan with integration.branch requires merge_commit (+ deleted branch) or disposition parked/discarded — orphaned plan/ branches are a finding")

if kind == "schema":
    req(plan, "tables", "rls_policies", "migrations", "tests", "risks")
    tables = {t.get("name") for t in plan.get("tables") or [] if isinstance(t, dict)}
    for pol in plan.get("rls_policies") or []:
        if not isinstance(pol, dict):
            continue
        t = pol.get("table")
        if t and tables and t not in tables:
            errors.append(f"rls_policies table not in tables[]: {t}")
    for t in tables:
        if t and not any(
            isinstance(p, dict) and p.get("table") == t for p in (plan.get("rls_policies") or [])
        ):
            errors.append(f"public table without rls_policies entry: {t}")

if kind == "scan-fix":
    findings = plan.get("findings") or []
    if not findings:
        errors.append("scan-fix requires findings[]")
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            errors.append(f"findings[{i}] not object")
            continue
        for k in ("file", "rule_id", "proposed_fix", "verify_command"):
            if not f.get(k):
                errors.append(f"findings[{i}].{k} required")

complexity = plan.get("complexity")
if plan.get("status") in ("approved", "executing", "in_progress", "done") and not isinstance(complexity, dict):
    errors.append("approved/executing/in_progress/done plan requires complexity receipt")
if complexity is not None:
    ckeys = {"need_now", "simplest_viable_design", "evidence", "new_abstractions", "new_runtime_components", "rejected_options", "reversibility", "solid_justifications"}
    if not isinstance(complexity, dict) or set(complexity) != ckeys:
        errors.append("complexity receipt keys invalid")
    else:
        for key in ("need_now", "simplest_viable_design"):
            if not isinstance(complexity.get(key), str) or len(complexity[key].strip()) < 10:
                errors.append(f"complexity.{key} must be meaningful")
        evidence = complexity.get("evidence")
        if not isinstance(evidence, list) or not evidence or any(not isinstance(x, str) or len(x.strip()) < 3 for x in evidence):
            errors.append("complexity.evidence requires current requirement or repository facts")
        for key in ("new_abstractions", "new_runtime_components"):
            if not isinstance(complexity.get(key), list) or any(not isinstance(x, str) or not x.strip() for x in complexity.get(key, [])):
                errors.append(f"complexity.{key} must be a string list")
        rejected = complexity.get("rejected_options")
        if not isinstance(rejected, list) or any(not isinstance(x, dict) or set(x) != {"option", "reason"} or not x["option"].strip() or not x["reason"].strip() for x in rejected):
            errors.append("complexity.rejected_options must bind each option to a reason")
        if complexity.get("new_runtime_components") and not rejected:
            errors.append("new runtime components require at least one simpler rejected option")
        reversibility = complexity.get("reversibility")
        if not isinstance(reversibility, dict) or set(reversibility) != {"class", "rollback", "decision_record"} or reversibility.get("class") not in {"reversible", "costly", "irreversible"} or not isinstance(reversibility.get("rollback"), str) or not reversibility["rollback"].strip():
            errors.append("complexity.reversibility invalid")
        elif reversibility["class"] in {"costly", "irreversible"} and (not isinstance(reversibility.get("decision_record"), str) or not reversibility["decision_record"].strip()):
            errors.append("costly or irreversible design requires a decision_record")
        solid = complexity.get("solid_justifications")
        valid_principles = {"SRP", "OCP", "LSP", "ISP", "DIP"}
        if not isinstance(solid, list) or any(not isinstance(x, dict) or set(x) != {"principle", "observed_pressure", "boundary"} or x.get("principle") not in valid_principles or not x.get("observed_pressure", "").strip() or not x.get("boundary", "").strip() for x in solid):
            errors.append("complexity.solid_justifications invalid")
        if complexity.get("new_abstractions") and not solid:
            errors.append("new abstractions require SOLID justification tied to observed pressure and boundary")

if plan.get("status") == "approved" and kind in ("schema", "feature", "scan-fix"):
    if not plan.get("verify_commands") and kind != "scan-fix":
        # soft: recommend verify_commands
        print("WARN: approved plan has no top-level verify_commands[]", file=sys.stderr)

# ── Advisory checks (warnings only; never a lock, never a failure) ──────────

def engineer_dir_of(path: Path):
    if path.parent.name == ".engineer":
        return path.parent
    if path.parent.name == "plans" and path.parent.parent.name == ".engineer":
        return path.parent.parent
    return None

def anchor_engineer(start: Path):
    """Coordination anchor: the PRIMARY worktree's .engineer/, resolved via plain git.

    Linked worktrees check out their own branch's copy of .engineer/, which is branch
    state, not coordination state — claims, activation classification, and fleet
    aggregation must all read the anchor, from any linked worktree or subdirectory."""
    try:
        r = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            common = Path(r.stdout.strip())
            if common.name == ".git" and common.parent.is_dir():
                return (common.parent / ".engineer").resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    return None

resolved = Path(plan_path).resolve()
engineer_dir = engineer_dir_of(resolved)
anchor = anchor_engineer(resolved.parent)
if engineer_dir is not None and anchor is not None and engineer_dir.resolve() != anchor:
    print(f"WARN: plan file lives outside the repo's coordination anchor {anchor} — a linked worktree's .engineer/ is a branch checkout, not coordination state; create and read plans at the primary worktree", file=sys.stderr)

# Claims check: two active plans claiming the same files in the repo's coordination
# .engineer (the primary-worktree anchor when resolvable, else this plan's own tree).
if engineer_dir is not None and anchor is not None and anchor.is_dir():
    engineer_dir = anchor
if status not in TERMINAL and engineer_dir is not None:
    mine = {f for f in (plan.get("files_touch") or []) if isinstance(f, str)}
    if mine:
        siblings = [engineer_dir / "plan.json"]
        siblings += sorted(engineer_dir.glob("plan-*.json"))
        plans_dir = engineer_dir / "plans"
        if plans_dir.is_dir():
            siblings += sorted(plans_dir.glob("*.json"))
        for sib in siblings:
            if not sib.is_file() or sib.resolve() == resolved:
                continue
            try:
                other = json.loads(sib.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(other, dict) or other.get("status") in TERMINAL:
                continue
            overlap = mine & {f for f in (other.get("files_touch") or []) if isinstance(f, str)}
            if overlap:
                shown = ", ".join(sorted(overlap)[:5]) + ("…" if len(overlap) > 5 else "")
                print(f"WARN: claims overlap with active plan {sib.name}: {shown} (advisory — coordinate streams, never a lock)", file=sys.stderr)

# Staleness: main moved significantly since approval of a non-terminal plan.
if status not in TERMINAL and isinstance(plan.get("approved_at"), str) and plan["approved_at"].strip():
    approved = None
    try:
        approved = datetime.datetime.fromisoformat(plan["approved_at"].replace("Z", "+00:00"))
    except ValueError:
        pass
    if approved is not None:
        if approved.tzinfo is None:
            approved = approved.replace(tzinfo=datetime.timezone.utc)
        def git(*args):
            return subprocess.run(["git", "-C", str(resolved.parent), *args], capture_output=True, text=True, timeout=10)
        try:
            inside = git("rev-parse", "--is-inside-work-tree")
            if inside.returncode == 0 and inside.stdout.strip() == "true":
                count = git("rev-list", "--count", "HEAD", "--since", approved.isoformat())
                last = git("log", "-1", "--format=%ct")
                commits = int(count.stdout.strip() or 0) if count.returncode == 0 else 0
                days = 0
                if last.returncode == 0 and last.stdout.strip():
                    last_dt = datetime.datetime.fromtimestamp(int(last.stdout.strip()), tz=datetime.timezone.utc)
                    days = (last_dt - approved).days
                if commits > 20 or days > 7:
                    print(f"WARN: stale plan — main moved since approved_at ({commits} commit(s), newest {days} day(s) after approval); re-validate scope", file=sys.stderr)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass

if errors:
    print("FAIL plan validation:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"OK plan valid kind={kind} status={plan.get('status')} title={plan.get('title')!r}")
PY
}

usage() {
  echo "Usage: validate-plan.sh <plan.json> | --all [repo-root] | --completion <plan.json> [--warn-only]"
}

if [[ "${1:-}" == "--completion" ]]; then
  shift
  WARN_ONLY=0
  PLAN=""
  for arg in "$@"; do
    case "$arg" in
      --warn-only) WARN_ONLY=1 ;;
      *) PLAN="$arg" ;;
    esac
  done
  if [[ -z "$PLAN" || ! -f "$PLAN" ]]; then
    usage
    exit 2
  fi
  python3 - "$PLAN" "$WARN_ONLY" <<'PY'
# Drift gate: the diff a completion claims must stay inside the plan's declared
# files_touch (evidence: removing scope declarations raised out-of-scope actions
# from 0% to 17% in published evals). .engineer/ lifecycle artifacts are always
# in scope; everything else must be declared.
import json, subprocess, sys
from pathlib import Path

plan_path = Path(sys.argv[1]).resolve()
warn_only = sys.argv[2] == "1"
plan = json.loads(plan_path.read_text(encoding="utf-8"))
label = "WARN" if warn_only else "FAIL"
rc = 0 if warn_only else 1

declared = [f for f in (plan.get("files_touch") or []) if isinstance(f, str) and f.strip()]
if not declared:
    print(f"{label} completion drift gate: plan declares no files_touch — the gate needs declared scope")
    sys.exit(rc)

def git(*args):
    return subprocess.run(["git", "-C", str(plan_path.parent), *args], capture_output=True, text=True, timeout=30)

top = git("rev-parse", "--show-toplevel")
if top.returncode != 0:
    print("completion drift gate: not inside a git repository (the gate compares git diffs)", file=sys.stderr)
    sys.exit(2)
root = Path(top.stdout.strip())

def porcelain_paths():
    out = git("status", "--porcelain")
    paths = set()
    for line in out.stdout.splitlines():
        if len(line) < 4:
            continue
        entry = line[3:]
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        paths.add(entry.strip().strip('"'))
    return paths

changed = set()
integration = plan.get("integration") if isinstance(plan.get("integration"), dict) else {}
branch = integration.get("branch")
if branch:
    # Branch refs are repo-global (shared through the git common dir), so this
    # works from the primary worktree even when the work happens in a linked
    # worktree. Fall back to HEAD if the branch ref is gone.
    tip = branch if git("rev-parse", "--verify", "--quiet", branch).returncode == 0 else "HEAD"
    base = integration.get("base") or "main"
    mb = git("merge-base", base, tip)
    base_ref = mb.stdout.strip() if mb.returncode == 0 and mb.stdout.strip() else base
    diff = git("diff", "--name-only", f"{base_ref}..{tip}")
    if diff.returncode != 0:
        print(f"completion drift gate: cannot diff {base!r}..{tip!r}: {diff.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    changed |= {l.strip() for l in diff.stdout.splitlines() if l.strip()}
# Uncommitted work counts in both modes (staged + unstaged + untracked).
changed |= porcelain_paths()

def allowed(f: str) -> bool:
    if f.startswith(".engineer/"):
        return True  # plan/receipt lifecycle artifacts
    for entry in declared:
        e = entry.strip()
        while e.startswith("./"):
            e = e[2:]
        if f == e or (e.endswith("/") and f.startswith(e)):
            return True
    return False

out_of_scope = sorted(f for f in changed if not allowed(f))
if out_of_scope:
    print(f"{label} completion drift gate: {len(out_of_scope)} changed file(s) outside declared files_touch:")
    for f in out_of_scope:
        print(f"  - {f}")
    print("  → extend the plan scope (with approval) or revert the out-of-scope changes before marking done")
    sys.exit(rc)
print(f"OK completion drift gate: {len(changed)} changed file(s), all within declared scope")
PY
  exit $?
fi

if [[ "${1:-}" == "--all" ]]; then
  TARGET="${2:-.}"
  if [[ "$(basename "$TARGET")" == ".engineer" ]]; then
    ENGINEER_DIR="$TARGET"   # explicit .engineer path: caller's choice wins
  else
    # Coordination anchor: the PRIMARY worktree's .engineer/. From a linked worktree
    # or subdirectory cwd, plain git walks up; a linked worktree's own .engineer/ is
    # a branch checkout, not coordination state.
    COMMON="$(git -C "$TARGET" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
    if [[ "$COMMON" == */.git && -d "${COMMON%/.git}" ]]; then
      PRIMARY="${COMMON%/.git}"
      ENGINEER_DIR="$PRIMARY/.engineer"
      if [[ "$(cd "$TARGET" 2>/dev/null && pwd -P)" != "$PRIMARY" ]]; then
        echo "note: coordination anchor resolved to primary worktree: $ENGINEER_DIR" >&2
      fi
    else
      ENGINEER_DIR="$TARGET/.engineer"
    fi
  fi
  if [[ ! -d "$ENGINEER_DIR" ]]; then
    echo "No .engineer directory at: $ENGINEER_DIR" >&2
    exit 2
  fi
  PLANS=()
  [[ -f "$ENGINEER_DIR/plan.json" ]] && PLANS+=("$ENGINEER_DIR/plan.json")
  if [[ -d "$ENGINEER_DIR/plans" ]]; then
    while IFS= read -r f; do PLANS+=("$f"); done \
      < <(find "$ENGINEER_DIR/plans" -maxdepth 1 -name '*.json' -type f | sort)
  fi
  if [[ ${#PLANS[@]} -eq 0 ]]; then
    echo "OK no plans found under $ENGINEER_DIR (plan.json, plans/*.json)"
    exit 0
  fi
  FAILED=0
  for f in "${PLANS[@]}"; do
    echo "== $f"
    validate_one "$f" || FAILED=$((FAILED + 1))
  done
  # Hygiene (advisory): .engineer/ holds plan/receipt artifacts only, and terminal
  # receipts older than 30 days belong in .engineer/plans/archive/ (workflows.md).
  JUNK=$( { find "$ENGINEER_DIR" -maxdepth 1 -type f ! -name '*.json' 2>/dev/null; \
            [[ -d "$ENGINEER_DIR/plans" ]] && find "$ENGINEER_DIR/plans" -maxdepth 1 -type f ! -name '*.json' 2>/dev/null; } | sort || true)
  if [[ -n "$JUNK" ]]; then
    echo "WARN: non-plan junk in .engineer/ (plan/receipt artifacts only — move or delete):" >&2
    echo "$JUNK" | sed 's/^/  - /' >&2
  fi
  TERMINAL_N=$(python3 - "$ENGINEER_DIR" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
TERMINAL = {"done", "verified", "completed", "abandoned", "superseded"}
count = 0
candidates = [d / "plan.json", *sorted(d.glob("plan-*.json"))]
plans = d / "plans"
if plans.is_dir():
    candidates += sorted(plans.glob("*.json"))
for f in candidates:
    if not f.is_file():
        continue
    try:
        if json.loads(f.read_text(encoding="utf-8")).get("status") in TERMINAL:
            count += 1
    except (json.JSONDecodeError, OSError):
        pass
print(count)
PY
)
  if [[ "$TERMINAL_N" -gt 20 ]]; then
    echo "WARN: $TERMINAL_N unarchived terminal plan(s) — move receipts older than 30 days to $ENGINEER_DIR/plans/archive/" >&2
  fi
  echo "--"
  if [[ $FAILED -gt 0 ]]; then
    echo "FAIL $FAILED of ${#PLANS[@]} plan(s) invalid"
    exit 1
  fi
  echo "OK all ${#PLANS[@]} plan(s) valid"
  exit 0
fi

PLAN="${1:-}"
if [[ -z "$PLAN" || ! -f "$PLAN" ]]; then
  usage
  exit 2
fi
validate_one "$PLAN"
