#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-skill-admission.py"
SAMPLE="$ROOT/templates/agentic/skill-admission.sample.json"
TMP="$(mktemp -d)"
# Standalone clean-checkout runs must not depend on prior suites.
mkdir -p "$ROOT/.engineer"
REPO_TMP="$(mktemp -d "$ROOT/.engineer/skill-admission-test.XXXXXX")"
trap 'rm -rf "$TMP" "$REPO_TMP"' EXIT
cd "$ROOT"

python3 "$VALIDATOR" "$SAMPLE" >/dev/null
python3 - "$SAMPLE" "$TMP/captured-trust.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
data["receipt_kind"] = "captured_review"
data["decision"].update({
    "status": "trust",
    "reasons": ["Complete captured review for the declared read-only capability."],
    "unresolved_risks": [],
})
json.dump(data, open(sys.argv[2], "w", encoding="utf-8"), indent=2)
PY
python3 "$VALIDATOR" "$TMP/captured-trust.json" >/dev/null
BASE="$TMP/captured-trust.json"

mutate() {
  local name="$1"
  local expression="$2"
  python3 - "$BASE" "$TMP/$name.json" "$expression" <<'PY'
import json
import sys

source, target, expression = sys.argv[1:]
data = json.load(open(source, encoding="utf-8"))
exec(expression, {"data": data})
json.dump(data, open(target, "w", encoding="utf-8"), indent=2)
PY
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected rejection: $name" >&2
    exit 1
  fi
}

mutate file_hash 'data["files"][0]["sha256"] = "0" * 64'
mutate tree_hash 'data["candidate"]["tree_sha256"] = "0" * 64'
mutate missing_inventory 'data["files"] = data["files"][:1]'
mutate mutable_source 'data["candidate"]["source"]["commit_sha"] = "main"'
mutate shadow_capability 'data["capabilities"]["observed"].append("read_secrets")'
mutate dangerous_trust 'data["permissions"]["requested"].append("shell"); data["permissions"]["dangerous"].append("shell")'
mutate unreviewed_code 'data["analysis"]["code_review"] = False'
mutate no_adversarial 'data["sandbox"]["cases"] = data["sandbox"]["cases"][:1]'
mutate observed_exfiltration 'data["sandbox"]["cases"][1]["exfiltration_observed"] = True'
mutate self_review 'data["review"]["independent_reviewer"] = data["candidate"]["author_identity"]'
mutate unresolved_trust 'data["decision"]["unresolved_risks"] = ["unknown endpoint"]'
mutate illustrative_trust 'data["receipt_kind"] = "illustrative_fixture"'
mutate floating_dependency 'data["dependencies"] = [{"ecosystem":"npm","name":"example","version":"latest","integrity":"sha256:" + "0" * 64,"provenance_reviewed":True,"lifecycle_scripts":[]}]'

python3 - "$BASE" "$TMP/valid-reject.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
data["permissions"]["requested"].append("shell")
data["permissions"]["dangerous"].append("shell")
data["decision"].update({
    "status": "reject",
    "reasons": ["The candidate requests unrestricted shell access."],
    "accepted_risks": [],
    "unresolved_risks": ["Shell behavior exceeds the advertised read-only capability."],
})
json.dump(data, open(sys.argv[2], "w", encoding="utf-8"), indent=2)
PY
python3 "$VALIDATOR" "$TMP/valid-reject.json" >/dev/null

cp -R templates/fixtures/skill-candidate "$REPO_TMP/candidate"
ln -s /tmp "$REPO_TMP/candidate/escape"
python3 - "$BASE" "$TMP/symlink.json" "$REPO_TMP" <<'PY'
import json
import pathlib
import sys

sys.path.insert(0, "scripts")
from evidence_path import relative_posix

data = json.load(open(sys.argv[1], encoding="utf-8"))
data["candidate"]["local_path"] = relative_posix(pathlib.Path(sys.argv[3], "candidate"), pathlib.Path.cwd())
json.dump(data, open(sys.argv[2], "w", encoding="utf-8"), indent=2)
PY
if python3 "$VALIDATOR" "$TMP/symlink.json" >/dev/null 2>&1; then
  echo "expected rejection: symlink" >&2
  exit 1
fi

echo "skill admission fixtures passed"
