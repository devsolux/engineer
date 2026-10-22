#!/usr/bin/env bash
# Validate engineer repo integrity (modules, commands, evals, path hygiene).
# Usage: bash scripts/validate-repo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FAILURES=0
VER=""
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }

echo "engineer validate — $ROOT"
echo "---"

# ─── SKILL.md frontmatter ───────────────────────────────────────────────────
if [[ -f SKILL.md ]] && grep -q '^name: engineer' SKILL.md && grep -q '^  version: "[0-9]' SKILL.md; then
  VER=$(sed -n 's/^  version: "\([^"]*\)"$/\1/p' SKILL.md | head -1)
  pass "SKILL.md frontmatter (v${VER})"
else
  fail "SKILL.md missing name/version frontmatter"
fi

FRONTMATTER_KEYS=$(awk 'NR==1 && $0=="---" {inside=1; next} inside && $0=="---" {exit} inside && /^[a-z][a-z0-9-]*:/ {sub(/:.*/, ""); print}' SKILL.md | sort -u)
UNEXPECTED_FRONTMATTER=$(comm -23 <(printf '%s\n' "$FRONTMATTER_KEYS") <(printf '%s\n' allowed-tools compatibility description license metadata name | sort) || true)
if [[ -z "$UNEXPECTED_FRONTMATTER" ]]; then
  pass "Skill frontmatter uses host-supported keys"
else
  fail "Unsupported SKILL.md frontmatter keys: $(echo "$UNEXPECTED_FRONTMATTER" | tr '\n' ' ')"
fi

# Skill discovery metadata must stay within host limits and UI metadata must remain usable.
DESCRIPTION_LENGTH=$(python3 - <<'PY'
from pathlib import Path
import re
text = Path("SKILL.md").read_text(encoding="utf-8")
match = re.search(
    r"^description: >-\n(.*?)(?=^(?:metadata|license|compatibility|allowed-tools):)",
    text,
    re.MULTILINE | re.DOTALL,
)
print(len(" ".join(line.strip() for line in match.group(1).splitlines())) if match else -1)
PY
)
if [[ "$DESCRIPTION_LENGTH" -ge 1 && "$DESCRIPTION_LENGTH" -le 1024 ]]; then
  pass "Skill trigger description length (${DESCRIPTION_LENGTH}/1024 chars)"
else
  fail "Skill trigger description must be 1-1024 chars (found ${DESCRIPTION_LENGTH})"
fi

if [[ -f agents/openai.yaml ]] \
  && grep -q '^  display_name: "engineer"$' agents/openai.yaml \
  && grep -q '\$engineer' agents/openai.yaml \
  && grep -q '^policy:$' agents/openai.yaml \
  && grep -q '^  allow_implicit_invocation: true$' agents/openai.yaml; then
  SHORT_LENGTH=$(sed -n 's/^  short_description: "\(.*\)"$/\1/p' agents/openai.yaml | awk '{ print length }')
  if [[ "$SHORT_LENGTH" -ge 25 && "$SHORT_LENGTH" -le 64 ]]; then
    pass "OpenAI skill interface metadata"
  else
    fail "agents/openai.yaml short_description must be 25-64 chars"
  fi
else
  fail "agents/openai.yaml missing interface metadata or explicit implicit-invocation policy"
fi

DESCRIPTION_PREFIX=$(python3 - <<'PY'
from pathlib import Path
import re
text = Path("SKILL.md").read_text(encoding="utf-8")
match = re.search(
    r"^description: >-\n(.*?)(?=^(?:metadata|license|compatibility|allowed-tools):)",
    text,
    re.MULTILINE | re.DOTALL,
)
print(" ".join(line.strip() for line in match.group(1).splitlines())[:240].lower() if match else "")
PY
)
if [[ "$DESCRIPTION_PREFIX" == *"automatically activates"* ]] && [[ "$DESCRIPTION_PREFIX" == *"software"* ]]; then
  pass "Implicit-routing intent is front-loaded before description truncation"
else
  fail "Skill description must front-load automatic software/product routing intent"
fi

