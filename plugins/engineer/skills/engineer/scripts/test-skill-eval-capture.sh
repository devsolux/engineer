#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/capture-skill-eval.py"
SAMPLE="$ROOT/templates/agentic/skill-eval-job.sample.json"
TMP="$(mktemp -d)"
mkdir -p "$ROOT/.engineer"
ROOT_TMP="$(mktemp -d "$ROOT/.engineer/host-binding-test.XXXXXX")"
trap 'rm -rf "$TMP" "$ROOT_TMP"; rm -f "$ROOT/templates/engineer-bundle-fixture.pyc"' EXIT
cd "$ROOT"

# Runtime bytecode and caches must not change the reviewed package digest.
printf 'fixture\n' >"$ROOT/templates/engineer-bundle-fixture.pyc"
python3 "$SCRIPT" "$SAMPLE" --print-command >/dev/null
rm -f "$ROOT/templates/engineer-bundle-fixture.pyc"

python3 "$SCRIPT" "$SAMPLE" --print-command >"$TMP/codex-command.json"
python3 - "$TMP/codex-command.json" <<'PY'
import json
import sys

argv = json.load(open(sys.argv[1], encoding="utf-8"))["argv"]
required = {"--ephemeral", "--ignore-user-config", "--strict-config", "--ignore-rules", "--json", "read-only", "never", 'web_search="disabled"'}
missing = required - set(argv)
assert not missing, missing
assert "danger-full-access" not in argv
assert "--dangerously-bypass-approvals-and-sandbox" not in argv
assert argv[-1].startswith("$engineer\n\n")
assert argv[-1].endswith("[routing-probe:alpha]")
PY

python3 - "$SAMPLE" "$TMP/codex-implicit.json" <<'PY'
import hashlib,json,sys
d=json.load(open(sys.argv[1])); d["scenario"]["id"]=121; d["scenario"]["activation_mode"]="implicit"; d["scenario"]["invocation"]=None
json.dump(d,open(sys.argv[2],"w"),indent=2)
PY
python3 "$SCRIPT" "$TMP/codex-implicit.json" --print-command >"$TMP/codex-implicit-command.json"
python3 - "$TMP/codex-implicit-command.json" <<'PY'
import json,sys
argv=json.load(open(sys.argv[1]))["argv"]; prompt=argv[-1]
assert "$engineer" not in prompt and "/engineer" not in prompt
assert prompt.endswith("[routing-probe:alpha]")
PY

python3 - "$SAMPLE" "$TMP/claude.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
data["host"] = "claude"
data["scenario"]["invocation"] = "/engineer-eval:engineer"
data["authentication"]["api_key_env"] = "ANTHROPIC_API_KEY"
data["host_inventory"].update({
    "host": "claude",
    "executable_sha256": "f" * 64,
    "version_output_sha256": "1" * 64,
    "help_output_sha256": "2" * 64,
    "required_capabilities": ["bare_mode", "no_persistence", "non_interactive", "permission_modes", "streaming_json"],
})
json.dump(data, open(sys.argv[2], "w", encoding="utf-8"), indent=2)
PY
python3 "$SCRIPT" "$TMP/claude.json" --print-command >"$TMP/claude-command.json"
python3 - "$TMP/claude-command.json" <<'PY'
import json
import sys

argv = json.load(open(sys.argv[1], encoding="utf-8"))["argv"]
required = {"--bare", "--plugin-dir", "<ISOLATED_ENGINEER_PLUGIN>", "--print", "stream-json", "--no-session-persistence", "dontAsk", "--max-turns", "--max-budget-usd", "Bash", "WebFetch", "Agent", "Read(./**)"}
missing = required - set(argv)
assert not missing, missing
assert "--dangerously-skip-permissions" not in argv
assert not ({"Read", "Glob", "Grep"} & set(argv)), "broad read allow rule escaped into Claude argv"
PY

mutate() {
  local name="$1"
  local expression="$2"
  python3 - "$SAMPLE" "$TMP/$name.json" "$expression" <<'PY'
import json
import sys

source, target, expression = sys.argv[1:]
data = json.load(open(source, encoding="utf-8"))
exec(expression, {"data": data})
json.dump(data, open(target, "w", encoding="utf-8"), indent=2)
PY
  if python3 "$SCRIPT" "$TMP/$name.json" --print-command >/dev/null 2>&1; then
    echo "expected rejection: $name" >&2
    exit 1
  fi
}

