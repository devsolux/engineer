#!/usr/bin/env python3
"""Validate a job-bound cross-host skill-eval capture manifest and its artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

HEX = re.compile(r"^[0-9a-f]{64}$")
SECRET = re.compile(
    rb"(?i)(?:sk-ant-[a-z0-9_-]{20,}|sk-[a-z0-9_-]{24,}|gh[pousr]_[a-z0-9]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:authorization|api[_-]?key|access[_-]?token|password)\s*[:=]\s*(?:bearer\s+)?[a-z0-9_./+\-=]{20,})"
)
LIMITATIONS = {
    "Capture success is not behavioral success or promotion evidence.",
    "Local hashes do not prove runner, sandbox, network, credential, or provider honesty.",
    "Artifacts require independent outcome and trajectory grading after secret review.",
}

# Dynamic compiler loading is validation-only; never leave machine-specific bytecode in the skill tree.
sys.dont_write_bytecode = True


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_capture_module() -> Any:
    path = Path(__file__).with_name("capture-skill-eval.py")
    spec = importlib.util.spec_from_file_location("engineer_capture_skill_eval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load capture compiler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(data: Any, root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    gates: list[str] = []
    keys = {"schema_version", "capture_kind", "run_id", "job", "host", "model", "scenario_id", "host_binding", "skill_binding", "execution", "artifacts", "assessment", "limitations"}
    if not isinstance(data, dict):
        return ["root must be an object"], []
    if set(data) != keys or data.get("schema_version") != 5 or data.get("capture_kind") not in {"illustrative_fixture", "captured_run"}:
        errors.append("capture root, schema, or kind invalid")
    if not isinstance(data.get("run_id"), str) or not data.get("run_id") or data.get("host") not in {"codex", "claude"} or not isinstance(data.get("model"), str) or not data.get("model") or not isinstance(data.get("scenario_id"), int) or isinstance(data.get("scenario_id"), bool) or data.get("scenario_id", 0) < 1:
        errors.append("capture identity invalid")

    job_ref = data.get("job", {})
    if not isinstance(job_ref, dict) or set(job_ref) != {"path", "sha256"}:
        errors.append("job reference invalid")
        job = {}
    else:
        job_path = safe_path(job_ref.get("path"), root)
        if job_path is None or not job_path.is_file() or not HEX.fullmatch(str(job_ref.get("sha256", ""))) or digest(job_path) != job_ref.get("sha256"):
            errors.append("job path or digest invalid")
            job = {}
        else:
            try:
                job = json.loads(job_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                errors.append("bound job unreadable")
                job = {}
    if job:
        compiler = Path(__file__).with_name("capture-skill-eval.py")
        compiled = __import__("subprocess").run(
            [sys.executable, str(compiler), str(job_path), "--print-command"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if compiled.returncode != 0:
            gates.append("bound job fails canonical capture-job validation")
    if job:
        if data.get("run_id") != job.get("run_id") or data.get("host") != job.get("host") or data.get("model") != job.get("model") or data.get("scenario_id") != job.get("scenario", {}).get("id"):
            gates.append("capture identity differs from bound job")
        if data.get("capture_kind") == "captured_run" and job.get("run_kind") != "captured_run":
            gates.append("captured manifest requires a captured-run job")

    binding = data.get("host_binding", {})
    binding_keys = {"inventory_sha256", "executable_sha256", "version_output_sha256", "help_output_sha256", "required_capabilities", "live_reverified", "reason"}
    if not isinstance(binding, dict) or set(binding) != binding_keys or any(not HEX.fullmatch(str(binding.get(key, ""))) for key in ("inventory_sha256", "executable_sha256", "version_output_sha256", "help_output_sha256")) or not isinstance(binding.get("required_capabilities"), list) or binding.get("required_capabilities") != sorted(set(binding.get("required_capabilities", []))) or binding.get("live_reverified") is not True or not isinstance(binding.get("reason"), str) or not binding.get("reason"):
        errors.append("host binding invalid")
    elif job:
        expected = job.get("host_inventory", {})
        for target, source in (("inventory_sha256", "sha256"), ("executable_sha256", "executable_sha256"), ("version_output_sha256", "version_output_sha256"), ("help_output_sha256", "help_output_sha256"), ("required_capabilities", "required_capabilities")):
            if binding.get(target) != expected.get(source):
                gates.append(f"host binding {target} differs from job")

    skill_binding = data.get("skill_binding", {})
    skill_keys = {"sha256", "version", "expectations_excluded", "runtime_supplied", "activation_mode", "invocation", "activation_probe_sha256", "activation_confirmed", "mechanism", "unresolved_marker_absent"}
    if not isinstance(skill_binding, dict) or set(skill_binding) != skill_keys or not HEX.fullmatch(str(skill_binding.get("sha256", ""))) or not isinstance(skill_binding.get("version"), str) or not skill_binding.get("version") or skill_binding.get("expectations_excluded") is not True or skill_binding.get("runtime_supplied") is not True or skill_binding.get("activation_mode") not in {"explicit", "implicit"} or not HEX.fullmatch(str(skill_binding.get("activation_probe_sha256", ""))) or skill_binding.get("activation_confirmed") is not True or skill_binding.get("unresolved_marker_absent") is not True:
        errors.append("skill binding invalid")
    elif job:
        expected_skill = job.get("skill_bundle", {})
        if skill_binding.get("sha256") != expected_skill.get("sha256") or skill_binding.get("version") != expected_skill.get("version"):
            gates.append("skill binding differs from bound package")
        expected_mechanism = "codex_home_skill" if job.get("host") == "codex" else "claude_plugin"
        scenario = job.get("scenario", {})
        if skill_binding.get("activation_mode") != scenario.get("activation_mode") or skill_binding.get("invocation") != scenario.get("invocation") or skill_binding.get("activation_probe_sha256") != scenario.get("activation_probe", {}).get("response_sha256") or skill_binding.get("mechanism") != expected_mechanism:
            gates.append("skill activation mechanism or invocation differs from bound job")

    execution = data.get("execution", {})
    execution_keys = {"exit_code", "timed_out", "duration_ms", "logical_command_sha256", "executed_argv_sha256"}
    if not isinstance(execution, dict) or set(execution) != execution_keys or not isinstance(execution.get("exit_code"), int) or isinstance(execution.get("exit_code"), bool) or type(execution.get("timed_out")) is not bool or not isinstance(execution.get("duration_ms"), int) or isinstance(execution.get("duration_ms"), bool) or execution.get("duration_ms", -1) < 0 or any(not HEX.fullmatch(str(execution.get(key, ""))) for key in ("logical_command_sha256", "executed_argv_sha256")):
        errors.append("execution evidence invalid")
        execution = {}

    artifacts = data.get("artifacts")
    seen_kinds: set[str] = set()
    seen_paths: set[Path] = set()
    if not isinstance(artifacts, list) or len(artifacts) != 3:
        errors.append("exactly three artifacts required")
        artifacts = []
    output_path: Path | None = None
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {"kind", "path", "sha256", "bytes"} or artifact.get("kind") not in {"output", "trace", "log"} or artifact.get("kind") in seen_kinds:
            errors.append("artifact identity invalid")
            continue
        seen_kinds.add(artifact["kind"])
        path = safe_path(artifact.get("path"), root)
        if path is None or not path.is_file() or path in seen_paths or not HEX.fullmatch(str(artifact.get("sha256", ""))):
            errors.append(f"artifact {artifact['kind']} path or digest shape invalid")
            continue
        seen_paths.add(path)
        if artifact["kind"] == "output":
            output_path = path
        body = path.read_bytes()
        if digest(path) != artifact.get("sha256") or len(body) != artifact.get("bytes"):
            gates.append(f"artifact {artifact['kind']} bytes or digest mismatch")
        if len(body) > 10_000_000:
            gates.append(f"artifact {artifact['kind']} exceeds 10 MB review bound")
        if SECRET.search(body):
            gates.append(f"artifact {artifact['kind']} contains a high-confidence secret pattern")
    if seen_kinds != {"output", "trace", "log"}:
        errors.append("output, trace, and log artifacts are all required")
    if job and output_path is not None and execution:
        try:
            module = load_capture_module()
            logical = module.command_for(job, root, output_path)
            expected_command_hash = module.logical_command_sha256(logical, root)
        except Exception as exc:  # validator must fail closed on compiler drift
            errors.append(f"logical command reconstruction failed: {exc}")
        else:
            if execution.get("logical_command_sha256") != expected_command_hash:
                gates.append("logical command digest differs from canonical job compilation")
        try:
            probe_confirmed = module.activation_probe_confirmed(output_path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            errors.append(f"activation probe reconstruction failed: {exc}")
        else:
            if not probe_confirmed or skill_binding.get("activation_confirmed") is not True:
                gates.append("sealed activation probe response was not observed exactly once")

    assessment = data.get("assessment", {})
    if not isinstance(assessment, dict) or set(assessment) != {"capture_succeeded", "behavioral_pass", "grading_required"} or type(assessment.get("capture_succeeded")) is not bool or assessment.get("behavioral_pass") is not None or assessment.get("grading_required") is not True:
        errors.append("assessment must separate capture from ungraded behavior")
    elif execution and assessment.get("capture_succeeded") != (execution.get("exit_code") == 0 and execution.get("timed_out") is False and skill_binding.get("unresolved_marker_absent") is True and skill_binding.get("activation_confirmed") is True):
        gates.append("capture_succeeded is not derived from execution evidence")
    if set(data.get("limitations", [])) != LIMITATIONS or len(data.get("limitations", [])) != 3:
        gates.append("mandatory capture limitations missing or altered")
    return errors, gates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        manifest = regular_input_file(args.manifest)
        if manifest is None: raise ValueError("manifest must be a regular file, not a symlink")
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors, gates = [str(exc)], []
    else:
        errors, gates = validate(data, Path(args.root).resolve())
    if args.json:
        print(json.dumps({"ok": not errors and not gates, "errors": errors, "gates": gates}, indent=2))
    else:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        for message in gates:
            print(f"GATE: {message}", file=sys.stderr)
        if not errors and not gates:
            print("skill eval capture manifest valid")
    return 0 if not errors and not gates else 1


if __name__ == "__main__":
    raise SystemExit(main())
