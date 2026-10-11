#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/references/oss-maintainer.md"
RECEIPT="$ROOT/templates/github/oss-maintainer-baseline.md"
APPLY="$ROOT/scripts/apply-oss-baseline.py"
VALIDATE_APPLY="$ROOT/scripts/validate-oss-application.py"

grep -q 'OSPS Baseline 2026.02.19' "$DOC"
grep -q 'Scorecard score are not outcome metrics' "$DOC"
grep -q 'protect `.github/` or `CODEOWNERS` itself' "$DOC"
grep -q 'pull_request_target' "$DOC"
grep -q 'Do not ask for exploit details in a public issue' "$DOC"
grep -q 'immutable GitHub releases' "$DOC"
grep -q 'Do not accept polished prose as proof' "$DOC"
grep -q 'Never auto-close a reproducible unanswered issue' "$DOC"
grep -q 'Evidence limitations:' "$RECEIPT"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
for file in README.md LICENSE CONTRIBUTING.md SECURITY.md; do printf 'fixture\n' >"$TMP/$file"; done
python3 "$ROOT/scripts/audit-oss-repo.py" "$TMP" --visibility public --profile experimental --strict --json >"$TMP/receipt.json"
python3 - "$TMP/receipt.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['decision']=='review_external_settings'; assert d['local_gaps']==[]
assert d['applicability']=='confirmed_public'; assert len(d['limitations'])==4
PY
rm "$TMP/SECURITY.md"
if python3 "$ROOT/scripts/audit-oss-repo.py" "$TMP" --visibility public --profile experimental --strict >/dev/null 2>&1; then
  echo "missing OSS baseline unexpectedly passed strict audit" >&2
  exit 1
fi
python3 "$ROOT/scripts/audit-oss-repo.py" "$TMP" --visibility private --profile critical --strict --json >"$TMP/private.json"
python3 - "$TMP/private.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['applicability']=='private_excluded'; assert d['decision']=='not_applicable_private'; assert d['local_gaps']==[]
PY

# Planning is read-only and unknown/private visibility fails closed.
PLAN="$TMP/plan-target"
mkdir -p "$PLAN/.github/workflows"
printf 'name: fixture\n' >"$PLAN/.github/workflows/ci.yml"
python3 "$APPLY" "$PLAN" --visibility public --json >"$TMP/plan.json"
python3 - "$TMP/plan.json" "$PLAN" <<'PY'
import json, pathlib, sys
d=json.load(open(sys.argv[1])); root=pathlib.Path(sys.argv[2])
assert d['mode']=='plan' and all(x['status']=='planned_create' for x in d['operations'])
assert not (root/'CONTRIBUTING.md').exists()
assert '.github/dependabot.yml' in {x['path'] for x in d['operations']}
assert d['external_mutations']==[] and len(d['limitations'])==5
PY
python3 "$VALIDATE_APPLY" "$TMP/plan.json" --root "$PLAN" >/dev/null
python3 "$APPLY" "$PLAN" --visibility public --output receipts/plan.json >/dev/null
python3 "$VALIDATE_APPLY" "$PLAN/receipts/plan.json" --root "$PLAN" >/dev/null
if python3 "$APPLY" "$PLAN" --visibility public --output receipts/plan.json >/dev/null 2>&1; then
  echo "OSS receipt output overwrote an existing file" >&2
  exit 1
fi
for visibility in unknown private; do
  if python3 "$APPLY" "$PLAN" --visibility "$visibility" --apply >/dev/null 2>&1; then
    echo "OSS baseline application accepted $visibility visibility" >&2
    exit 1
  fi
done

# Apply creates only missing deterministic files and is idempotent.
python3 "$APPLY" "$PLAN" --visibility public --apply --json >"$TMP/applied.json"
python3 "$VALIDATE_APPLY" "$TMP/applied.json" --root "$PLAN" >/dev/null
ln -s "$TMP/applied.json" "$TMP/applied-link.json"
if python3 "$VALIDATE_APPLY" "$TMP/applied-link.json" --root "$PLAN" >/dev/null 2>&1; then
  echo "symlinked OSS application receipt unexpectedly validated" >&2
  exit 1
fi
python3 - "$TMP/applied.json" "$PLAN" <<'PY'
import json, pathlib, sys
d=json.load(open(sys.argv[1])); root=pathlib.Path(sys.argv[2])
assert all(x['status']=='present_canonical' for x in d['operations'])
for item in d['operations']:
    assert (root/item['path']).is_file()
assert {x['path'] for x in d['project_decisions_required']} >= {'README.md','LICENSE','SECURITY.md','CODE_OF_CONDUCT.md','SUPPORT.md'}
PY
python3 "$APPLY" "$PLAN" --visibility public --apply --json >"$TMP/idempotent.json"
python3 "$VALIDATE_APPLY" "$TMP/idempotent.json" --root "$PLAN" >/dev/null
python3 - "$TMP/idempotent.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert all(x['status']=='present_canonical' for x in d['operations'])
PY

