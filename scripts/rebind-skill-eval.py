#!/usr/bin/env python3
"""Rebind the skill-eval sample hash chain to the current SKILL.md / runtime.

An Engineer version bump — or any edit to the runtime package (SKILL.md,
references, scripts, templates, …) — invalidates every skill-eval sample
binding at once:

  - the skill version               (skill_bundle.version / skill_binding.version / skill_version)
  - the SKILL.md content hash        (run.environment.skill_sha256)
  - the canonical bundle hash        (skill_bundle.sha256 / skill_binding.sha256 / grade.skill_sha256)
  - the eval-bank hash               (run.environment.bank_sha256)
  - the job -> capture -> grade/oracle file-content chain ({path, sha256} nodes)

Left unbound, the samples fail their own validators and engineer-health drops.
This retargets them all to the current tree, idempotently, then self-verifies
with the real grader.

Design: the "value" bindings are rebound by VALUE substitution keyed off the
current (old) values found in canonical reference fields — no field paths are
hardcoded except those references, so an added binding that reuses an old value
is caught automatically. The file-content chain is rebound generically: any
{path, sha256} object whose path resolves to a sample file gets sha256 =
sha256(that file), iterated to a fixpoint so job -> capture -> grade converges.

Usage:
  python3 scripts/rebind-skill-eval.py            # rebind in place, then verify
  python3 scripts/rebind-skill-eval.py --check     # report drift only; exit 1 if a rebind is needed
  python3 scripts/rebind-skill-eval.py --root DIR  # operate on an alternate tree (tests)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def fsha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def skillmd_version(root: Path) -> str:
    m = re.search(r'^\s*version:\s*"([^"]+)"', (root / "SKILL.md").read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit("rebind: SKILL.md metadata.version not found")
    return m.group(1)


def capture_module(root: Path):
    """The canonical runtime-package digest, computed by the very function the
    validators use, so the tool can never disagree with the checker."""
    spec = importlib.util.spec_from_file_location("_cse", root / "scripts" / "capture-skill-eval.py")
    if spec is None or spec.loader is None:
        sys.exit("rebind: cannot load scripts/capture-skill-eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bundle_sha256(root: Path) -> str:
    return capture_module(root).bundle_sha256(root)


def derived_capture(root: Path) -> dict:
    """Recompute only deterministic fields of the checked-in illustrative capture."""
    cap = load(root / "templates/agentic/skill-eval-capture.sample.json")
    job = load(root / "templates/agentic/skill-eval-job.sample.json")
    if cap.get("capture_kind") != "illustrative_fixture" or job.get("run_kind") != "illustrative_fixture":
        raise ValueError("refusing to rebind captured evidence")
    module = capture_module(root)
    cap["skill_binding"]["activation_probe_sha256"] = module.ACTIVATION_PROBE_SHA256
    job["scenario"]["activation_probe"]["response_sha256"] = module.ACTIVATION_PROBE_SHA256
    for artifact in cap["artifacts"]:
        path = module.safe_path(artifact["path"], root)
        if path is None or not path.is_file():
            raise ValueError("missing or unsafe illustrative artifact: " + artifact["path"])
        artifact["sha256"] = fsha(path)
        artifact["bytes"] = path.stat().st_size
    output = next(root / a["path"] for a in cap["artifacts"] if a["kind"] == "output")
    command = module.command_for(job, root, output)
    cap["execution"]["logical_command_sha256"] = module.logical_command_sha256(command, root)
    return cap


def derived_run(root: Path) -> dict:
    """Refresh artifact bindings, not behavioral claims, in the illustrative run."""
    run = load(root / "templates/agentic/skill-eval-run.sample.json")
    if run.get("run_kind") != "illustrative_fixture":
        raise ValueError("refusing to rebind captured run evidence")
    module = capture_module(root)
    for trial in run["trials"]:
        for artifact in trial["artifacts"]:
            path = module.safe_path(artifact["path"], root)
            if path is None or not path.is_file():
                raise ValueError("missing or unsafe illustrative run artifact")
            artifact["sha256"] = fsha(path)
            if "bytes" in artifact:
                artifact["bytes"] = path.stat().st_size
    return run


def canonical_values(root: Path) -> dict:
    run = load(root / "templates/agentic/skill-eval-run.sample.json")
    bank_path = run["environment"]["bank_path"]
    return {
        "VER": skillmd_version(root),
        "BUNDLE": bundle_sha256(root),
        "SKILLMD": fsha(root / "SKILL.md"),
        "BANK": fsha(root / bank_path),
        "PROBE": capture_module(root).ACTIVATION_PROBE_SHA256,
    }


def current_values(root: Path) -> dict:
    """The old values, read from canonical reference fields (self-configuring)."""
    job = load(root / "templates/agentic/skill-eval-job.sample.json")
    run = load(root / "templates/agentic/skill-eval-run.sample.json")
    return {
        "VER": job["skill_bundle"]["version"],
        "BUNDLE": job["skill_bundle"]["sha256"],
        "SKILLMD": run["environment"]["skill_sha256"],
        "BANK": run["environment"]["bank_sha256"],
        "PROBE": job["scenario"]["activation_probe"]["response_sha256"],
    }


def sample_paths(root: Path) -> list[Path]:
    paths = sorted(Path(p) for p in glob.glob(str(root / "templates/agentic/skill-eval-*.sample.json")))
    for path in paths:
        if path.is_symlink():
            raise ValueError("refusing symlinked fixture: " + path.name)
        data = load(path)
        for key in ("run_kind", "capture_kind", "grade_kind", "receipt_kind"):
            if key in data and data[key] != "illustrative_fixture":
                raise ValueError("refusing non-illustrative fixture: " + path.name)
    return paths


def chain_nodes(obj, names: set[str], out: list):
    """Collect (current_sha256, target_name) for every {path, sha256} object
    whose path points at a sample file."""
    if isinstance(obj, dict):
        p, s = obj.get("path"), obj.get("sha256")
        if isinstance(p, str) and isinstance(s, str) and Path(p).name in names:
            out.append((s, Path(p).name))
        for v in obj.values():
            chain_nodes(v, names, out)
    elif isinstance(obj, list):
        for v in obj:
            chain_nodes(v, names, out)


def canonical_grade(root: Path) -> dict:
    """Use the production deterministic grader; never manufacture captured evidence."""
    spec = importlib.util.spec_from_file_location("_fixture_grader", root / "scripts/grade-skill-eval-capture.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load deterministic grader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grade(root / "templates/agentic/skill-eval-capture.sample.json",
                        root / "templates/agentic/skill-eval-oracle.sample.json", root)


def detect_drift(root: Path) -> list[str]:
    """Return human-readable drift reasons; empty means already bound."""
    reasons = []
    cur, new = current_values(root), canonical_values(root)
    for k in ("VER", "BUNDLE", "SKILLMD", "BANK", "PROBE"):
        if cur[k] != new[k]:
            reasons.append(f"{k.lower()} {cur[k][:12]} -> {new[k][:12]}")
    names = {p.name for p in sample_paths(root)}
    for sp in sample_paths(root):
        nodes: list = []
        chain_nodes(load(sp), names, nodes)
        for have, target in nodes:
            want = fsha(root / "templates/agentic" / target)
            if have != want:
                reasons.append(f"{sp.name}: {target} digest {have[:12]} -> {want[:12]}")
    if derived_capture(root) != load(root / "templates/agentic/skill-eval-capture.sample.json"):
        reasons.append("derived capture probe, artifact, or command binding differs")
    if derived_run(root) != load(root / "templates/agentic/skill-eval-run.sample.json"):
        reasons.append("illustrative run artifact binding differs")
    # Replay only once prerequisite bindings are valid. A stale artifact hash in
    # the grade is not necessarily represented by a {path, sha256} chain node.
    if not reasons and canonical_grade(root) != load(root / "templates/agentic/skill-eval-grade.sample.json"):
        reasons.append("stored grade differs from deterministic replay")
    return reasons


def replace_in_samples(root: Path, old: str, new: str) -> int:
    if old == new:
        return 0
    n = 0
    for sp in sample_paths(root):
        t = sp.read_text(encoding="utf-8")
        if old in t:
            sp.write_text(t.replace(old, new), encoding="utf-8")
            n += 1
    return n


def rebind(root: Path) -> None:
    derived_capture(root)  # Refuse captured evidence before any mutation.
    derived_run(root)
    cur, new = current_values(root), canonical_values(root)
    # 1. Value bindings (versions are quoted so only skill-version fields match;
    #    hashes are full 64-char digests, unique by construction).
    replace_in_samples(root, f'"{cur["VER"]}"', f'"{new["VER"]}"')
    for k in ("BUNDLE", "SKILLMD", "BANK", "PROBE"):
        replace_in_samples(root, cur[k], new[k])
    cap_path = root / "templates/agentic/skill-eval-capture.sample.json"
    cap = derived_capture(root)
    if cap != load(cap_path):
        cap_path.write_text(json.dumps(cap, indent=2) + "\n", encoding="utf-8")
    run_path = root / "templates/agentic/skill-eval-run.sample.json"
    run = derived_run(root)
    if run != load(run_path):
        run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    # 2. File-content chain to a fixpoint (job -> capture -> grade/oracle).
    names = {p.name for p in sample_paths(root)}
    for _ in range(len(names) + 2):
        changed = False
        for sp in sample_paths(root):
            nodes: list = []
            chain_nodes(load(sp), names, nodes)
            for have, target in nodes:
                want = fsha(root / "templates/agentic" / target)
                if have != want:
                    sp.write_text(sp.read_text(encoding="utf-8").replace(have, want), encoding="utf-8")
                    changed = True
        if not changed:
            grade_path = root / "templates/agentic/skill-eval-grade.sample.json"
            grade = canonical_grade(root)
            if grade == load(grade_path):
                break
            grade_path.write_text(json.dumps(grade, indent=2) + "\n", encoding="utf-8")
            # Continue to update any receipt bound to the regenerated grade.
    else:
        sys.exit("rebind: file-content chain did not converge (cyclic {path,sha256}?)")


def verify(root: Path) -> bool:
    """Self-check: the real grader must accept the rebound capture sample."""
    cap = root / "templates/agentic/skill-eval-capture.sample.json"
    oracle = root / "templates/agentic/skill-eval-oracle.sample.json"
    with tempfile.TemporaryDirectory(prefix="engineer-rebind-") as tmp:
        output = Path(tmp) / "grade.json"
        r = subprocess.run(
            [sys.executable, str(root / "scripts/grade-skill-eval-capture.py"), str(cap),
             "--oracle", str(oracle), "--root", str(root), "--output", str(output)],
            capture_output=True, text=True,
        )
    if r.returncode != 0:
        sys.stderr.write("rebind: grader rejected the rebound sample:\n" + (r.stdout or r.stderr)[:400] + "\n")
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebind the skill-eval sample hash chain.")
    ap.add_argument("--check", action="store_true", help="report drift only; exit 1 if rebind needed")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="repo root")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    try:
        reasons = detect_drift(root)
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print(f"rebind: {exc}", file=sys.stderr)
        return 2
    if args.check:
        if reasons:
            print("skill-eval chain drift — rebind needed:")
            for r in reasons:
                print(f"  - {r}")
            return 1
        print("skill-eval chain: bound (no drift)")
        return 0

    if not reasons:
        print("skill-eval chain already bound; nothing to do")
        return 0 if verify(root) else 3
    print("rebinding skill-eval chain:")
    for r in reasons:
        print(f"  - {r}")
    rebind(root)
    remaining = detect_drift(root)
    if remaining:
        sys.stderr.write("rebind: drift remains after rebind:\n  " + "\n  ".join(remaining) + "\n")
        return 3
    if not verify(root):
        return 3
    print("rebind complete and grader-verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
