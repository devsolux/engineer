#!/usr/bin/env bash
# Fleet overview: every non-terminal engineer plan across the canonical workspace repos.
# Read-only and host-neutral (bash + python3 + plain git); the orchestration layer's
# "who else is working here" fact source.
#
# Usage: bash scripts/plan-fleet-status.sh                # human table + findings
#        bash scripts/plan-fleet-status.sh --json         # same data as JSON on stdout
#        bash scripts/plan-fleet-status.sh --snapshot     # write JSON to
#                                                         # <workspace>/<control-plane>/data/plan-fleet.json
#                                                         # (control-plane snapshot-consumption
#                                                         # pattern: dashboards and agents read
#                                                         # snapshots, never rescan)
#        bash scripts/plan-fleet-status.sh --root <dir>   # override the workspace root
#
# Workspace root: --root, else $ENGINEER_WORKSPACE_ROOT, else $HOME/dev.
# Control-plane repo name: $ENGINEER_CONTROL_PLANE_REPO, else "control-plane".
# Repo list: <root>/<control-plane>/config/workspace-policy.json (canonical_repositories +
# repo_ventures). Degrades gracefully without the control plane: scans first-level
# directories under the root that carry a .engineer/, ventures reported as n/a.
set -euo pipefail

MODE=table
ROOT_DIR="${ENGINEER_WORKSPACE_ROOT:-$HOME/dev}"
CONTROL_PLANE_REPO="${ENGINEER_CONTROL_PLANE_REPO:-control-plane}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) MODE=json ;;
    --snapshot) MODE=snapshot ;;
    --root)
      [[ $# -ge 2 ]] || { echo "--root requires a directory" >&2; exit 2; }
      ROOT_DIR="$2"
      shift
      ;;
    *) echo "Usage: plan-fleet-status.sh [--json | --snapshot] [--root <workspace-root>]" >&2; exit 2 ;;
  esac
  shift
done

if [[ ! -d "$ROOT_DIR" ]]; then
  echo "Workspace root not found: $ROOT_DIR" >&2
  exit 2
fi

python3 - "$ROOT_DIR" "$MODE" "$CONTROL_PLANE_REPO" <<'PY'
import datetime, json, subprocess, sys, time
from pathlib import Path

root = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
control_plane = sys.argv[3]
TERMINAL = {"done", "verified", "completed", "cancelled", "abandoned", "superseded"}
STALE_DAYS = 7

policy_path = root / control_plane / "config" / "workspace-policy.json"
repos, ventures, policy_source = [], {}, None
if policy_path.is_file():
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        repos = [r for r in policy.get("canonical_repositories", []) if isinstance(r, str)]
        ventures = {k: v for k, v in (policy.get("repo_ventures") or {}).items() if isinstance(v, str)}
        policy_source = str(policy_path)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARN: cannot parse {policy_path}: {exc}", file=sys.stderr)
if not repos:  # graceful degrade: no control plane on this machine
    repos = sorted(p.name for p in root.iterdir() if p.is_dir() and (p / ".engineer").is_dir())

def git(repo_dir, *args):
    try:
        return subprocess.run(["git", "-C", str(repo_dir), *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None

def anchor_root(repo_dir):
    """Primary-worktree root via the git common dir. The anchor's .engineer/ is the
    repo's single coordination directory; a linked worktree's .engineer/ is a branch
    checkout and must not be aggregated (it would double-count committed plans)."""
    r = git(repo_dir, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if r is not None and r.returncode == 0:
        common = Path(r.stdout.strip())
        if common.name == ".git" and common.parent.is_dir():
            return common.parent.resolve()
    return None

def rel(f):
    try:
        return str(f.relative_to(root))
    except ValueError:  # anchor outside the workspace root
        return str(f)

now = time.time()
plans, findings, scanned = [], [], []
seen_anchors: dict = {}
origin_urls: dict = {}
for repo in repos:
    repo_dir = root / repo
    if not repo_dir.is_dir():
        continue
    # duplicate full clones share an origin URL but not a git common dir
    o = git(repo_dir, "remote", "get-url", "origin")
    if o is not None and o.returncode == 0 and o.stdout.strip():
        url = o.stdout.strip().rstrip("/").removesuffix(".git").lower()
        origin_urls.setdefault(url, []).append(repo)
    anchor = anchor_root(repo_dir)
    if anchor is not None and anchor != repo_dir.resolve():
        findings.append({"kind": "worktree-entry", "repo": repo,
                         "detail": f"linked worktree — coordination anchor is {anchor}/.engineer"})
    primary = anchor or repo_dir
    if primary in seen_anchors:
        findings.append({"kind": "shared-anchor", "repo": repo,
                         "detail": f"same primary worktree as {seen_anchors[primary]!r}; skipping duplicate aggregation"})
        continue
    seen_anchors[primary] = repo
    engineer = primary / ".engineer"
    if not engineer.is_dir():
        continue
    scanned.append(repo)
    repo_dir = primary
    venture = ventures.get(repo, "n/a" if policy_source is None else "unknown")
    candidates = [engineer / "plan.json", *sorted(engineer.glob("plan-*.json"))]
    plans_dir = engineer / "plans"
    if plans_dir.is_dir():
        candidates += sorted(p for p in plans_dir.glob("*.json") if p.parent.name != "archive")
    active_slugs, repo_active = set(), []
    for f in candidates:
        if not f.is_file():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            findings.append({"kind": "unparseable-plan", "repo": repo, "detail": rel(f)})
            continue
        if not isinstance(data, dict):
            continue
        status = data.get("status") or "?"
        slug = data.get("stream") or f.stem
        if status not in TERMINAL:
            age_days = round((now - f.stat().st_mtime) / 86400, 1)
            integration = data.get("integration") if isinstance(data.get("integration"), dict) else {}
            row = {
                "stream": slug,
                "repo": repo,
                "venture": venture,
                "title": (data.get("title") or "?"),
                "status": status,
                "branch": integration.get("branch") or "-",
                "claims": len(data.get("files_touch") or []),
                "age_days": age_days,
                "stale": age_days > STALE_DAYS,
                "path": rel(f),
            }
            plans.append(row)
            repo_active.append((f.name, {x for x in (data.get("files_touch") or []) if isinstance(x, str)}))
            if age_days > STALE_DAYS:
                findings.append({"kind": "stale-stream", "repo": repo, "detail": f"{slug}: untouched for {age_days} day(s)"})
        active_slugs.add(slug)
        if status not in TERMINAL or (isinstance(data.get("integration"), dict) and data["integration"].get("disposition") == "parked"):
            pass  # parked terminal plans legitimately keep their branch
    # claim collisions between active plans of the same repo (fleet-level visibility)
    for i in range(len(repo_active)):
        for j in range(i + 1, len(repo_active)):
            overlap = repo_active[i][1] & repo_active[j][1]
            if overlap:
                shown = ", ".join(sorted(overlap)[:5]) + ("…" if len(overlap) > 5 else "")
                findings.append({"kind": "claim-collision", "repo": repo,
                                 "detail": f"{repo_active[i][0]} ∩ {repo_active[j][0]}: {shown}"})
    # orphaned plan/ branches: branch exists, but no plan (or only a terminal,
    # non-parked plan) matches its slug
    refs = git(repo_dir, "for-each-ref", "refs/heads/plan/", "--format=%(refname:short)")
    if refs is not None and refs.returncode == 0:
        for branch in (l.strip() for l in refs.stdout.splitlines() if l.strip()):
            slug = branch.split("/", 1)[1]
            matching = None
            for f in candidates:
                if not f.is_file():
                    continue
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if isinstance(d, dict) and (d.get("stream") or f.stem) == slug:
                    matching = d
                    break
            if matching is None:
                findings.append({"kind": "orphaned-branch", "repo": repo, "detail": f"{branch}: no matching plan"})
            elif matching.get("status") in TERMINAL:
                integ = matching.get("integration") if isinstance(matching.get("integration"), dict) else {}
                if integ.get("disposition") not in ("parked",):
                    findings.append({"kind": "orphaned-branch", "repo": repo,
                                     "detail": f"{branch}: plan terminal ({matching.get('status')}) but branch not deleted/parked"})

# Duplicate full clones: same origin URL under different paths cannot share a git
# common dir, so plan coordination silently forks. One canonical checkout per
# repository (workspace policy); extra copies must be explicit git worktrees.
for url, paths in sorted(origin_urls.items()):
    primaries = sorted({str((anchor_root(root / p) or (root / p)).resolve()) for p in paths})
    if len(primaries) > 1:
        findings.append({"kind": "duplicate-clone", "repo": ", ".join(paths),
                         "detail": f"same origin {url} at {len(primaries)} checkouts ({'; '.join(primaries)}) — workspace policy allows one canonical checkout; make extras explicit worktrees"})

payload = {
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "workspace_root": str(root),
    "policy_source": policy_source,
    "repos_scanned": scanned,
    "active_plans": plans,
    "findings": findings,
}

if mode == "json":
    print(json.dumps(payload, ensure_ascii=False, indent=2))
elif mode == "snapshot":
    out = root / control_plane / "data" / "plan-fleet.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK snapshot written: {out} ({len(plans)} active plan(s), {len(findings)} finding(s))")
else:
    if not plans:
        print(f"No active plans across {len(scanned)} repo(s) with .engineer/ under {root}")
    else:
        cols = ("stream", "repo", "venture", "status", "branch", "claims", "age")
        rows = [(p["stream"], p["repo"], p["venture"], p["status"], p["branch"],
                 str(p["claims"]), f"{p['age_days']}d" + (" STALE" if p["stale"] else "")) for p in plans]
        widths = [max(len(c), *(len(r[i]) for r in rows)) for i, c in enumerate(cols)]
        fmt = "  ".join("{:<%d}" % w for w in widths)
        print(fmt.format(*cols))
        print(fmt.format(*("-" * w for w in widths)))
        for r, p in zip(rows, plans):
            print(fmt.format(*r) + f"  {p['title'][:60]}")
    if findings:
        print(f"\nFindings ({len(findings)}):")
        for f in findings:
            print(f"  [{f['kind']}] {f['repo']}: {f['detail']}")
PY
