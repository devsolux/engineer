#!/usr/bin/env python3
"""Live model-in-the-loop eval runner for engineer routing (Claude Code headless).

What this proves
    The static harness (scripts/run-evals.sh) validates eval-bank structure only.
    This runner drives `claude -p` (Claude Code headless print mode) — NOT the raw
    API — because the test target is "does engineer routing actually fire in a real
    host session". Each scenario prompt gets the sealed routing probe token
    appended; per the SKILL.md contract, an activated engineer emits a final
    standalone line with the activation marker. Marker presence == activation.

Baseline mechanism (verified on claude 2.1.211, 2026-07-16)
    `--disable-slash-commands` ("Disable all skills" per `claude --help`) is the
    cleanest engineer-off switch for -p mode: the same prompt that activates engineer
    with skills enabled (marker emitted, multi-turn skill load) answers directly
    with no skill load and no marker when the flag is passed. Rejected
    alternatives: `--safe-mode` also disables CLAUDE.md/hooks/MCP (changes more
    than skill availability); `--settings` has no documented per-skill override;
    uninstalling the symlink mutates shared user state.

Cost & safety
    - Default model is haiku; the host default (unpinned) is far more expensive,
      so --model is always passed explicitly.
    - Turns capped via --max-turns (accepted by claude -p even though absent from
      --help), per-scenario wall-clock timeout, and a hard cap of 12 scenarios
      per run.
    - Runs execute from a throwaway temp cwd so project CLAUDE.md context cannot
      leak in (user-level ~/.claude context still applies, as in any real
      session).
    - Run from a real terminal. Inside a Claude Code session (CLAUDECODE /
      CLAUDE_CODE_CHILD_SESSION exported) the child `claude -p` answers without
      loading skills, so every with-skill scenario reports a false activation
      miss; scrub those env vars if nesting is unavoidable (measured 2026-07-16,
      claude 2.1.209/2.1.211, haiku: same prompt Y/Y clean vs Y/N nested).
    - Never passes --dangerously-skip-permissions or any permission bypass; in -p
      mode mutating tool calls are denied by default, and scenarios are
      advisory-only ("text only; do not edit files").

Usage
    python3 scripts/run-live-evals.py                      # with-skill arm, all scenarios
    python3 scripts/run-live-evals.py --baseline           # baseline arm only (skills disabled)
    python3 scripts/run-live-evals.py --compare            # both arms + lift summary
    python3 scripts/run-live-evals.py --scenarios root-cause-retry,core-signup-auth --model haiku
    python3 scripts/run-live-evals.py --list               # print scenarios, no model call

Grading
    pass = activation-match AND (assert_any empty or >=1 substring hit)
           AND (no forbid_any substring hit), case-insensitive.
    Baseline arm is graded two ways: strict (same criteria — positive scenarios
    fail by construction since the skill cannot load) and content-only
    (assert/forbid only), so the lift summary cannot overstate.
    Scenarios flagged "known_gap": true are xfail — fully run and reported, but
    a miss does not gate the exit code, and a pass prints a notice to remove the
    flag. Measured 2026-07-16 (claude 2.1.211, haiku and sonnet): advisory-form
    fix prompts get correct root-cause behavior from L1 metadata + host rules
    without a Skill-tool body load, so the activation marker never appears.
    Implicit routing is also nondeterministic run-to-run (the same build-shaped
    prompt loaded the skill body on one run and not the next), so the runner
    defaults to pass@2 (--attempts); use --attempts 1 for strict single-shot.

Output
    Per-scenario PASS/FAIL table on stdout; JSON report written to
    .engineer/live-eval-runs/<timestamp>.json (gitignored). Exit 0 only when every
    graded row in the requested arm(s) passes (baseline strict misses on
    expect_activation=true scenarios are expected and do not fail the run).

Test seam
    --claude-bin lets the offline fixture (scripts/test-live-evals.sh) substitute
    a shim binary; --report-dir redirects report output. Neither changes grading.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import NoReturn
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BANK = ROOT / "evals" / "live-smoke.json"
DEFAULT_REPORT_DIR = ROOT / ".engineer" / "live-eval-runs"
HARD_SCENARIO_CAP = 12
FORBIDDEN_FLAGS = ("--dangerously-skip-permissions", "--allow-dangerously-skip-permissions")


def fail(msg: str, code: int = 2) -> NoReturn:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_bank(path: Path) -> dict:
    try:
        bank = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read live-smoke bank {path}: {exc}")
    errors = []
    if bank.get("skill_name") != "engineer":
        errors.append("skill_name must equal engineer")
    for key in ("probe_token", "activation_marker"):
        if not isinstance(bank.get(key), str) or not bank[key].strip():
            errors.append(f"{key} missing or empty")
    scenarios = bank.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("scenarios must be a non-empty array")
        scenarios = []
    allowed = {"id", "source_eval", "prompt", "expect_activation", "assert_any", "forbid_any", "known_gap"}
    seen_ids: set[str] = set()
    for i, s in enumerate(scenarios):
        if not isinstance(s, dict):
            errors.append(f"scenarios[{i}] not an object")
            continue
        unknown = set(s) - allowed
        if unknown:
            errors.append(f"scenarios[{i}] unknown keys: {sorted(unknown)}")
        sid = s.get("id")
        if not isinstance(sid, str) or not sid.strip():
            errors.append(f"scenarios[{i}] id must be a non-empty string")
        elif sid in seen_ids:
            errors.append(f"duplicate scenario id: {sid}")
        else:
            seen_ids.add(sid)
        if not isinstance(s.get("prompt"), str) or not s["prompt"].strip():
            errors.append(f"scenarios[{i}] prompt empty")
        if not isinstance(s.get("expect_activation"), bool):
            errors.append(f"scenarios[{i}] expect_activation must be boolean")
        if not isinstance(s.get("known_gap", False), bool):
            errors.append(f"scenarios[{i}] known_gap must be boolean when present")
        for key in ("assert_any", "forbid_any"):
            val = s.get(key, [])
            if not isinstance(val, list) or any(not isinstance(x, str) or not x.strip() for x in val):
                errors.append(f"scenarios[{i}] {key} must be an array of non-empty strings")
        src = s.get("source_eval")
        if src is not None and (not isinstance(src, int) or isinstance(src, bool) or src < 1):
            errors.append(f"scenarios[{i}] source_eval must be null or a positive integer")
    # Curated subset must trace back to the real eval bank.
    evals_path = ROOT / "evals" / "evals.json"
    if evals_path.is_file():
        known = {e.get("id") for e in json.loads(evals_path.read_text(encoding="utf-8")).get("evals", [])}
        for s in scenarios:
            src = s.get("source_eval") if isinstance(s, dict) else None
            if isinstance(src, int) and src not in known:
                errors.append(f"scenario {s.get('id')} source_eval {src} not in evals/evals.json")
    if errors:
        print("FAIL live-smoke bank:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    return bank


def run_scenario(scenario: dict, bank: dict, arm: str, args: argparse.Namespace, workdir: Path) -> dict:
    prompt = f"{scenario['prompt']} {bank['probe_token']}"
    cmd = [
        args.claude_bin, "-p", prompt,
        "--output-format", "json",
        "--model", args.model,
        "--max-turns", str(args.max_turns),
        "--no-session-persistence",
    ]
    if arm == "baseline":
        cmd.append("--disable-slash-commands")
    for flag in FORBIDDEN_FLAGS:
        if flag in cmd:
            fail(f"refusing to run with {flag}")
    started = datetime.now(timezone.utc)
    row: dict = {
        "id": scenario["id"],
        "arm": arm,
        "expect_activation": scenario["expect_activation"],
        "known_gap": bool(scenario.get("known_gap", False)),
        "started_at": started.isoformat(),
    }
    try:
        proc = subprocess.run(
            cmd, cwd=workdir, capture_output=True, text=True, timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        row.update({"error": f"timeout after {args.timeout}s", "passed": False, "graded": False})
        return row
    except OSError as exc:
        fail(f"cannot execute {args.claude_bin}: {exc}")
    row["duration_s"] = round((datetime.now(timezone.utc) - started).total_seconds(), 1)
    if proc.returncode != 0:
        row.update({
            "error": f"claude exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:300]}",
            "passed": False,
            "graded": False,
        })
        return row
    text = proc.stdout
    try:
        payload = json.loads(proc.stdout)
        text = str(payload.get("result", ""))
        row["cost_usd"] = payload.get("total_cost_usd")
        row["num_turns"] = payload.get("num_turns")
        if payload.get("is_error"):
            row["error"] = "host reported is_error"
    except json.JSONDecodeError:
        row["error"] = "non-JSON host output; graded on raw stdout"

    marker = bank["activation_marker"]
    lowered = text.lower()
    activation_observed = any(line.strip() == marker for line in text.splitlines()) or marker in text
    asserts = scenario.get("assert_any") or []
    forbids = scenario.get("forbid_any") or []
    assert_hits = [s for s in asserts if s.lower() in lowered]
    forbid_hits = [s for s in forbids if s.lower() in lowered]
    activation_ok = activation_observed == scenario["expect_activation"]
    content_ok = (not asserts or bool(assert_hits)) and not forbid_hits
    row.update({
        "activation_observed": activation_observed,
        "activation_ok": activation_ok,
        "assert_hits": assert_hits,
        "forbid_hits": forbid_hits,
        "content_ok": content_ok,
        "passed": activation_ok and content_ok and "error" not in row,
        "graded": True,
        "output_tail": text[-400:],
    })
    return row


def print_table(rows: list[dict]) -> None:
    header = f"{'scenario':<24} {'arm':<10} {'act exp/got':<12} {'asserts':<8} {'forbids':<8} {'verdict':<7} {'cost':<8} {'secs':<6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        act = f"{'Y' if r['expect_activation'] else 'N'}/{'Y' if r.get('activation_observed') else 'N' if r.get('graded') else '?'}"
        asserts = f"{len(r.get('assert_hits', []))} hit" if r.get("graded") else "-"
        forbids = f"{len(r.get('forbid_hits', []))} hit" if r.get("graded") else "-"
        verdict = "PASS" if r["passed"] else ("XFAIL" if r.get("known_gap") else "FAIL")
        cost = f"${r['cost_usd']:.3f}" if isinstance(r.get("cost_usd"), (int, float)) else "-"
        secs = f"{r['duration_s']:.0f}" if isinstance(r.get("duration_s"), (int, float)) else "-"
        print(f"{r['id']:<24} {r['arm']:<10} {act:<12} {asserts:<8} {forbids:<8} {verdict:<7} {cost:<8} {secs:<6}")
        if r.get("error"):
            print(f"  ! {r['error']}")


def summarize(rows: list[dict]) -> dict:
    with_skill = [r for r in rows if r["arm"] == "with-skill"]
    baseline = [r for r in rows if r["arm"] == "baseline"]
    summary: dict = {}
    if with_skill:
        summary["with_skill_pass_rate"] = round(
            sum(r["passed"] for r in with_skill) / len(with_skill), 3)
    if baseline:
        summary["baseline_strict_pass_rate"] = round(
            sum(r["passed"] for r in baseline) / len(baseline), 3)
        graded = [r for r in baseline if r.get("graded")]
        if graded:
            summary["baseline_content_pass_rate"] = round(
                sum(r["content_ok"] for r in graded) / len(graded), 3)
    if with_skill and baseline:
        summary["lift_strict"] = round(
            summary["with_skill_pass_rate"] - summary["baseline_strict_pass_rate"], 3)
        if "baseline_content_pass_rate" in summary:
            summary["lift_content"] = round(
                summary["with_skill_pass_rate"] - summary["baseline_content_pass_rate"], 3)
    total_cost = sum(r.get("cost_usd") or 0 for r in rows)
    summary["total_cost_usd"] = round(total_cost, 4)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Live engineer routing evals via claude -p")
    parser.add_argument("--file", type=Path, default=DEFAULT_BANK, help="live-smoke bank path")
    parser.add_argument("--scenarios", default="", help="comma-separated scenario ids")
    parser.add_argument("--model", default="haiku", help="model alias (default: haiku)")
    parser.add_argument("--max-turns", type=int, default=6,
                        help="turn cap per scenario (default 6: skill load + answer plus "
                             "slack for user-level hooks that consume turns)")
    parser.add_argument("--timeout", type=int, default=180, help="per-scenario seconds")
    parser.add_argument("--attempts", type=int, default=2, choices=(1, 2, 3),
                        help="pass@N: retry a scenario-arm only when it fails (default 2; "
                             "implicit routing is nondeterministic run-to-run — use 1 for "
                             "strict single-shot measurement)")
    parser.add_argument("--baseline", action="store_true", help="baseline arm only (skills disabled)")
    parser.add_argument("--compare", action="store_true", help="run both arms and report lift")
    parser.add_argument("--list", action="store_true", help="validate + list scenarios, no model call")
    parser.add_argument("--claude-bin", default="claude", help="host binary (test seam)")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    if args.baseline and args.compare:
        fail("--baseline and --compare are mutually exclusive")

    bank = load_bank(args.file)
    scenarios = bank["scenarios"]
    if args.scenarios:
        wanted = [s.strip() for s in args.scenarios.split(",") if s.strip()]
        by_id = {s["id"]: s for s in scenarios}
        missing = [w for w in wanted if w not in by_id]
        if missing:
            fail(f"unknown scenario id(s): {', '.join(missing)}")
        scenarios = [by_id[w] for w in wanted]

    if args.list:
        for s in scenarios:
            print(f"{s['id']:<24} expect_activation={s['expect_activation']} source_eval={s.get('source_eval')}")
        print(f"OK — {len(scenarios)} scenario(s) valid")
        return 0

    if len(scenarios) > HARD_SCENARIO_CAP:
        fail(f"{len(scenarios)} scenarios exceed the hard cap of {HARD_SCENARIO_CAP} per live run; use --scenarios")

    arms = ["with-skill", "baseline"] if args.compare else (["baseline"] if args.baseline else ["with-skill"])
    workdir = Path(tempfile.mkdtemp(prefix="engineer-live-eval-"))
    rows: list[dict] = []
    try:
        for arm in arms:
            for scenario in scenarios:
                attempts = []
                for attempt in range(1, args.attempts + 1):
                    print(f"running {scenario['id']} [{arm}] attempt {attempt} …", flush=True)
                    row = run_scenario(scenario, bank, arm, args, workdir)
                    attempts.append(row)
                    if row["passed"]:
                        break
                best = attempts[-1]
                best["attempts"] = len(attempts)
                if len(attempts) > 1:
                    best["attempt_verdicts"] = ["PASS" if a["passed"] else "FAIL" for a in attempts]
                    best["cost_usd"] = round(sum(a.get("cost_usd") or 0 for a in attempts), 4)
                    best["duration_s"] = round(sum(a.get("duration_s") or 0 for a in attempts), 1)
                rows.append(best)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    print_table(rows)
    summary = summarize(rows)
    print("---")
    for key, val in summary.items():
        print(f"{key}: {val}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bank": str(args.file),
        "model": args.model,
        # The CLI resolves aliases such as "haiku" at run time and does not echo the dated model id
        # back to this runner, so a capture records the alias only; pass a dated id to pin a run.
        "model_resolution": "alias_only" if "-20" not in args.model else "pinned_id",
        "max_turns": args.max_turns,
        "attempts": args.attempts,
        "arms": arms,
        "scenarios": rows,
        "summary": summary,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.report_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%SZ')}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"report: {report_path}")

    # Baseline strict misses on positive scenarios are the expected control result.
    gating = [r for r in rows if not (r["arm"] == "baseline" and r["expect_activation"])]
    baseline_control = [r for r in rows if r["arm"] == "baseline" and r["expect_activation"]]
    control_leak = [r for r in baseline_control if r.get("activation_observed")]
    if control_leak:
        print(f"FAIL — activation marker leaked into baseline arm: {[r['id'] for r in control_leak]}")
        return 1
    # known_gap == expected-fail (xfail): tracked routing gaps report but do not gate.
    healed = [r for r in gating if r.get("known_gap") and r["passed"] and r["arm"] == "with-skill"]
    for r in healed:
        print(f"NOTE — known_gap scenario now passes: {r['id']} (remove its known_gap flag)")
    xfailed = [r for r in gating if r.get("known_gap") and not r["passed"]]
    for r in xfailed:
        print(f"XFAIL — tracked routing gap (not gating): {r['id']}")
    failed = [r for r in gating if not r["passed"] and not r.get("known_gap")]
    if failed:
        print(f"FAIL — {len(failed)} scenario run(s) failed: {[r['id'] for r in failed]}")
        return 1
    print("OK — live eval run passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