mutate leaked_expected 'data["scenario"]["expected_output"] = "secret golden"'
mutate source_hash_mismatch 'data["scenario"]["source_sha256"] = "0" * 64'
mutate missing_scenario 'data["scenario"]["id"] = 99999'
mutate exposed_expectations 'data["scenario"]["expectations_exposed"] = True'
mutate path_traversal 'data["workspace"] = "../outside"'
mutate missing_marker 'data["fixture_marker"] = "missing-marker"'
mutate output_escape 'data["output_dir"] = "tmp/capture"'
mutate network_enabled 'data["permissions"]["network"] = "allow"'
mutate external_writes 'data["permissions"]["external_writes"] = True'
mutate codex_write 'data["permissions"]["sandbox"] = "workspace_write"'
mutate wrong_invocation 'data["scenario"]["invocation"] = "/engineer"'
mutate implicit_with_invocation 'data["scenario"]["activation_mode"]="implicit"'
mutate implicit_named_prompt 'data["scenario"]["activation_mode"]="implicit"; data["scenario"]["invocation"]=None'
mutate missing_activation_probe 'data["scenario"].pop("activation_probe")'
mutate forged_probe_request 'data["scenario"]["activation_probe"]["request"]="[show-the-answer]"'
mutate forged_probe_response 'data["scenario"]["activation_probe"]["response_sha256"]="0"*64'
mutate cached_credentials 'data["authentication"]["cached_credentials_allowed"] = True'
mutate keyring_enabled 'data["authentication"]["keyring_allowed"] = True'
mutate real_home 'data["authentication"]["isolated_home"] = False'
mutate wrong_auth_env 'data["authentication"]["api_key_env"] = "ANTHROPIC_API_KEY"'
mutate missing_read_tool 'data["host"]="claude"; data["scenario"]["invocation"]="/engineer-eval:engineer"; data["permissions"]["allowed_tools"]=["Read","Glob"]; data["host_inventory"].update(host="claude",executable_sha256="f"*64,version_output_sha256="1"*64,help_output_sha256="2"*64,required_capabilities=["bare_mode","no_persistence","non_interactive","permission_modes","streaming_json"])'
mutate bundle_hash_mismatch 'data["skill_bundle"]["sha256"] = "0" * 64'
mutate exposed_bundle_expectations 'data["skill_bundle"]["expectations_excluded"] = False'
mutate bundle_policy_expansion 'data["skill_bundle"]["include"].append("evals")'
mutate bundle_version_drift 'data["skill_bundle"]["version"] = "999.0.0"'
mutate inventory_hash_mismatch 'data["host_inventory"]["sha256"] = "0" * 64'
mutate inventory_host_mismatch 'data["host_inventory"]["host"] = "claude"'
mutate binary_hash_mismatch 'data["host_inventory"]["executable_sha256"] = "0" * 64'
mutate help_hash_mismatch 'data["host_inventory"]["help_output_sha256"] = "0" * 64'
mutate invented_required_capability 'data["host_inventory"]["required_capabilities"].append("root_everything")'
mutate duplicate_required_capability 'data["host_inventory"]["required_capabilities"].append("sandbox")'
mutate omitted_required_capability 'data["host_inventory"]["required_capabilities"].remove("strict_config")'

if python3 "$SCRIPT" "$SAMPLE" --execute --acknowledge-cost >/dev/null 2>&1; then
  echo "illustrative fixture unexpectedly executed" >&2
  exit 1
fi
if python3 "$SCRIPT" "$SAMPLE" --execute >/dev/null 2>&1; then
  echo "execution without cost acknowledgment unexpectedly accepted" >&2
  exit 1
fi