# Existing project content and symlink targets are never overwritten.
CONFLICT="$TMP/conflict-target"
mkdir -p "$CONFLICT/.github/ISSUE_TEMPLATE"
printf 'project-owned\n' >"$CONFLICT/CONTRIBUTING.md"
ln -s "$TMP" "$CONFLICT/.github/ISSUE_TEMPLATE/bug.yml"
if python3 "$APPLY" "$CONFLICT" --visibility public --apply --json >"$TMP/conflict.json"; then
  echo "OSS baseline conflicts unexpectedly passed" >&2
  exit 1
fi
grep -q '^project-owned$' "$CONFLICT/CONTRIBUTING.md"
python3 - "$TMP/conflict.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); states={x['path']:x['status'] for x in d['operations']}
assert states['CONTRIBUTING.md']=='existing_conflict'
assert states['.github/ISSUE_TEMPLATE/bug.yml']=='blocked_symlink'
assert d['decision']=='review_conflicts'
PY
python3 "$VALIDATE_APPLY" "$TMP/conflict.json" --root "$CONFLICT" >/dev/null

# Hash, path, state, mode, decision, and authority claims are replayed, not trusted.
mutate_receipt() {
  local name="$1" expression="$2"
  python3 - "$TMP/applied.json" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'))
PY
  if python3 "$VALIDATE_APPLY" "$TMP/$name.json" --root "$PLAN" >/dev/null 2>&1; then
    echo "forged OSS application receipt unexpectedly passed: $name" >&2
    exit 1
  fi
}
mutate_receipt template_hash 'd["operations"][0]["template_sha256"]="0"*64'
mutate_receipt observed_hash 'd["operations"][0]["observed_sha256"]="0"*64'
mutate_receipt path_escape 'd["operations"][0]["path"]="../outside"'
mutate_receipt path_type 'd["operations"][0]["path"]=42'
mutate_receipt missing_operation 'd["operations"].pop()'
mutate_receipt external_mutation 'd["external_mutations"]=["ruleset changed"]'
mutate_receipt decisions 'd["project_decisions_required"]=[]'
mutate_receipt decision 'd["decision"]="review_external_settings"'
mutate_receipt false_apply 'd["mode"]="apply"; d["operations"][0]["status"]="planned_create"'
mutate_receipt mode_type 'd["mode"]=[]'

if python3 "$APPLY" "$PLAN" --visibility public --output ../outside.json >/dev/null 2>&1; then
  echo "OSS receipt output escaped the target" >&2
  exit 1
fi
ln -s "$TMP" "$PLAN/receipt-link"
if python3 "$APPLY" "$PLAN" --visibility public --output receipt-link/receipt.json >/dev/null 2>&1; then
  echo "OSS receipt output traversed a symlink" >&2
  exit 1
fi

cp "$PLAN/CONTRIBUTING.md" "$TMP/contributing.saved"
printf 'drift\n' >"$PLAN/CONTRIBUTING.md"
if python3 "$VALIDATE_APPLY" "$TMP/applied.json" --root "$PLAN" >/dev/null 2>&1; then
  echo "post-application target drift unexpectedly passed receipt replay" >&2
  exit 1
fi
cp "$TMP/contributing.saved" "$PLAN/CONTRIBUTING.md"

# Dependabot policy follows supported manifests, combines monorepo directories,
# prefers uv over pip in the same directory, and ignores symlinked manifests.
DEPS="$TMP/dependency-target"
mkdir -p "$DEPS/.github/workflows" "$DEPS/apps/web" "$DEPS/services/api" "$DEPS/crates/core"
printf 'name: ci\n' >"$DEPS/.github/workflows/ci.yml"
printf '{}\n' >"$DEPS/package.json"
printf '{}\n' >"$DEPS/apps/web/package.json"
printf 'version = 1\n' >"$DEPS/services/api/uv.lock"
printf '[project]\n' >"$DEPS/services/api/pyproject.toml"
printf '[package]\nname = "core"\n' >"$DEPS/crates/core/Cargo.toml"
ln -s "$DEPS/package.json" "$DEPS/services/api/package.json"
python3 "$APPLY" "$DEPS" --visibility public --apply --json >"$TMP/dependencies.json"
python3 "$VALIDATE_APPLY" "$TMP/dependencies.json" --root "$DEPS" >/dev/null
python3 - "$DEPS/.github/dependabot.yml" <<'PY'
from pathlib import Path
import sys
body=Path(sys.argv[1]).read_text()
assert 'package-ecosystem: "github-actions"' in body
assert 'package-ecosystem: "npm"' in body
assert 'directories:\n      - "/"\n      - "/apps/web"' in body
assert 'package-ecosystem: "uv"' in body and 'package-ecosystem: "pip"' not in body
assert 'package-ecosystem: "cargo"' in body
assert body.count('/services/api') == 1  # symlinked package.json was ignored
PY