# ─── References resolve from SKILL.md ───────────────────────────────────────
MISSING=0
while IFS= read -r ref; do
  if [[ ! -f "references/$ref" ]]; then
    echo "    missing references/$ref"
    MISSING=$((MISSING + 1))
  fi
done < <(grep -oE 'references/[a-z0-9-]+\.md' SKILL.md | sed 's|references/||' | sort -u)

if [[ "$MISSING" -eq 0 ]]; then
  pass "All SKILL.md reference paths resolve"
else
  fail "$MISSING SKILL.md reference path(s) missing"
fi

# ─── MANIFEST vs files ──────────────────────────────────────────────────────
REF_COUNT=$(find references -name '*.md' ! -name 'MANIFEST.md' | wc -l | tr -d ' ')
pass "Reference modules: $REF_COUNT (+ MANIFEST)"

# ─── Commands ───────────────────────────────────────────────────────────────
CMD_COUNT=$(find commands -name 'engineer*.md' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$CMD_COUNT" -ge 20 ]]; then
  pass "Slash commands: $CMD_COUNT"
else
  fail "Expected ≥20 slash commands, found $CMD_COUNT"
fi

# Command → reference paths
CMD_MISS=0
for f in commands/*.md; do
  while IFS= read -r ref; do
    if [[ ! -f "references/$ref" ]]; then
      echo "    $f → missing references/$ref"
      CMD_MISS=$((CMD_MISS + 1))
    fi
  done < <(grep -oE 'references/[a-z0-9-]+\.md' "$f" 2>/dev/null | sed 's|references/||' | sort -u || true)
done
if [[ "$CMD_MISS" -eq 0 ]]; then
  pass "Command reference paths resolve"
else
  fail "$CMD_MISS command reference path(s) missing"
fi

# Every documented engineer command must have a command file, and vice versa.
DOC_COMMANDS=$(grep -rhoE '`/engineer-[a-z0-9-]+`' SKILL.md docs/ references/workflows.md 2>/dev/null \
  | tr -d '`/' | sort -u || true)
CMD_STEMS=$(find commands -name 'engineer-*.md' -exec basename {} .md \; | sort -u)
DOC_ONLY=$(comm -23 <(printf '%s\n' "$DOC_COMMANDS") <(printf '%s\n' "$CMD_STEMS") || true)
CMD_ONLY=$(comm -13 <(printf '%s\n' "$DOC_COMMANDS") <(printf '%s\n' "$CMD_STEMS") || true)
if [[ -z "$DOC_ONLY" && -z "$CMD_ONLY" ]]; then
  pass "Slash command files and documentation are synchronized"
else
  [[ -n "$DOC_ONLY" ]] && echo "    documented but missing file: $(echo "$DOC_ONLY" | tr '\n' ' ')"
  [[ -n "$CMD_ONLY" ]] && echo "    command file missing from docs: $(echo "$CMD_ONLY" | tr '\n' ' ')"
  fail "Slash command documentation drift"
fi

# Manifest reference entries must resolve. This catches catalog drift that SKILL.md cannot see.
MANIFEST_MISS=0
while IFS= read -r ref; do
  [[ -z "$ref" || "$ref" == "MANIFEST.md" ]] && continue
  if [[ ! -f "references/$ref" ]]; then
    echo "    MANIFEST → missing references/$ref"
    MANIFEST_MISS=$((MANIFEST_MISS + 1))
  fi
done < <(grep -oE '`[a-z0-9-]+\.md`' references/MANIFEST.md | tr -d '`' | sort -u)
if [[ "$MANIFEST_MISS" -eq 0 ]]; then
  pass "MANIFEST reference entries resolve"
else
  fail "$MANIFEST_MISS MANIFEST reference entry(s) missing"
fi

# Published version headers must match the skill frontmatter.
VERSION_MISS=0
for f in docs/README.md docs/modules.md; do
  if ! grep -q "$VER" "$f"; then
    echo "    $f does not mention current version $VER"
    VERSION_MISS=$((VERSION_MISS + 1))
  fi
done
if [[ "$VERSION_MISS" -eq 0 ]]; then
  pass "Current version synchronized in human docs"
else
  fail "$VERSION_MISS version synchronization issue(s)"
fi

# Progressive disclosure guard: the router must stay compact.
SKILL_LINES=$(wc -l < SKILL.md | tr -d ' ')
if [[ "$SKILL_LINES" -lt 500 ]]; then
  pass "SKILL.md progressive-disclosure limit (${SKILL_LINES}/499 lines)"
else
  fail "SKILL.md too large (${SKILL_LINES} lines; must stay below 500)"
fi

# ─── Anti-bloat: reference module size cap ──────────────────────────────────
# Explicit exceptions (each must justify itself; shrink, never grow):
#   deep-research.md — verbatim prompt templates + schemas the pipeline executes
#   python.md        — peer-language depth module covering a whole service stack
REF_SIZE_EXCEPTIONS="deep-research.md python.md"
REF_OVERSIZE=0
for f in references/*.md; do
  b=$(basename "$f")
  [[ "$b" == "MANIFEST.md" ]] && continue
  n=$(wc -l < "$f" | tr -d ' ')
  if [[ "$n" -gt 300 && " $REF_SIZE_EXCEPTIONS " != *" $b "* ]]; then
    echo "    $b has $n lines (max 300; split per enforcement.md precedent)"
    REF_OVERSIZE=$((REF_OVERSIZE + 1))
  fi
done
if [[ "$REF_OVERSIZE" -eq 0 ]]; then
  pass "Reference modules within 300-line budget (exceptions: $REF_SIZE_EXCEPTIONS)"
else
  fail "$REF_OVERSIZE reference module(s) over the 300-line budget"
fi

# ─── Anti-bloat: per-verb load budget (SKILL.md + Load-first modules) ───────
# Each verb's initial context load (SKILL.md body + its Load-first modules) must
# stay ≤800 lines. Excepted verbs carry an explicit ceiling: shrink, never grow.
if python3 - <<'PY'
import re, sys
from pathlib import Path

LIMIT = 800
# verb -> explicit ceiling for multi-module verbs (reduce over time)
EXCEPTIONS = {
    "design": 1150,        # design-system + a11y + patterns; motion is at-need
    "api": 850,            # backend-api + api-data-flows
    "browser": 850,        # browser-qa + browser-agent-security + frontend-testing
    "hermes": 950,         # hermes-agent-integration + coding-agent-hosts
    "ship": 900,           # deploy-ops + backend-security + infra-security
    "self-improve": 950,   # skill-authoring + refactoring + workflows
}

text = Path("SKILL.md").read_text(encoding="utf-8")
match = re.search(r"^## Verbs\n(.*?)^## ", text, re.M | re.S)
if match is None:
    print("    SKILL.md verb table not found")
    sys.exit(1)
skill_lines = len(text.splitlines())
refs = {p.stem for p in Path("references").glob("*.md")}
sizes = {p.stem: len(p.read_text(encoding="utf-8").splitlines()) for p in Path("references").glob("*.md")}
failures = 0
for row in match.group(1).splitlines():
    if not row.startswith("|") or row.startswith("|---") or "Invocation" in row:
        continue
    cols = [c.strip() for c in row.strip("|").split("|")]
    if len(cols) < 3:
        continue
    invocation, load = cols[0], cols[2]
    verb_match = re.search(r"engineer ([a-z][a-z0-9-]*)", invocation)
    verb = verb_match.group(1) if verb_match else invocation.strip("`")
    modules = set()
    for token in re.findall(r"[a-z][a-z0-9-]*(?:\.md)?\*?", load):
        base = token.removesuffix(".md")
        if base.endswith("*"):
            modules.update(p.stem for p in Path("references").glob(base.rstrip("*") + "*.md"))
        elif base in refs:
            modules.add(base)
    total = skill_lines + sum(sizes[m] for m in modules)
    ceiling = EXCEPTIONS.get(verb, LIMIT)
    if total > ceiling:
        print(f"    verb '{verb}' loads {total} lines (ceiling {ceiling}): {sorted(modules)}")
        failures += 1
sys.exit(1 if failures else 0)
PY
then
  pass "Per-verb load budgets within ceiling (800; explicit exceptions: design api browser hermes ship self-improve)"
else
  fail "Verb load budget exceeded"
fi

# ─── Last verified header on reference modules ──────────────────────────────
MISSING_VERIFIED=0
for f in references/*.md; do
  b=$(basename "$f")
  [[ "$b" == "MANIFEST.md" ]] && continue
  if ! awk 'NR<=12 && /Last verified/ { found=1 } END { exit found ? 0 : 1 }' "$f"; then
    echo "    references/$b missing Last verified in the first 12 lines"
    MISSING_VERIFIED=$((MISSING_VERIFIED + 1))
  fi
done
if [[ "$MISSING_VERIFIED" -eq 0 ]]; then
  pass "Reference modules carry Last verified dates"
else
  fail "$MISSING_VERIFIED reference module(s) missing Last verified"
fi
# Informational only: modules past their own review cadence. Re-verify or record them in the
# dated ledger (docs/releasing.md); never redate. `--fail-after-days N` makes this a gate.
CURRENCY=$(python3 scripts/report-module-currency.py --summary 2>/dev/null || echo "report unavailable")
echo "  ℹ Module review cadence: $CURRENCY (python3 scripts/report-module-currency.py)"

# ─── Operator/venture runbooks must not live in the public skill ───────────
OPERATOR_HITS=$(grep -R -n -E 'x_article_publish|nyk-article-gating|personal-brand/research/articles' \
  SKILL.md references commands 2>/dev/null || true)
if [[ -z "$OPERATOR_HITS" ]]; then
  pass "No operator X-article runbooks in the public skill surface"
else
  echo "$OPERATOR_HITS" | sed 's/^/    /'
  fail "Operator-specific publishing runbook leaked into SKILL.md/references/commands"
fi

# ─── Anti-bloat: every reference module must be registered in MANIFEST ──────
ORPHANS=0
for f in references/*.md; do
  b=$(basename "$f")
  [[ "$b" == "MANIFEST.md" ]] && continue
  if ! grep -q "\`$b\`" references/MANIFEST.md; then
    echo "    references/$b missing from MANIFEST.md"
    ORPHANS=$((ORPHANS + 1))
  fi
done
if [[ "$ORPHANS" -eq 0 ]]; then
  pass "No orphan reference modules (all registered in MANIFEST)"
else
  fail "$ORPHANS orphan reference module(s) not in MANIFEST.md"
fi

# ─── Path hygiene: no repo-escaping pointer paths in agent-loaded docs ──────
# Backticked or linked ../../ paths dead-end on every machine that installs only
# this skill. Vendor the synthesis into research/ or point at a local file.
ESCAPES=$(grep -REn '`\.\./\.\.|\]\(\.\./\.\.' references/ docs/ 2>/dev/null || true)
if [[ -z "$ESCAPES" ]]; then
  pass "No repo-escaping ../../ pointer paths in references/ or docs/"
else
  fail "Repo-escaping pointer path(s) found:"
  echo "$ESCAPES" | head -10
fi

# ─── Anti-bloat: TOC required for long reference modules ────────────────────
# Modules >150 lines need a Contents block (](# link) within the first 40 lines.
TOC_MISS=0
for f in references/*.md; do
  b=$(basename "$f")
  [[ "$b" == "MANIFEST.md" ]] && continue
  n=$(wc -l < "$f" | tr -d ' ')
  if [[ "$n" -gt 150 ]] && ! head -40 "$f" | grep -q '](#'; then
    echo "    $b ($n lines) missing a Contents block in the first 40 lines"
    TOC_MISS=$((TOC_MISS + 1))
  fi
done
if [[ "$TOC_MISS" -eq 0 ]]; then
  pass "Long reference modules carry a TOC"
else
  fail "$TOC_MISS long reference module(s) missing a TOC"
fi

# ─── Every script mentioned in SKILL.md must be catalogued in MANIFEST ──────
SCRIPT_MISS=0
while IFS= read -r s; do
  base=$(basename "$s")
  if [[ ! -f "$s" ]] || ! grep -q "$base" references/MANIFEST.md; then
    echo "    SKILL.md mentions $s but MANIFEST.md has no entry"
    SCRIPT_MISS=$((SCRIPT_MISS + 1))
  fi
done < <(grep -oE 'scripts/[A-Za-z0-9_.-]+\.(sh|py)' SKILL.md | sort -u)
if [[ "$SCRIPT_MISS" -eq 0 ]]; then
  pass "All SKILL.md script mentions are catalogued in MANIFEST"
else
  fail "$SCRIPT_MISS SKILL.md script mention(s) missing from MANIFEST.md"
fi

# ─── Evals ──────────────────────────────────────────────────────────────────
if command -v python3 >/dev/null 2>&1; then
  EVAL_N=$(python3 -c "import json; d=json.load(open('evals/evals.json')); print(len(d.get('evals',[])))")
  if [[ "$EVAL_N" -ge 20 ]]; then
    pass "Evals parse: $EVAL_N scenarios"
  else
    fail "Evals count low: $EVAL_N"
  fi

  # Skill-eval hash chain must be bound to the current SKILL.md / runtime — a
  # version bump or runtime edit that forgets the rebind is caught here, not in
  # a red engineer-health fixture after release.
  if [[ -f scripts/rebind-skill-eval.py ]]; then
    if python3 scripts/rebind-skill-eval.py --check >/dev/null 2>&1; then
      pass "Skill-eval hash chain bound to current runtime"
    else
      fail "Skill-eval hash chain drift — run: python3 scripts/rebind-skill-eval.py"
    fi
  fi

  # Offline trajectory fixture smoke (no model)
  if [[ -f scripts/check-trajectory-fixture.py && -f templates/fixtures/trajectory-fix-typecheck.json ]]; then
    TMP_TRACE="$(mktemp)"
    python3 -c 'import json,sys; json.dump([{"tool":"bash","name":"typecheck","ok":True,"exit":0},{"tool":"edit","name":"src/x.ts","ok":True},{"tool":"bash","name":"typecheck","ok":True,"exit":0}], open(sys.argv[1],"w"))' "$TMP_TRACE"
    if python3 scripts/check-trajectory-fixture.py \
      --fixture templates/fixtures/trajectory-fix-typecheck.json \
      --trace "$TMP_TRACE" >/dev/null; then
      pass "Trajectory fixture checker smoke"
    else
      fail "Trajectory fixture checker failed on golden trace"
    fi
    rm -f "$TMP_TRACE"
  fi
else
  fail "python3 required to parse evals"
fi

# ─── Scripts executable bits / shebang / pipefail ───────────────────────────
SCRIPT_HYGIENE_BEFORE=$FAILURES
for s in scripts/*.sh; do
  if head -1 "$s" | grep -q '#!/usr/bin/env bash'; then
    :
  else
    fail "$s missing bash shebang"
  fi
  if ! grep -q 'set -euo pipefail' "$s"; then
    fail "$s missing set -euo pipefail"
  fi
  # Direct invocation (./scripts/foo.sh) is the documented interface; CI's
  # `bash scripts/foo.sh` masks a missing exec bit, so enforce it here.
  if [ ! -x "$s" ]; then
    fail "$s missing executable bit (chmod +x)"
  fi
done
if [[ "$FAILURES" -eq "$SCRIPT_HYGIENE_BEFORE" ]]; then
  pass "Script shebangs + set -euo pipefail + executable bits OK"
fi

# ─── Shell assertions must stop the script under every bash ─────────────────
# Bash 3.2 (macOS) ignores a failing [[ ]] under set -e and no bash stops on `! cmd`,
# so a bare statement of either form is an assertion that silently never fails.
UNENFORCED="$(grep -nE '^[[:space:]]*(\[\[|![[:space:]])' scripts/*.sh 2>/dev/null | grep -vE '\|\||&&' || true)"
if [[ -n "$UNENFORCED" ]]; then
  while IFS= read -r hit; do
    fail "${hit%%:*} line $(printf '%s' "$hit" | cut -d: -f2): bare [[ ]] or ! statement is not enforced; end it with || fail or use if ...; then fail"
  done <<< "$UNENFORCED"
else
  pass "Shell assertions end in an explicit failure (bash 3.2-safe)"
fi

# Package fixture scripts must run in first-party CI, not only local health.
if [[ -f scripts/run-tests.py && -f Makefile && -f .github/workflows/validate.yml ]] \
  && grep -q 'make test' .github/workflows/validate.yml \
  && grep -q 'scripts/run-tests.py' Makefile \
  && python3 scripts/run-tests.py --list >/dev/null; then
  pass "All shell and Python fixtures are discovered through the CI Make target"
else
  fail "Offline test discovery is not wired through Makefile into CI"
fi

# Inventory executables (informational)
EXE_LIST=$(find scripts -type f \( -perm -111 -o -name '*.sh' \) 2>/dev/null | sort || true)
if [[ -n "$EXE_LIST" ]]; then
  pass "Script inventory: $(echo "$EXE_LIST" | wc -l | tr -d ' ') file(s)"
fi

# ─── Supply-chain hygiene (skill scripts must not network-fetch by default) ─
# First-party skill scripts should not curl|bash remote installers or fetch blobs.
SC_HITS=$(grep -REn 'curl\s+[^|]*\|\s*(ba)?sh|wget\s+[^|]*\|\s*(ba)?sh|curl\s+-fsSL|pip install|npm install -g|npx\s+[^ ]+@' \
  scripts/ 2>/dev/null \
  | grep -v 'validate-repo' \
  | grep -v '# supply-chain:allow' \
  || true)
if [[ -z "$SC_HITS" ]]; then
  pass "No remote-install / curl|bash patterns in scripts/"
else
  fail "Supply-chain risk pattern in scripts/ (add # supply-chain:allow if intentional):"
  echo "$SC_HITS" | head -15
fi

# Executable documentation and workflows get a syntax-aware supply-chain gate. This deliberately
# ignores defensive prose and scans only runnable Markdown fences plus active Action references.
if python3 scripts/scan-doc-supply-chain.py >/dev/null; then
  pass "Executable docs and workflow dependencies are immutable"
else
  fail "Executable documentation supply-chain scan failed"
  python3 scripts/scan-doc-supply-chain.py | head -20 || true
fi

# ─── Path hygiene (no personal absolute paths in published docs) ────────────
PATH_HITS=$(grep -REn --exclude='*.py[co]' --exclude-dir='__pycache__' '/Users/|/home/[a-z]+/dev' \
  README.md docs/ scripts/ commands/ SKILL.md CONTRIBUTING.md 2>/dev/null \
  | grep -v 'validate-repo' || true)
if [[ -z "$PATH_HITS" ]]; then
  pass "No machine-specific absolute paths in docs/scripts"
else
  fail "Hardcoded personal paths found:"
  echo "$PATH_HITS" | head -20
fi

# ─── Required OSS files ─────────────────────────────────────────────────────
for f in LICENSE CONTRIBUTING.md CHANGELOG.md assets/BRAND.md; do
  if [[ -f "$f" ]]; then
    pass "Present: $f"
  else
    fail "Missing: $f"
  fi
done

# ─── Brand assets ───────────────────────────────────────────────────────────
BRAND_MISS=0
for f in assets/logo.svg assets/wordmark.svg assets/header.svg assets/og.svg \
         assets/blueprint.svg assets/blueprint-verbs.svg \
         assets/blueprint-enforcement.svg; do
  if [[ ! -f "$f" ]]; then
    fail "Missing brand asset: $f"
    BRAND_MISS=$((BRAND_MISS + 1))
  fi
done
if [[ "$BRAND_MISS" -eq 0 ]]; then
  pass "Core brand assets present"
fi

echo "---"
if [[ "$FAILURES" -eq 0 ]]; then
  echo "OK — all checks passed"
  exit 0
else
  echo "FAILED — $FAILURES check(s)"
  exit 1
fi