python3 - "$SCRIPT" "$ROOT" "$SAMPLE" <<'PY'
import importlib.util,os,pathlib,sys,tempfile
sys.dont_write_bytecode=True
path,root,sample=sys.argv[1:]; spec=importlib.util.spec_from_file_location('capture',path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory() as home:
 os.environ['CODEX_API_KEY']='synthetic-not-a-real-key'; os.environ['ANTHROPIC_API_KEY']='synthetic-not-a-real-key'; os.environ['UNRELATED_SECRET']='must-not-pass'; os.environ['CODEX_HOME']='/real/codex/home'
 codex=mod.sanitized_environment('codex',pathlib.Path(home)); claude=mod.sanitized_environment('claude',pathlib.Path(home))
 assert codex['HOME']==home and codex['CODEX_HOME'].startswith(home) and 'CODEX_API_KEY' in codex
 assert claude['HOME']==home and claude['CLAUDE_CONFIG_DIR'].startswith(home) and 'ANTHROPIC_API_KEY' in claude
 assert 'UNRELATED_SECRET' not in codex and 'UNRELATED_SECRET' not in claude
 assert codex['CODEX_HOME']!='/real/codex/home' and 'ANTHROPIC_API_KEY' not in codex and 'CODEX_API_KEY' not in claude
 data=__import__('json').load(open(sample)); root_path=pathlib.Path(root)
 mod.prepare_runtime_bundle(data,root_path,pathlib.Path(home))
 skill=pathlib.Path(home)/'.codex/skills/engineer'
 assert (skill/'SKILL.md').is_file() and not (skill/'evals').exists() and not (skill/'research').exists()
 data['host']='claude'; plugin=mod.prepare_runtime_bundle(data,root_path,pathlib.Path(home)/'claude-home')
 assert (plugin/'.claude-plugin/plugin.json').is_file() and (plugin/'skills/engineer/SKILL.md').is_file()
 assert mod.activation_failure_reason('skill not found: engineer')=='skill not found'
 assert mod.activation_failure_reason('engineer routing completed') is None
 assert mod.activation_probe_confirmed('result\nENGINEER_ROUTING_ACTIVE_v1\n')
 assert not mod.activation_probe_confirmed('result only')
 assert not mod.activation_probe_confirmed('ENGINEER_ROUTING_ACTIVE_v1\nENGINEER_ROUTING_ACTIVE_v1')
 try: mod.copy_skill_bundle(root_path,pathlib.Path(home)/'.codex/skills/engineer',data['skill_bundle']['sha256'])
 except ValueError as exc: assert 'target must be empty' in str(exc)
 else: raise AssertionError('non-empty bundle target accepted')
PY

# A captured inventory can be checked against the live binary without a model call.
python3 "$ROOT/scripts/capture-host-capabilities.py" --cwd "$ROOT" --output "$ROOT_TMP/live.json"
if ! python3 - "$ROOT_TMP/live.json" <<'PY'
import json,sys
inventory=json.load(open(sys.argv[1]))
raise SystemExit(0 if any(host.get('id')=='codex' and host.get('installed') is True for host in inventory['hosts']) else 1)
PY
then
  echo "codex live host re-probe skipped: executable not installed"
  echo "skill eval capture fixtures passed"
  exit 0
fi
python3 - "$SAMPLE" "$ROOT_TMP/live.json" "$ROOT_TMP/job.json" "$ROOT" <<'PY'
import hashlib,json,os,sys
sample,inventory_path,out,root=sys.argv[1:]
d=json.load(open(sample)); inv=json.load(open(inventory_path)); host=next(h for h in inv['hosts'] if h['id']=='codex')
rel=os.path.relpath(inventory_path,root)
d['run_kind']='captured_run'
d['host_inventory']={
 'path':rel,'sha256':hashlib.sha256(open(inventory_path,'rb').read()).hexdigest(),'host':'codex',
 'executable_sha256':host['executable_sha256'],'version_output_sha256':host['version_output_sha256'],
 'help_output_sha256':host['help_output_sha256'],'required_capabilities':['approvals','non_interactive','sandbox','strict_config']}
json.dump(d,open(out,'w'),indent=2)
PY
python3 "$SCRIPT" "$ROOT_TMP/job.json" --verify-live-host >/dev/null

# A structurally valid but forged/stale reviewed inventory must fail the live re-probe.
python3 - "$ROOT_TMP/live.json" "$ROOT_TMP/stale.json" "$ROOT_TMP/job.json" "$ROOT_TMP/stale-job.json" "$ROOT" <<'PY'
import hashlib,json,os,sys
live,stale,job_path,out,root=sys.argv[1:]
inv=json.load(open(live)); host=next(h for h in inv['hosts'] if h['id']=='codex'); host['executable_sha256']='0'*64
json.dump(inv,open(stale,'w'),indent=2)
d=json.load(open(job_path)); d['host_inventory']['path']=os.path.relpath(stale,root)
d['host_inventory']['sha256']=hashlib.sha256(open(stale,'rb').read()).hexdigest(); d['host_inventory']['executable_sha256']='0'*64
json.dump(d,open(out,'w'),indent=2)
PY
if python3 "$SCRIPT" "$ROOT_TMP/stale-job.json" --verify-live-host >/dev/null 2>&1; then
  echo "stale host binding unexpectedly passed live re-probe" >&2
  exit 1
fi

echo "skill eval capture fixtures passed"
