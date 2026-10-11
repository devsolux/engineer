#!/usr/bin/env python3
"""Check an agent trajectory against its execution contract."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(contract, trace):
    errors = []
    def err(path, message): errors.append(f"{path}: {message}")
    events = trace.get("events") if isinstance(trace, dict) else None
    if not isinstance(events, list) or not events: return ["$.events: must be a non-empty array"]
    if len(events) > contract["loop"]["max_steps"]: err("$.events", "exceeds contract max_steps")
    seqs = [event.get("seq") for event in events if isinstance(event, dict)]
    if seqs != list(range(1, len(events) + 1)): err("$.events[*].seq", "must be contiguous from 1")

    tools = {tool["name"]: tool for tool in contract["tools"]}
    security = contract["security"]
    steps = {step["id"] for step in contract["plan"]}
    acceptance = {item["id"] for item in contract["acceptance"]}
    observations, actions, completed, planned, observed_hashes = {}, {}, set(), set(), []
    last_checkpoint = 0
    latest_action_or_observation = 0
    latest_observed_hash = None
    stop_count = 0
    for index, event in enumerate(events):
        path = f"$.events[{index}]"
        if not isinstance(event, dict): err(path, "must be an object"); continue
        phase = event.get("phase")
        if phase == "plan":
            if event.get("step_id") not in steps: err(f"{path}.step_id", "must reference a contract plan step")
            else: planned.add(event.get("step_id"))
        elif phase == "act":
            action_id, tool_name = event.get("action_id"), event.get("tool")
            if not action_id or action_id in actions: err(f"{path}.action_id", "must be present and unique")
            actions[action_id] = index
            latest_action_or_observation = index + 1
            tool = tools.get(tool_name)
            if tool is None: err(f"{path}.tool", "unknown tool")
            else:
                if tool["class"] != "read" and event.get("approval") != tool["approval"]: err(f"{path}.approval", "does not match mutation approval policy")
                sinks = set(event.get("output_sinks", []))
                if not sinks <= set(tool.get("allowed_sinks", [])): err(f"{path}.output_sinks", "contains an undeclared sink")
                if not sinks <= set(security.get("allowed_sinks", [])): err(f"{path}.output_sinks", "violates the contract security sink policy")
                sources = set(event.get("input_sources", []))
                classes = set(event.get("data_classes", []))
                crosses_domain = tool["class"].startswith("external_") and bool(sinks)
                risky_input = bool(sources & set(security.get("untrusted_sources", [])) or classes & set(security.get("sensitive_data", [])))
                if crosses_domain and risky_input and event.get("user_confirmation") is not True:
                    err(f"{path}.user_confirmation", "cross-domain transfer of untrusted or sensitive data requires confirmation")
        elif phase == "observe":
            action_id = event.get("action_id")
            if action_id not in actions: err(f"{path}.action_id", "has no preceding action")
            elif action_id in observations: err(f"{path}.action_id", "duplicates an observation")
            observations[action_id] = index
            latest_action_or_observation = index + 1
            if not isinstance(event.get("ok"), bool): err(f"{path}.ok", "must be boolean")
            if not isinstance(event.get("evidence"), list) or not event.get("evidence"): err(f"{path}.evidence", "observation requires evidence")
            if not isinstance(event.get("state_hash"), str) or not event.get("state_hash"): err(f"{path}.state_hash", "observation requires state hash")
            else:
                observed_hashes.append(event["state_hash"])
                latest_observed_hash = event["state_hash"]
        elif phase == "checkpoint":
            last_checkpoint = index + 1
            ids = event.get("completed_step_ids", [])
            if not isinstance(ids, list) or not set(ids) <= steps: err(f"{path}.completed_step_ids", "contains an unknown step")
            elif not set(ids) <= planned: err(f"{path}.completed_step_ids", "contains a step not planned in this trajectory")
            completed.update(ids)
            if not event.get("evidence"): err(f"{path}.evidence", "checkpoint requires evidence")
            if latest_observed_hash is None or event.get("state_hash") != latest_observed_hash: err(f"{path}.state_hash", "must match the latest observed state")
            if last_checkpoint <= latest_action_or_observation: err(path, "must follow the latest action and observation")
        elif phase == "stop":
            stop_count += 1
            if index != len(events) - 1: err(path, "stop must be the final event")
            if event.get("reason") == "success":
                if event.get("verification_passed") is not True: err(f"{path}.verification_passed", "success requires passing verification")
                if set(event.get("acceptance_ids", [])) != acceptance: err(f"{path}.acceptance_ids", "success must cover every acceptance criterion")
                if not event.get("evidence"): err(f"{path}.evidence", "success requires evidence")
                if completed != steps: err(path, "success requires every plan step checkpointed")
                if last_checkpoint <= latest_action_or_observation: err(path, "success requires a fresh checkpoint after the final action and observation")
            elif event.get("reason") not in set(contract.get("stop_conditions", [])):
                err(f"{path}.reason", "must be success or a declared contract stop condition")
        elif phase not in {"sense", "critique"}: err(f"{path}.phase", "unknown phase")

    missing_observations = set(actions) - set(observations)
    if missing_observations: err("$.events", f"actions without observations: {sorted(missing_observations)}")
    if actions and last_checkpoint == 0: err("$.events", "mutating work requires a checkpoint")
    if stop_count != 1: err("$.events", "trajectory requires exactly one final stop event")
    limit = contract["loop"]["no_progress_limit"]
    run = 1
    for previous, current in zip(observed_hashes, observed_hashes[1:]):
        run = run + 1 if current == previous else 1
        if run >= limit: err("$.events", "reaches no_progress_limit with unchanged state"); break
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trajectory", type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    trajectory = regular_input_file(args.trajectory)
    contract = regular_input_file(args.contract)
    if trajectory is None or contract is None:
        errors = ["$: trajectory and contract must each be a regular file, not a symlink"]
    else:
        try: errors = validate(load(contract), load(trajectory))
        except (OSError, json.JSONDecodeError, KeyError) as exc: errors = [f"$: invalid input: {exc}"]
    if args.json: print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        print("agentic trajectory invalid", file=sys.stderr)
        for error in errors: print(f"- {error}", file=sys.stderr)
    else: print(f"agentic trajectory valid: {args.trajectory}")
    return bool(errors)


if __name__ == "__main__": raise SystemExit(main())
