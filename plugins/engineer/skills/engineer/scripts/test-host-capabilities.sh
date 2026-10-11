#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-host-capabilities.py"
SAMPLE="$ROOT/templates/agentic/host-capabilities.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$VALIDATOR" "$SAMPLE" >/dev/null
python3 - "$ROOT" <<'PY'
import importlib.util, pathlib, sys
root=pathlib.Path(sys.argv[1])
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
capture=load("host_capture",root/"scripts/capture-host-capabilities.py")
validator=load("host_validator",root/"scripts/validate-host-capabilities.py")
for host, spec in capture.HOSTS.items():
    assert set(spec["tokens"]) == validator.CAPABILITIES[host]
required={
    "codex":{"code_review","plugins","app_server","remote_control","remote_client","session_fork","local_provider","hooks","plugin_marketplace","feature_toggles","exec_server","profile_as_file"},
    "claude":{"safe_mode","remote_control","cloud_review","fallback_model","effort_control","cost_budget","strict_mcp","tmux"},
    "grok":{"permission_modes","best_of_n","inspect_receipt","plugin_marketplace","claude_compat","session_fork","approval_bypass","structured_output"},
    "hermes":{"fallback_chain","credential_pools","kanban","checkpoints","bundles","curator","toolsets","acp"},
}
for host, expected in required.items(): assert expected <= validator.CAPABILITIES[host]
PY
python3 "$ROOT/scripts/capture-host-capabilities.py" --cwd "$ROOT" --output "$TMP/captured.json"
python3 "$VALIDATOR" "$TMP/captured.json" >/dev/null
if grep -Fq "$HOME" "$TMP/captured.json"; then
  echo "host capability receipt leaked an absolute home path" >&2
  exit 1
fi

mutate() {
  local name="$1" expression="$2"
  python3 - "$SAMPLE" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected host capability rejection: $name" >&2
    exit 1
  fi
}

mutate unknown_capability 'd["hosts"][0]["capabilities"].append("root_everything")'
mutate duplicate_host 'd["hosts"][1]["id"]="codex"; d["hosts"][1]["executable_name"]="codex"'
mutate unsafe_context 'd["context_files"][0]["path"]="../../.env"'
mutate missing_limitation 'd["limitations"].pop()'
mutate absent_with_hash 'd["hosts"][2]["executable_sha256"]="a"*64'
mutate fake_authorization 'd["decision"]["outcome"]="authorized"'
mutate raw_signal_value 'd["runtime_signals"]["codex_thread"]="secret-session-id"'
mutate missing_probe_hash 'd["hosts"][0]["help_output_sha256"]=None'
echo "host capability fixtures passed"
