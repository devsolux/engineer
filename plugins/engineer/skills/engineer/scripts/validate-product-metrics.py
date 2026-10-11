#!/usr/bin/env python3
"""Validate an engineer product measurement plan without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

ID = re.compile(r"^[a-z][a-z0-9_]*$")
METRIC_KINDS = {"north_star", "input", "outcome", "guardrail", "diagnostic"}
GRAINS = {"event", "session", "user", "account", "workspace", "subscription"}
CADENCES = {"realtime", "hourly", "daily", "weekly", "monthly", "quarterly"}
EVENT_SOURCES = {"client", "server"}
CRITICALITIES = {"interaction", "durable", "money", "permission"}
PROPERTY_TYPES = {"string", "number", "boolean", "integer", "timestamp", "enum", "object"}
CLASSIFICATIONS = {"none", "pii", "sensitive", "revenue"}
FORBIDDEN_PROPERTY_NAMES = {
    "api_key", "authorization", "card_number", "cvv", "password", "raw_prompt",
    "secret", "session_cookie", "token",
}


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def nonempty(self, obj: dict[str, Any], field: str, path: str) -> None:
        if not isinstance(obj.get(field), str) or not obj[field].strip():
            self.error(f"{path}.{field}", "must be a non-empty string")

    def identifier(self, value: Any, path: str) -> None:
        if not isinstance(value, str) or ID.fullmatch(value) is None:
            self.error(path, "must match ^[a-z][a-z0-9_]*$")

    def unique_strings(self, value: Any, path: str, *, allow_empty: bool = False) -> list[str]:
        if not isinstance(value, list) or (not allow_empty and not value):
            self.error(path, "must be a non-empty array" if not allow_empty else "must be an array")
            return []
        strings = [item for item in value if isinstance(item, str) and item.strip()]
        if len(strings) != len(value):
            self.error(path, "must contain only non-empty strings")
        if len(set(strings)) != len(strings):
            self.error(path, "must not contain duplicates")
        return strings

    def validate(self, data: Any) -> list[str]:
        if not isinstance(data, dict):
            return ["$: must be a JSON object"]
        if data.get("schema_version") != 1:
            self.error("$.schema_version", "must equal 1")
        self.nonempty(data, "product", "$")
        if "as_of" in data:
            try:
                date.fromisoformat(data["as_of"])
            except (TypeError, ValueError):
                self.error("$.as_of", "must be an ISO date (YYYY-MM-DD)")

        metrics = data.get("metrics")
        events = data.get("events")
        experiments = data.get("experiments", [])
        if not isinstance(metrics, list) or not metrics:
            self.error("$.metrics", "must be a non-empty array")
            metrics = []
        if not isinstance(events, list) or not events:
            self.error("$.events", "must be a non-empty array")
            events = []
        if not isinstance(experiments, list):
            self.error("$.experiments", "must be an array")
            experiments = []

        metric_map = self.validate_metrics(metrics)
        event_names = self.validate_events(events)
        self.validate_north_star(data.get("north_star"), metric_map)
        self.validate_metric_links(metrics, metric_map)
        self.validate_experiments(experiments, metric_map, event_names)
        return self.errors

    def validate_metrics(self, metrics: list[Any]) -> dict[str, dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        required = ("name", "question", "formula", "source", "owner", "freshness_slo", "decision_rule")
        for index, metric in enumerate(metrics):
            path = f"$.metrics[{index}]"
            if not isinstance(metric, dict):
                self.error(path, "must be an object")
                continue
            metric_id = metric.get("id")
            self.identifier(metric_id, f"{path}.id")
            if isinstance(metric_id, str):
                if metric_id in found:
                    self.error(f"{path}.id", f"duplicate metric id {metric_id!r}")
                else:
                    found[metric_id] = metric
            for field in required:
                self.nonempty(metric, field, path)
            if metric.get("kind") not in METRIC_KINDS:
                self.error(f"{path}.kind", f"must be one of {sorted(METRIC_KINDS)}")
            if metric.get("grain") not in GRAINS:
                self.error(f"{path}.grain", f"must be one of {sorted(GRAINS)}")
            if metric.get("cadence") not in CADENCES:
                self.error(f"{path}.cadence", f"must be one of {sorted(CADENCES)}")
            self.unique_strings(metric.get("segments"), f"{path}.segments")
            self.unique_strings(metric.get("guardrails"), f"{path}.guardrails", allow_empty=True)
        return found

    def validate_north_star(self, north_star: Any, metrics: dict[str, dict[str, Any]]) -> None:
        path = "$.north_star"
        if not isinstance(north_star, dict):
            self.error(path, "must be an object")
            return
        self.identifier(north_star.get("metric_id"), f"{path}.metric_id")
        self.nonempty(north_star, "value_moment", path)
        north_metrics = [key for key, metric in metrics.items() if metric.get("kind") == "north_star"]
        if len(north_metrics) != 1:
            self.error("$.metrics", "must contain exactly one north_star metric")
        selected = north_star.get("metric_id")
        if selected not in metrics:
            self.error(f"{path}.metric_id", "must reference an existing metric")
        elif metrics[selected].get("kind") != "north_star":
            self.error(f"{path}.metric_id", "must reference the north_star metric")

    def validate_metric_links(self, metrics: list[Any], metric_map: dict[str, dict[str, Any]]) -> None:
        for index, metric in enumerate(metrics):
            if not isinstance(metric, dict):
                continue
            for guardrail in metric.get("guardrails", []):
                linked = metric_map.get(guardrail)
                path = f"$.metrics[{index}].guardrails"
                if linked is None:
                    self.error(path, f"references unknown metric {guardrail!r}")
                elif linked.get("kind") != "guardrail":
                    self.error(path, f"{guardrail!r} is not a guardrail metric")

    def validate_events(self, events: list[Any]) -> set[str]:
        names: set[str] = set()
        for index, event in enumerate(events):
            path = f"$.events[{index}]"
            if not isinstance(event, dict):
                self.error(path, "must be an object")
                continue
            name = event.get("name")
            self.identifier(name, f"{path}.name")
            if isinstance(name, str):
                if name in names:
                    self.error(f"{path}.name", f"duplicate event name {name!r}")
                names.add(name)
            for field in ("description", "owner"):
                self.nonempty(event, field, path)
            if not isinstance(event.get("version"), int) or event["version"] < 1:
                self.error(f"{path}.version", "must be a positive integer")
            source = event.get("source")
            criticality = event.get("criticality")
            if source not in EVENT_SOURCES:
                self.error(f"{path}.source", f"must be one of {sorted(EVENT_SOURCES)}")
            if criticality not in CRITICALITIES:
                self.error(f"{path}.criticality", f"must be one of {sorted(CRITICALITIES)}")
            self.unique_strings(event.get("identities"), f"{path}.identities")
            if criticality in {"durable", "money", "permission"}:
                if source != "server":
                    self.error(f"{path}.source", f"{criticality} events must be server events")
                self.nonempty(event, "dedupe_key", path)
            self.validate_properties(event.get("properties"), f"{path}.properties")
        return names

    def validate_properties(self, properties: Any, path: str) -> None:
        if not isinstance(properties, list):
            self.error(path, "must be an array")
            return
        names: set[str] = set()
        for index, prop in enumerate(properties):
            prop_path = f"{path}[{index}]"
            if not isinstance(prop, dict):
                self.error(prop_path, "must be an object")
                continue
            name = prop.get("name")
            self.identifier(name, f"{prop_path}.name")
            if isinstance(name, str):
                if name in names:
                    self.error(f"{prop_path}.name", f"duplicate property name {name!r}")
                names.add(name)
                if name in FORBIDDEN_PROPERTY_NAMES:
                    self.error(f"{prop_path}.name", "must not collect secrets, raw prompts, or raw payment credentials")
            prop_type = prop.get("type")
            classification = prop.get("classification")
            if prop_type not in PROPERTY_TYPES:
                self.error(f"{prop_path}.type", f"must be one of {sorted(PROPERTY_TYPES)}")
            if not isinstance(prop.get("required"), bool):
                self.error(f"{prop_path}.required", "must be a boolean")
            if classification not in CLASSIFICATIONS:
                self.error(f"{prop_path}.classification", f"must be one of {sorted(CLASSIFICATIONS)}")
            if prop_type == "enum":
                self.unique_strings(prop.get("enum_values"), f"{prop_path}.enum_values")
            if classification in {"pii", "sensitive"}:
                self.nonempty(prop, "privacy_basis", prop_path)
                if not isinstance(prop.get("retention_days"), int) or prop["retention_days"] < 1:
                    self.error(f"{prop_path}.retention_days", "must be a positive integer for pii or sensitive data")

    def validate_experiments(
        self, experiments: list[Any], metrics: dict[str, dict[str, Any]], events: set[str]
    ) -> None:
        ids: set[str] = set()
        for index, experiment in enumerate(experiments):
            path = f"$.experiments[{index}]"
            if not isinstance(experiment, dict):
                self.error(path, "must be an object")
                continue
            experiment_id = experiment.get("id")
            self.identifier(experiment_id, f"{path}.id")
            if isinstance(experiment_id, str):
                if experiment_id in ids:
                    self.error(f"{path}.id", f"duplicate experiment id {experiment_id!r}")
                ids.add(experiment_id)
            for field in ("hypothesis", "eligible_cohort", "decision_rule", "owner"):
                self.nonempty(experiment, field, path)
            if experiment.get("randomization_unit") not in {"user", "account", "workspace"}:
                self.error(f"{path}.randomization_unit", "must be user, account, or workspace")
            if experiment.get("exposure_event") not in events:
                self.error(f"{path}.exposure_event", "must reference an existing event")
            if experiment.get("primary_metric") not in metrics:
                self.error(f"{path}.primary_metric", "must reference an existing metric")
            guardrails = self.unique_strings(experiment.get("guardrails"), f"{path}.guardrails")
            for guardrail in guardrails:
                linked = metrics.get(guardrail)
                if linked is None:
                    self.error(f"{path}.guardrails", f"references unknown metric {guardrail!r}")
                elif linked.get("kind") != "guardrail":
                    self.error(f"{path}.guardrails", f"{guardrail!r} is not a guardrail metric")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    try:
        path = regular_input_file(args.file)
        if path is None: raise ValueError("file must be a regular file, not a symlink")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors = [f"$: cannot read valid JSON: {exc}"]
    else:
        errors = Validator().validate(data)
    result = {"ok": not errors, "file": str(args.file), "errors": errors}
    if args.json_output:
        print(json.dumps(result, indent=2))
    elif errors:
        print(f"measurement plan invalid: {args.file}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    else:
        print(f"measurement plan valid: {args.file}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
