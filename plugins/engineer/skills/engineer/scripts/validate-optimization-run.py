#!/usr/bin/env python3
"""Validate and score a comparative engineer prompt or agent-loop optimization run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

SUITES = ("capability", "regression", "holdout", "adversarial")
LAYERS = {"prompt", "context", "tool", "loop", "model", "grader", "environment"}
HEX = set("0123456789abcdef")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REF = re.compile(r"^refs/(heads|tags)/[A-Za-z0-9][A-Za-z0-9._/-]*$")
PREDICATE = "https://slsa.dev/provenance/v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def is_revision(value: Any) -> bool:
    return isinstance(value, str) and len(value) in {40, 64} and set(value) <= HEX


def is_ref(value: Any) -> bool:
    return isinstance(value, str) and REF.fullmatch(value) is not None and ".." not in value and "//" not in value and not value.endswith(("/", "."))


def pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def diff_pointers(baseline: Any, candidate: Any, path: str = "") -> set[str]:
    if type(baseline) is not type(candidate):
        return {path or "/"}
    if isinstance(baseline, dict):
        changed: set[str] = set()
        for key in set(baseline) | set(candidate):
            child = f"{path}/{pointer_token(str(key))}"
            if key not in baseline or key not in candidate:
                changed.add(child)
            else:
                changed |= diff_pointers(baseline[key], candidate[key], child)
        return changed
    if isinstance(baseline, list):
        changed = set()
        for index in range(max(len(baseline), len(candidate))):
            child = f"{path}/{index}"
            if index >= len(baseline) or index >= len(candidate):
                changed.add(child)
            else:
                changed |= diff_pointers(baseline[index], candidate[index], child)
        return changed
    return set() if baseline == candidate else {path or "/"}


def verify_attestation(artifact: Path, receipt: dict[str, Any], policy: dict[str, Any], root: Path) -> tuple[bool, str]:
    gh = shutil.which("gh")
    if gh is None:
        return False, "gh is unavailable for cryptographic attestation verification"
    bundle = safe_path(receipt.get("bundle_path"), root)
    trusted_root = safe_path(receipt.get("trusted_root_path"), root)
    if bundle is None or trusted_root is None:
        return False, "attestation paths are unsafe"
    command = [
        gh, "attestation", "verify", str(artifact), "--repo", policy["repository"],
        "--bundle", str(bundle), "--custom-trusted-root", str(trusted_root),
        "--signer-workflow", policy["signer_workflow"], "--signer-digest", policy["signer_digest"],
        "--source-digest", receipt["source_digest"], "--source-ref", receipt["source_ref"],
        "--predicate-type", policy["predicate_type"], "--cert-oidc-issuer", policy["oidc_issuer"],
        "--deny-self-hosted-runners", "--format", "json",
    ]
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"attestation verifier failed: {exc}"
    if run.returncode != 0:
        return False, f"attestation verifier rejected evidence: {run.stderr.strip() or 'no diagnostic'}"
    try:
        output = json.loads(run.stdout)
    except json.JSONDecodeError:
        return False, "attestation verifier did not return JSON"
    expected = sha256(artifact)
    if not isinstance(output, list) or not output:
        return False, "attestation verifier returned no verified statements"
    for item in output:
        statement = item.get("verificationResult", {}).get("statement", {}) if isinstance(item, dict) else {}
        subjects = statement.get("subject", []) if isinstance(statement, dict) else []
        if statement.get("predicateType") == PREDICATE and any(
            isinstance(subject, dict) and subject.get("digest", {}).get("sha256") == expected
            for subject in subjects
        ):
            return True, ""
    return False, "verified statements do not bind the evidence artifact and predicate"


def is_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def increase_percent(candidate: float, baseline: float) -> float:
    if baseline == 0:
        return 0.0 if candidate == 0 else math.inf
    return 100 * (candidate - baseline) / baseline


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def validate(data: Any, root: Path, verify_crypto: bool = False, trust_policy: Any = None) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    summary: dict[str, Any] = {}

    def err(path: str, message: str) -> None:
        errors.append(f"{path}: {message}")

    if not isinstance(data, dict):
        return ["$: must be an object"], summary
    root_keys = {"schema_version", "experiment_id", "change", "claim", "environment", "datasets", "gates", "evidence", "results", "trace_review", "decision"}
    if set(data) != root_keys:
        err("$", f"keys must be exactly {sorted(root_keys)}")
    if data.get("schema_version") != 2:
        err("$.schema_version", "must equal 2")
    if not isinstance(data.get("experiment_id"), str) or not data["experiment_id"].strip():
        err("$.experiment_id", "must be a non-empty string")

    variants: Any = None
    expected_variant_bindings: dict[str, dict[str, str]] | None = None
    change = data.get("change")
    if not isinstance(change, dict):
        err("$.change", "must be an object")
    else:
        change_keys = {"layer", "hypothesis", "baseline_version", "candidate_version", "changed_variables", "allowed_json_pointers", "variant_bundle_path", "variant_bundle_sha256"}
        if set(change) != change_keys:
            err("$.change", f"keys must be exactly {sorted(change_keys)}")
        if change.get("layer") not in LAYERS:
            err("$.change.layer", f"must be one of {sorted(LAYERS)}")
        for field in ("hypothesis", "baseline_version", "candidate_version"):
            if not isinstance(change.get(field), str) or not change[field].strip():
                err(f"$.change.{field}", "must be a non-empty string")
        variables = change.get("changed_variables")
        if not isinstance(variables, list) or len(variables) != 1 or not isinstance(variables[0], str):
            err("$.change.changed_variables", "must contain exactly one attributable variable")
        if change.get("baseline_version") == change.get("candidate_version"):
            err("$.change", "baseline and candidate versions must differ")
        allowed_pointers = change.get("allowed_json_pointers")
        if not isinstance(allowed_pointers, list) or len(allowed_pointers) != 1 or not isinstance(allowed_pointers[0], str) or not allowed_pointers[0].startswith("/"):
            err("$.change.allowed_json_pointers", "must contain exactly one JSON pointer")
            allowed_pointers = []
        layer_prefix = f"/{change.get('layer')}" if change.get("layer") in LAYERS else ""
        if allowed_pointers and not allowed_pointers[0].startswith(f"{layer_prefix}/"):
            err("$.change.allowed_json_pointers", "must be beneath the declared changed layer")
        variant_path = safe_path(change.get("variant_bundle_path"), root)
        if variant_path is None or not variant_path.is_file():
            err("$.change.variant_bundle_path", "must resolve beneath the evidence root")
        elif not is_hash(change.get("variant_bundle_sha256")) or sha256(variant_path) != change.get("variant_bundle_sha256"):
            err("$.change.variant_bundle_sha256", "does not match the variant bundle")
        else:
            try:
                variants = json.loads(variant_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                err("$.change.variant_bundle_path", f"bundle is invalid JSON: {exc}")
        if isinstance(variants, dict):
            if set(variants) != {"schema_version", "experiment_id", "baseline", "candidate"} or variants.get("schema_version") != 1 or variants.get("experiment_id") != data.get("experiment_id"):
                err("$.change.variant_bundle_path", "bundle schema or experiment identity is invalid")
            variant_keys = {"version", "prompt", "context", "tool", "loop", "model", "grader", "environment"}
            baseline_variant, candidate_variant = variants.get("baseline"), variants.get("candidate")
            for name, variant in (("baseline", baseline_variant), ("candidate", candidate_variant)):
                if not isinstance(variant, dict) or set(variant) != variant_keys:
                    err(f"$.change.variant_bundle.{name}", f"keys must be exactly {sorted(variant_keys)}")
            if isinstance(baseline_variant, dict) and isinstance(candidate_variant, dict):
                if baseline_variant.get("version") != change.get("baseline_version") or candidate_variant.get("version") != change.get("candidate_version"):
                    err("$.change.variant_bundle", "variant versions differ from the receipt")
                baseline_config = {key: value for key, value in baseline_variant.items() if key != "version"}
                candidate_config = {key: value for key, value in candidate_variant.items() if key != "version"}
                observed = diff_pointers(baseline_config, candidate_config)
                if observed != set(allowed_pointers):
                    err("$.change.allowed_json_pointers", f"declared {sorted(allowed_pointers)} but observed {sorted(observed)}")
                if all(set(variant) == variant_keys for variant in (baseline_variant, candidate_variant)):
                    expected_variant_bindings = {
                        name: {
                            "variant_sha256": canonical_sha(variant),
                            **{f"{layer}_sha256": canonical_sha(variant[layer]) for layer in sorted(LAYERS)},
                        }
                        for name, variant in (("baseline", baseline_variant), ("candidate", candidate_variant))
                    }

    claim = data.get("claim")
    claim_keys = {"estimand", "target", "generalization_claimed", "uncertainty_method", "limitations"}
    if not isinstance(claim, dict) or set(claim) != claim_keys:
        err("$.claim", f"keys must be exactly {sorted(claim_keys)}")
        claim = {}
    if claim.get("estimand") not in {"fixed_benchmark_performance", "task_population_performance"}:
        err("$.claim.estimand", "must identify fixed benchmark or task population performance")
    if not isinstance(claim.get("target"), str) or not claim.get("target", "").strip():
        err("$.claim.target", "must be a non-empty measurement target")
    if not isinstance(claim.get("generalization_claimed"), bool):
        err("$.claim.generalization_claimed", "must be boolean")
    if claim.get("uncertainty_method") not in {"none_fixed_benchmark", "task_cluster_bootstrap", "hierarchical_model"}:
        err("$.claim.uncertainty_method", "is invalid")
    if not isinstance(claim.get("limitations"), str) or not claim.get("limitations", "").strip():
        err("$.claim.limitations", "must be non-empty")
    if claim.get("generalization_claimed") is True:
        if claim.get("estimand") != "task_population_performance" or claim.get("uncertainty_method") not in {"task_cluster_bootstrap", "hierarchical_model"}:
            err("$.claim", "generalization requires a task-population estimand and task-level uncertainty method")
    elif claim.get("estimand") != "fixed_benchmark_performance" or claim.get("uncertainty_method") != "none_fixed_benchmark":
        err("$.claim", "a non-generalizing claim must use the fixed-benchmark estimand and uncertainty method")

    environment = data.get("environment")
    if not isinstance(environment, dict):
        err("$.environment", "must be an object")
    else:
        environment_keys = {"model", "harness", "tools_hash", "repo_fixture", "resource_class", "temperature"}
        if set(environment) != environment_keys:
            err("$.environment", f"keys must be exactly {sorted(environment_keys)}")
        for field in ("model", "harness", "tools_hash", "repo_fixture", "resource_class", "temperature"):
            if field not in environment or environment[field] == "":
                err(f"$.environment.{field}", "is required to freeze the comparison")
        if not is_hash(environment.get("tools_hash")) or not is_hash(environment.get("repo_fixture")):
            err("$.environment", "tools_hash and repo_fixture must be lowercase SHA-256 values")
        if not isinstance(environment.get("temperature"), (int, float)) or isinstance(environment.get("temperature"), bool) or not math.isfinite(environment.get("temperature", math.nan)) or environment.get("temperature", -1) < 0:
            err("$.environment.temperature", "must be a finite non-negative number")
        if isinstance(variants, dict):
            baseline_variant, candidate_variant = variants.get("baseline", {}), variants.get("candidate", {})
            layer = change.get("layer") if isinstance(change, dict) else None
            frozen_checks = []
            if layer != "model":
                frozen_checks.extend([
                    (environment.get("model"), baseline_variant.get("model", {}).get("id"), "model"),
                    (environment.get("model"), candidate_variant.get("model", {}).get("id"), "model"),
                    (environment.get("temperature"), baseline_variant.get("model", {}).get("temperature"), "temperature"),
                    (environment.get("temperature"), candidate_variant.get("model", {}).get("temperature"), "temperature"),
                ])
            if layer != "tool":
                frozen_checks.extend([
                    (environment.get("tools_hash"), baseline_variant.get("tool", {}).get("manifest_sha256"), "tools_hash"),
                    (environment.get("tools_hash"), candidate_variant.get("tool", {}).get("manifest_sha256"), "tools_hash"),
                ])
            if layer != "environment":
                for key, receipt_key in (("harness", "harness"), ("repo_fixture_sha256", "repo_fixture"), ("resource_class", "resource_class")):
                    frozen_checks.extend([
                        (environment.get(receipt_key), baseline_variant.get("environment", {}).get(key), receipt_key),
                        (environment.get(receipt_key), candidate_variant.get("environment", {}).get(key), receipt_key),
                    ])
            for receipt_value, bundle_value, label in frozen_checks:
                if receipt_value != bundle_value:
                    err(f"$.environment.{label}", "differs from the frozen variant bundle")

    datasets = data.get("datasets")
    task_to_suite: dict[str, str] = {}
    if not isinstance(datasets, dict):
        err("$.datasets", "must be an object")
        datasets = {}
    for suite in SUITES:
        tasks = datasets.get(suite)
        if not isinstance(tasks, list) or not tasks or any(not isinstance(x, str) or not x for x in tasks):
            err(f"$.datasets.{suite}", "must be a non-empty array of task IDs")
            continue
        if len(tasks) != len(set(tasks)):
            err(f"$.datasets.{suite}", "contains duplicate task IDs")
        for task in tasks:
            if task in task_to_suite:
                err(f"$.datasets.{suite}", f"task {task!r} also appears in {task_to_suite[task]}")
            task_to_suite[task] = suite

    gates = data.get("gates")
    gate_names = (
        "min_trials_per_task", "min_capability_quality_delta",
        "max_regression_pass_rate_drop", "max_holdout_pass_rate_drop",
        "max_per_task_pass_rate_drop",
        "max_cost_per_success_increase_percent", "max_latency_p95_increase_percent",
        "min_adversarial_safety_rate", "max_infrastructure_error_rate",
        "min_trace_review_fraction",
    )
    if not isinstance(gates, dict):
        err("$.gates", "must be an object")
        gates = {}
    for name in gate_names:
        value = gates.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            err(f"$.gates.{name}", "must be a finite non-negative number")
    if isinstance(gates.get("min_trials_per_task"), (int, float)) and gates["min_trials_per_task"] < 3:
        err("$.gates.min_trials_per_task", "must be at least 3")
    for name in ("min_adversarial_safety_rate", "max_infrastructure_error_rate", "min_trace_review_fraction"):
        if isinstance(gates.get(name), (int, float)) and gates[name] > 1:
            err(f"$.gates.{name}", "must be between 0 and 1")

    results = data.get("results")
    if not isinstance(results, dict):
        err("$.results", "must be an object")
        results = {}
    parsed: dict[str, list[dict[str, Any]]] = {}
    keys: dict[str, set[tuple[str, str, str]]] = {}
    for variant in ("baseline", "candidate"):
        trials = results.get(variant)
        if not isinstance(trials, list) or not trials:
            err(f"$.results.{variant}", "must be a non-empty array")
            trials = []
        parsed[variant] = []
        keys[variant] = set()
        counts: Counter[tuple[str, str]] = Counter()
        for index, trial in enumerate(trials):
            path = f"$.results.{variant}[{index}]"
            if not isinstance(trial, dict):
                err(path, "must be an object")
                continue
            suite, task, trial_id = trial.get("suite"), trial.get("task_id"), trial.get("trial_id")
            key = (suite, task, trial_id)
            if suite not in SUITES:
                err(f"{path}.suite", "invalid suite")
            if task_to_suite.get(task) != suite:
                err(f"{path}.task_id", "does not belong to the declared suite")
            if not isinstance(trial_id, str) or not trial_id:
                err(f"{path}.trial_id", "must be a non-empty string")
            if key in keys[variant]:
                err(path, "duplicate suite/task/trial tuple")
            keys[variant].add(key)
            counts[(suite, task)] += 1
            for field in ("passed", "safety_pass", "infrastructure_error"):
                if not isinstance(trial.get(field), bool):
                    err(f"{path}.{field}", "must be boolean")
            quality = trial.get("quality")
            if not isinstance(quality, (int, float)) or isinstance(quality, bool) or not math.isfinite(quality) or not 0 <= quality <= 1:
                err(f"{path}.quality", "must be between 0 and 1")
            for field in ("cost_usd", "latency_ms"):
                value = trial.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                    err(f"{path}.{field}", "must be a finite non-negative number")
            parsed[variant].append(trial)
        minimum = gates.get("min_trials_per_task", 3)
        for task, suite in task_to_suite.items():
            if counts[(suite, task)] < minimum:
                err(f"$.results.{variant}", f"{suite}/{task} has fewer than {minimum} trials")
    if keys.get("baseline") != keys.get("candidate"):
        err("$.results", "baseline and candidate must use identical suite/task/trial pairs")
    trial_maps = {
        variant: {(t.get("suite"), t.get("task_id"), t.get("trial_id")): t for t in trials}
        for variant, trials in parsed.items()
    }
    if keys.get("baseline") == keys.get("candidate"):
        for key in keys.get("baseline", set()):
            if trial_maps["baseline"][key].get("infrastructure_error") != trial_maps["candidate"][key].get("infrastructure_error"):
                err("$.results", f"infrastructure status differs for paired trial {key}")

    evidence = data.get("evidence")
    evidence_bound = False
    captured_evidence = False
    evidence_protocol: dict[str, Any] = {}
    if not isinstance(evidence, dict):
        err("$.evidence", "must be an object")
    else:
        expected_evidence = {"capture_kind", "path", "sha256", "captured_at", "runner", "attestation"}
        if set(evidence) != expected_evidence:
            err("$.evidence", f"keys must be exactly {sorted(expected_evidence)}")
        if evidence.get("capture_kind") not in {"illustrative_fixture", "captured_run"}:
            err("$.evidence.capture_kind", "must be illustrative_fixture or captured_run")
        if not is_timestamp(evidence.get("captured_at")):
            err("$.evidence.captured_at", "must be an ISO-8601 UTC timestamp")
        if not isinstance(evidence.get("runner"), str) or not evidence.get("runner", "").strip():
            err("$.evidence.runner", "must be a non-empty string")
        attestation = evidence.get("attestation")
        attestation_ok = False
        if evidence.get("capture_kind") == "illustrative_fixture":
            if attestation is not None:
                err("$.evidence.attestation", "must be null for illustrative fixtures")
        elif data.get("decision") == "promote":
            attestation_keys = {"provider", "repository", "signer_workflow", "signer_digest", "source_digest", "source_ref", "predicate_type", "deny_self_hosted_runners", "bundle_path", "bundle_sha256", "trusted_root_path", "trusted_root_sha256"}
            if not isinstance(attestation, dict) or set(attestation) != attestation_keys:
                err("$.evidence.attestation", f"keys must be exactly {sorted(attestation_keys)} for captured runs")
                attestation = {}
            if attestation.get("provider") != "github_sigstore":
                err("$.evidence.attestation.provider", "must be github_sigstore")
            if not REPO.fullmatch(str(attestation.get("repository", ""))):
                err("$.evidence.attestation.repository", "must be owner/repository")
            workflow = attestation.get("signer_workflow")
            expected_prefix = f"github.com/{attestation.get('repository', '')}/.github/workflows/"
            if not isinstance(workflow, str) or not workflow.startswith(expected_prefix) or not workflow.endswith((".yml", ".yaml")):
                err("$.evidence.attestation.signer_workflow", "must pin a workflow in the declared repository")
            for field in ("signer_digest", "source_digest"):
                if not is_revision(attestation.get(field)):
                    err(f"$.evidence.attestation.{field}", "must be a full lowercase revision digest")
            if not is_ref(attestation.get("source_ref")):
                err("$.evidence.attestation.source_ref", "must be a full heads or tags ref")
            if attestation.get("predicate_type") != PREDICATE:
                err("$.evidence.attestation.predicate_type", f"must be {PREDICATE}")
            if attestation.get("deny_self_hosted_runners") is not True:
                err("$.evidence.attestation.deny_self_hosted_runners", "must be true")
            for path_field, hash_field in (("bundle_path", "bundle_sha256"), ("trusted_root_path", "trusted_root_sha256")):
                bound_path = safe_path(attestation.get(path_field), root)
                if bound_path is None or not bound_path.is_file():
                    err(f"$.evidence.attestation.{path_field}", "must resolve beneath the evidence root")
                elif not is_hash(attestation.get(hash_field)) or sha256(bound_path) != attestation.get(hash_field):
                    err(f"$.evidence.attestation.{hash_field}", "does not match the bound file")
            policy_keys = {"schema_version", "provider", "repository", "signer_workflow", "signer_digest", "allowed_source_refs", "predicate_type", "oidc_issuer", "deny_self_hosted_runners"}
            if not isinstance(trust_policy, dict) or set(trust_policy) != policy_keys or trust_policy.get("schema_version") != 1:
                err("$.evidence.attestation", "promotion requires a valid external --attestation-policy")
                trust_policy = {}
            if trust_policy.get("provider") != "github_sigstore" or not REPO.fullmatch(str(trust_policy.get("repository", ""))):
                err("$.evidence.attestation", "external policy provider or repository is invalid")
            trusted_workflow = trust_policy.get("signer_workflow")
            trusted_prefix = f"github.com/{trust_policy.get('repository', '')}/.github/workflows/"
            if not isinstance(trusted_workflow, str) or not trusted_workflow.startswith(trusted_prefix) or ".." in trusted_workflow or not trusted_workflow.endswith((".yml", ".yaml")):
                err("$.evidence.attestation", "external policy signer workflow is invalid")
            if not is_revision(trust_policy.get("signer_digest")):
                err("$.evidence.attestation", "external policy signer digest is invalid")
            allowed_refs = trust_policy.get("allowed_source_refs")
            if not isinstance(allowed_refs, list) or not allowed_refs or any(not is_ref(value) for value in allowed_refs):
                err("$.evidence.attestation", "external policy source refs are invalid")
                allowed_refs = []
            if trust_policy.get("predicate_type") != PREDICATE or trust_policy.get("oidc_issuer") != "https://token.actions.githubusercontent.com" or trust_policy.get("deny_self_hosted_runners") is not True:
                err("$.evidence.attestation", "external policy predicate, OIDC issuer, or runner policy is invalid")
            comparisons = {
                "provider": trust_policy.get("provider"), "repository": trust_policy.get("repository"),
                "signer_workflow": trust_policy.get("signer_workflow"), "signer_digest": trust_policy.get("signer_digest"),
                "predicate_type": trust_policy.get("predicate_type"), "deny_self_hosted_runners": trust_policy.get("deny_self_hosted_runners"),
            }
            if any(attestation.get(key) != value for key, value in comparisons.items()) or attestation.get("source_ref") not in allowed_refs:
                err("$.evidence.attestation", "receipt expectations are not authorized by the external trust policy")
        elif attestation is not None:
            err("$.evidence.attestation", "must be null until a rejected captured run is promoted with verified provenance")
        artifact_path = safe_path(evidence.get("path"), root)
        artifact: Any = None
        if artifact_path is None or not artifact_path.is_file():
            err("$.evidence.path", "must resolve to a file beneath the evidence root")
        elif not is_hash(evidence.get("sha256")) or sha256(artifact_path) != evidence.get("sha256"):
            err("$.evidence.sha256", "does not match the evidence artifact")
        else:
            try:
                artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                err("$.evidence.path", f"artifact is invalid JSON: {exc}")
        if isinstance(artifact, dict):
            artifact_keys = {"schema_version", "capture_kind", "experiment_id", "captured_at", "runner", "experiment_binding_sha256", "variant_bindings", "protocol", "trials"}
            if set(artifact) != artifact_keys or artifact.get("schema_version") != 2:
                err("$.evidence.path", f"artifact keys must be exactly {sorted(artifact_keys)} and schema_version must be 2")
            if any(artifact.get(key) != evidence.get(key) for key in ("capture_kind", "captured_at", "runner")):
                err("$.evidence", "receipt provenance differs from the evidence artifact")
            if artifact.get("experiment_id") != data.get("experiment_id"):
                err("$.evidence", "experiment_id differs from the evidence artifact")
            binding = {name: data.get(name) for name in ("change", "claim", "environment", "datasets", "gates")}
            if artifact.get("experiment_binding_sha256") != canonical_sha(binding):
                err("$.evidence", "experiment change, claim, environment, datasets, or gates differ from the captured binding")

            variant_bindings = artifact.get("variant_bindings")
            binding_keys = {"variant_sha256", *(f"{layer}_sha256" for layer in LAYERS)}
            if not isinstance(variant_bindings, dict) or set(variant_bindings) != {"baseline", "candidate"}:
                err("$.evidence.variant_bindings", "must contain exactly baseline and candidate")
            elif any(not isinstance(value, dict) or set(value) != binding_keys or any(not is_hash(item) for item in value.values()) for value in variant_bindings.values()):
                err("$.evidence.variant_bindings", f"each binding must contain exactly {sorted(binding_keys)} as lowercase SHA-256 values")
            elif expected_variant_bindings is None or variant_bindings != expected_variant_bindings:
                err("$.evidence.variant_bindings", "do not match the exact hash-bound baseline and candidate configurations")

            protocol = artifact.get("protocol")
            protocol_keys = {"dataset_frozen_before_candidate", "holdout_access", "optimizer_saw_holdout_results", "paired_seed_policy", "execution_order", "blind_grading", "grader_role", "optimizer_role"}
            if not isinstance(protocol, dict) or set(protocol) != protocol_keys:
                err("$.evidence.protocol", f"keys must be exactly {sorted(protocol_keys)}")
                protocol = {}
            evidence_protocol = protocol
            if protocol.get("dataset_frozen_before_candidate") is not True:
                err("$.evidence.protocol.dataset_frozen_before_candidate", "must be true")
            if protocol.get("holdout_access") != "evaluation_only" or protocol.get("optimizer_saw_holdout_results") is not False:
                err("$.evidence.protocol.holdout_access", "holdout must be evaluation-only and hidden from the optimizer")
            if protocol.get("paired_seed_policy") != "identical":
                err("$.evidence.protocol.paired_seed_policy", "must be identical")
            if protocol.get("execution_order") != "counterbalanced":
                err("$.evidence.protocol.execution_order", "must be counterbalanced")
            if protocol.get("blind_grading") is not True:
                err("$.evidence.protocol.blind_grading", "must be true")
            roles = (protocol.get("grader_role"), protocol.get("optimizer_role"))
            if not all(isinstance(role, str) and role.strip() for role in roles) or roles[0] == roles[1]:
                err("$.evidence.protocol.grader_role", "grader and optimizer roles must be non-empty and independent")

            artifact_trials = artifact.get("trials")
            if not isinstance(artifact_trials, list) or not artifact_trials:
                err("$.evidence.trials", "must be a non-empty array")
                artifact_trials = []
            evidence_map: dict[tuple[Any, Any, Any, Any], dict[str, Any]] = {}
            pair_meta: dict[tuple[Any, Any, Any], dict[str, tuple[Any, Any]]] = defaultdict(dict)
            for index, trial in enumerate(artifact_trials):
                label = f"$.evidence.trials[{index}]"
                trial_keys = {"variant", "suite", "task_id", "trial_id", "seed", "run_order", "output", "trace", "grader", "cost_usd", "latency_ms", "infrastructure_error"}
                if not isinstance(trial, dict) or set(trial) != trial_keys:
                    err(label, f"keys must be exactly {sorted(trial_keys)}")
                    continue
                variant = trial.get("variant")
                key3 = (trial.get("suite"), trial.get("task_id"), trial.get("trial_id"))
                key4 = (variant, *key3)
                if variant not in {"baseline", "candidate"} or key3 not in keys.get(variant, set()):
                    err(label, "does not identify a declared receipt trial")
                if key4 in evidence_map:
                    err(label, "duplicates an evidence trial")
                evidence_map[key4] = trial
                if not isinstance(trial.get("seed"), int) or isinstance(trial.get("seed"), bool) or trial["seed"] < 0:
                    err(f"{label}.seed", "must be a non-negative integer")
                if trial.get("run_order") not in {1, 2}:
                    err(f"{label}.run_order", "must be 1 or 2")
                if not isinstance(trial.get("output"), str):
                    err(f"{label}.output", "must be a string")
                if not isinstance(trial.get("trace"), list) or not trial.get("trace"):
                    err(f"{label}.trace", "must be a non-empty array")
                grader = trial.get("grader")
                grader_keys = {"id", "version", "independent", "blind", "quality", "passed", "safety_pass"}
                if not isinstance(grader, dict) or set(grader) != grader_keys:
                    err(f"{label}.grader", f"keys must be exactly {sorted(grader_keys)}")
                    grader = {}
                if not all(isinstance(grader.get(key), str) and grader[key].strip() for key in ("id", "version")):
                    err(f"{label}.grader", "id and version must be non-empty")
                if grader.get("independent") is not True or grader.get("blind") is not True:
                    err(f"{label}.grader", "must be independent and blind")
                quality = grader.get("quality")
                if not isinstance(quality, (int, float)) or isinstance(quality, bool) or not 0 <= quality <= 1:
                    err(f"{label}.grader.quality", "must be between 0 and 1")
                for field in ("passed", "safety_pass"):
                    if not isinstance(grader.get(field), bool):
                        err(f"{label}.grader.{field}", "must be boolean")
                for field in ("cost_usd", "latency_ms"):
                    value = trial.get(field)
                    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                        err(f"{label}.{field}", "must be finite and non-negative")
                if not isinstance(trial.get("infrastructure_error"), bool):
                    err(f"{label}.infrastructure_error", "must be boolean")
                pair_meta[key3][variant] = (trial.get("seed"), trial.get("run_order"))

                receipt_trial = trial_maps.get(variant, {}).get(key3)
                derived = {
                    "suite": trial.get("suite"), "task_id": trial.get("task_id"), "trial_id": trial.get("trial_id"),
                    "passed": grader.get("passed"), "quality": grader.get("quality"), "safety_pass": grader.get("safety_pass"),
                    "cost_usd": trial.get("cost_usd"), "latency_ms": trial.get("latency_ms"),
                    "infrastructure_error": trial.get("infrastructure_error"),
                }
                if receipt_trial != derived:
                    err(label, "captured trial does not exactly derive the receipt result")
            expected_keys = {(variant, *key) for variant in ("baseline", "candidate") for key in keys.get(variant, set())}
            if set(evidence_map) != expected_keys:
                err("$.evidence.trials", "must exactly cover every baseline and candidate receipt trial")
            order_counts: Counter[int] = Counter()
            for key3, variants in pair_meta.items():
                if set(variants) != {"baseline", "candidate"}:
                    continue
                baseline_meta, candidate_meta = variants["baseline"], variants["candidate"]
                if baseline_meta[0] != candidate_meta[0]:
                    err("$.evidence.trials", f"paired seed differs for {key3}")
                if {baseline_meta[1], candidate_meta[1]} != {1, 2}:
                    err("$.evidence.trials", f"paired run order is not counterbalanced for {key3}")
                order_counts[baseline_meta[1]] += 1
            if order_counts and abs(order_counts[1] - order_counts[2]) > 1:
                err("$.evidence.trials", "baseline-first and candidate-first pairs must be balanced")
            evidence_bound = not any(item.startswith("$.evidence") for item in errors)
            if evidence_bound and evidence.get("capture_kind") == "captured_run" and data.get("decision") == "promote":
                if verify_crypto and isinstance(attestation, dict):
                    attestation_ok, message = verify_attestation(artifact_path, attestation, trust_policy, root)
                    if not attestation_ok:
                        err("$.evidence.attestation", message)
                elif not verify_crypto:
                    err("$.evidence.attestation", "captured promotion requires --verify-attestation")
            captured_evidence = evidence_bound and evidence.get("capture_kind") == "captured_run" and attestation_ok
    minimum_valid = gates.get("min_trials_per_task", 3)
    for variant, trials in parsed.items():
        valid_counts = Counter((t.get("suite"), t.get("task_id")) for t in trials if t.get("infrastructure_error") is False)
        for task, suite in task_to_suite.items():
            if valid_counts[(suite, task)] < minimum_valid:
                err(f"$.results.{variant}", f"{suite}/{task} has fewer than {minimum_valid} valid non-infrastructure trials")

    metrics: dict[str, dict[str, float]] = {}
    for variant, trials in parsed.items():
        valid = [t for t in trials if t.get("infrastructure_error") is False]
        successes = [t for t in valid if t.get("passed") is True]
        metrics[variant] = {
            "capability_quality": mean([float(t["quality"]) for t in valid if t.get("suite") == "capability" and isinstance(t.get("quality"), (int, float))]),
            "regression_pass_rate": mean([1.0 if t.get("passed") else 0.0 for t in valid if t.get("suite") == "regression"]),
            "holdout_pass_rate": mean([1.0 if t.get("passed") else 0.0 for t in valid if t.get("suite") == "holdout"]),
            "adversarial_safety_rate": mean([1.0 if t.get("safety_pass") else 0.0 for t in valid if t.get("suite") == "adversarial"]),
            "cost_per_success": sum(float(t.get("cost_usd", 0)) for t in valid) / len(successes) if successes else math.inf,
            "latency_p95": percentile95([float(t.get("latency_ms", 0)) for t in valid]),
            "infrastructure_error_rate": mean([1.0 if t.get("infrastructure_error") else 0.0 for t in trials]),
        }
    summary["metrics"] = metrics

    if len(metrics) == 2 and gates:
        baseline, candidate = metrics["baseline"], metrics["candidate"]
        checks = {
            "capability_quality": candidate["capability_quality"] - baseline["capability_quality"] >= gates.get("min_capability_quality_delta", math.inf),
            "regression": baseline["regression_pass_rate"] - candidate["regression_pass_rate"] <= gates.get("max_regression_pass_rate_drop", -1),
            "holdout": baseline["holdout_pass_rate"] - candidate["holdout_pass_rate"] <= gates.get("max_holdout_pass_rate_drop", -1),
            "safety": candidate["adversarial_safety_rate"] >= gates.get("min_adversarial_safety_rate", math.inf) and candidate["adversarial_safety_rate"] >= baseline["adversarial_safety_rate"],
            "cost": increase_percent(candidate["cost_per_success"], baseline["cost_per_success"]) <= gates.get("max_cost_per_success_increase_percent", -1),
            "latency": increase_percent(candidate["latency_p95"], baseline["latency_p95"]) <= gates.get("max_latency_p95_increase_percent", -1),
            "infrastructure": candidate["infrastructure_error_rate"] <= gates.get("max_infrastructure_error_rate", -1),
        }
        per_task_ok = True
        for suite in ("regression", "holdout"):
            for task in datasets.get(suite, []):
                baseline_trials = [t for t in parsed["baseline"] if t.get("suite") == suite and t.get("task_id") == task and t.get("infrastructure_error") is False]
                candidate_trials = [t for t in parsed["candidate"] if t.get("suite") == suite and t.get("task_id") == task and t.get("infrastructure_error") is False]
                baseline_rate = mean([1.0 if t.get("passed") else 0.0 for t in baseline_trials])
                candidate_rate = mean([1.0 if t.get("passed") else 0.0 for t in candidate_trials])
                if baseline_rate - candidate_rate > gates.get("max_per_task_pass_rate_drop", -1):
                    per_task_ok = False
        checks["per_task_regression"] = per_task_ok
    else:
        checks = {}

    review = data.get("trace_review")
    review_ok = True
    if not isinstance(review, dict):
        err("$.trace_review", "must be an object")
        review_ok = False
    else:
        if not review.get("optimizer_role") or not review.get("reviewer_role"):
            err("$.trace_review", "optimizer_role and reviewer_role are required"); review_ok = False
        elif review["optimizer_role"] == review["reviewer_role"]:
            err("$.trace_review.reviewer_role", "must be independent from optimizer_role"); review_ok = False
        if evidence_protocol:
            if review.get("optimizer_role") != evidence_protocol.get("optimizer_role"):
                err("$.trace_review.optimizer_role", "must match the captured optimization protocol"); review_ok = False
            if review.get("reviewer_role") in {evidence_protocol.get("optimizer_role"), evidence_protocol.get("grader_role")}:
                err("$.trace_review.reviewer_role", "must differ from captured optimizer and grader roles"); review_ok = False
        reviewed = review.get("reviewed_candidate_trials")
        candidate_count = len(parsed.get("candidate", []))
        required = math.ceil(candidate_count * gates.get("min_trace_review_fraction", 1))
        if not isinstance(reviewed, list) or len(set(reviewed)) < required:
            err("$.trace_review.reviewed_candidate_trials", f"must review at least {required} unique candidate trials"); review_ok = False
        elif not set(reviewed) <= {f"{suite}/{task}/{trial}" for suite, task, trial in keys.get("candidate", set())}:
            err("$.trace_review.reviewed_candidate_trials", "contains unknown candidate trial IDs"); review_ok = False
        if review.get("grader_gaming_found") is not False:
            err("$.trace_review.grader_gaming_found", "must be false for promotion"); review_ok = False
        if not isinstance(review.get("findings"), str) or not review["findings"].strip():
            err("$.trace_review.findings", "must record review findings"); review_ok = False
    checks["trace_review"] = review_ok
    checks["evidence_binding"] = evidence_bound
    summary["checks"] = checks
    summary["captured_evidence"] = captured_evidence
    eligible = bool(checks) and all(checks.values()) and captured_evidence and not errors
    summary["eligible_for_promotion"] = eligible
    decision = data.get("decision")
    if decision not in {"promote", "reject"}:
        err("$.decision", "must be promote or reject")
    elif decision == "promote" and not eligible:
        err("$.decision", "cannot promote because one or more gates failed")
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--evidence-root", type=Path, default=Path("."))
    parser.add_argument("--verify-attestation", action="store_true", help="cryptographically verify captured promotion evidence with gh")
    parser.add_argument("--attestation-policy", type=Path, help="protected trust policy; required for captured promotion")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        path = regular_input_file(args.file)
        if path is None: raise ValueError("file must be a regular file, not a symlink")
        data = json.loads(path.read_text(encoding="utf-8"))
        policy_path = regular_input_file(args.attestation_policy) if args.attestation_policy else None
        if args.attestation_policy and policy_path is None: raise ValueError("attestation policy must be a regular file, not a symlink")
        trust_policy = json.loads(policy_path.read_text(encoding="utf-8")) if policy_path else None
        errors, summary = validate(data, args.evidence_root.resolve(), args.verify_attestation, trust_policy)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors, summary = [f"$: invalid JSON: {exc}"], {}
    output = {"ok": not errors, "errors": errors, **summary}
    if args.json:
        print(json.dumps(json_safe(output), indent=2, allow_nan=False))
    elif errors:
        print("optimization run invalid", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    else:
        print(f"optimization run valid: {args.file}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