# A manifest change changes canonical generated policy and invalidates old evidence.
printf 'module fixture\n' >"$DEPS/go.mod"
if python3 "$VALIDATE_APPLY" "$TMP/dependencies.json" --root "$DEPS" >/dev/null 2>&1; then
  echo "dependency-manifest drift unexpectedly passed receipt replay" >&2
  exit 1
fi

# Existing alternate Dependabot spelling or Renovate policy blocks a competing updater.
POLICY="$TMP/policy-target"
mkdir -p "$POLICY/.github"
printf '{}\n' >"$POLICY/package.json"
printf 'version: 2\nupdates: []\n' >"$POLICY/.github/dependabot.yaml"
python3 "$APPLY" "$POLICY" --visibility public --apply --json >"$TMP/policy.json"
python3 - "$TMP/policy.json" "$POLICY" <<'PY'
import json,pathlib,sys
d=json.load(open(sys.argv[1])); root=pathlib.Path(sys.argv[2])
assert not (root/'.github/dependabot.yml').exists()
assert any(x['path']=='.github/dependabot.yaml' for x in d['project_decisions_required'])
PY
python3 "$VALIDATE_APPLY" "$TMP/policy.json" --root "$POLICY" >/dev/null

# Safely identifiable official ecosystems are covered; overlapping .tf ownership is disclosed.
MORE="$TMP/more-ecosystems"
for pair in \
  'pre/.pre-commit-config.yaml' 'rust/rust-toolchain.toml' 'nix/flake.lock' \
  'vcpkg/vcpkg.json' 'julia/Project.toml' 'sbt/build.sbt' 'swift/Package.swift' \
  'helm/Chart.yaml' 'submodules/.gitmodules' 'bazel/MODULE.bazel' 'conda/environment.yml' \
  'elm/elm.json' 'dotnet/global.json' 'tofu/main.tofu' 'terraform/.terraform.lock.hcl'; do
  mkdir -p "$MORE/${pair%/*}"
  printf 'fixture\n' >"$MORE/$pair"
done
printf 'fixture\n' >"$MORE/nix/flake.nix"
printf 'fixture\n' >"$MORE/terraform/main.tf"
mkdir -p "$MORE/ambiguous"; printf 'fixture\n' >"$MORE/ambiguous/main.tf"
mkdir -p "$MORE/orphan-nix" "$MORE/orphan-julia" "$MORE/nuget-only"
printf 'fixture\n' >"$MORE/orphan-nix/flake.lock"
printf 'fixture\n' >"$MORE/orphan-julia/Manifest.toml"
printf 'fixture\n' >"$MORE/nuget-only/app.csproj"
python3 "$APPLY" "$MORE" --visibility public --apply --json >"$TMP/more.json"
python3 "$VALIDATE_APPLY" "$TMP/more.json" --root "$MORE" >/dev/null
python3 - "$TMP/more.json" "$MORE/.github/dependabot.yml" <<'PY'
import json,pathlib,sys
d=json.load(open(sys.argv[1])); body=pathlib.Path(sys.argv[2]).read_text()
expected={'pre-commit','rust-toolchain','nix','vcpkg','julia','sbt','swift','helm','gitsubmodule','bazel','conda','elm','dotnet-sdk','opentofu','terraform'}
assert all(f'package-ecosystem: "{name}"' in body for name in expected)
assert any('ambiguous Terraform/OpenTofu' in x and '/ambiguous' in x for x in d['limitations'])
assert '/ambiguous' not in body
assert '/orphan-nix' not in body and '/orphan-julia' not in body
assert body.count('/nuget-only') == 1 and 'package-ecosystem: "nuget"' in body
PY

# Traversal is bounded and reports the boundary instead of claiming complete discovery.
DEEP="$TMP/deep-target/a/b/c/d/e"
mkdir -p "$DEEP"
printf '{}\n' >"$DEEP/package.json"
python3 "$APPLY" "$TMP/deep-target" --visibility public --json >"$TMP/deep.json"
python3 - "$TMP/deep.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert any('dependency scan stopped' in x for x in d['limitations'])
assert '.github/dependabot.yml' not in {x['path'] for x in d['operations']}
PY

MANY="$TMP/many-target"
for i in $(seq 1 129); do mkdir -p "$MANY/pkg-$i"; printf '{}\n' >"$MANY/pkg-$i/package.json"; done
python3 "$APPLY" "$MANY" --visibility public --json >"$TMP/many.json"
python3 - "$TMP/many.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert any('capped at 128' in x for x in d['limitations'])
PY

echo "oss maintainer fixtures passed"
