#!/usr/bin/env bash
# engineer policy scanner — run from repo root
# Usage: engineer-scan.sh [--strict] [--design] [--backend] [--python] [--rust] [--fix-hints] [--json] [--quiet]
set -euo pipefail

STRICT=0
DESIGN=0
BACKEND=0
PYTHON=0
RUST=0
HINTS=0
JSON_OUT=0
QUIET=0
FAILURES=0
WARNINGS=0
SCAN_START=$(date +%s 2>/dev/null || echo 0)

for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    --design) DESIGN=1 ;;
    --backend) BACKEND=1 ;;
    --python) PYTHON=1 ;;
    --rust) RUST=1 ;;
    --fix-hints) HINTS=1 ;;
    --json) JSON_OUT=1 ;;
    --quiet) QUIET=1 ;;
    -h|--help)
      echo "Usage: engineer-scan.sh [--strict] [--design] [--backend] [--python] [--rust] [--fix-hints] [--json] [--quiet]"
      exit 0
      ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# Default: run design + backend baseline unless flags specified
if [[ "$DESIGN" -eq 0 && "$BACKEND" -eq 0 && "$PYTHON" -eq 0 && "$RUST" -eq 0 ]]; then
  DESIGN=1
  BACKEND=1
fi

# Auto-enable Python checks when a Python project is present
if [[ "$PYTHON" -eq 0 ]] && { [[ -f pyproject.toml ]] || [[ -f uv.lock ]] || compgen -G 'services/**/*.py' >/dev/null 2>&1; }; then
  PYTHON=1
fi

# Auto-enable Rust checks when a crate or Cargo workspace is present
if [[ "$RUST" -eq 0 ]] && { [[ -f Cargo.toml ]] || compgen -G 'crates/*/Cargo.toml' >/dev/null 2>&1 || compgen -G 'services/*/Cargo.toml' >/dev/null 2>&1; }; then
  RUST=1
fi

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
NC='\033[0m'

fail() {
  FAILURES=$((FAILURES + 1))
  if [[ "$JSON_OUT" -eq 1 ]]; then
    printf '{"severity":"error","message":%s}\n' "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")"
  elif [[ "$QUIET" -eq 0 ]]; then
    echo -e "${RED}FAIL${NC} $1"
  fi
}

pass() {
  if [[ "$JSON_OUT" -eq 0 && "$QUIET" -eq 0 ]]; then
    echo -e "${GRN}PASS${NC} $1"
  fi
}

warn() {
  WARNINGS=$((WARNINGS + 1))
  if [[ "$JSON_OUT" -eq 1 ]]; then
    printf '{"severity":"warn","message":%s}\n' "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")"
  elif [[ "$QUIET" -eq 0 ]]; then
    echo -e "${YLW}WARN${NC} $1"
  fi
}

hint() {
  if [[ "$HINTS" -eq 1 && "$JSON_OUT" -eq 0 ]]; then
    echo "       → $1"
  fi
}

has_rg() {
  [[ "${ENGINEER_FORCE_GREP:-0}" != "1" ]] && command -v rg >/dev/null 2>&1
}

# A private marker carries read/search failures out of command substitutions.
SCAN_TMP="$(mktemp -d)"
trap 'rm -rf "$SCAN_TMP"' EXIT

grep_rg() {
  local status=0
  if has_rg; then
    rg -n "$@" || status=$?
  else
    local -a options=(-n -r -E)
    local -a filters=()
    local -a paths=()
    local pattern="" glob=""
    while [[ "${1:-}" == "-i" || "${1:-}" == "-l" ]]; do
      options+=("$1")
      shift
    done
    pattern="${1:-}"
    [[ $# -gt 0 ]] && shift
    while [[ $# -gt 0 ]]; do
      if [[ "$1" == "--glob" && $# -ge 2 ]]; then
        glob="$2"
        shift 2
        if [[ "$glob" == !* ]]; then
          glob="${glob#!}"
          if [[ "${glob: -3}" == "/**" ]]; then
            glob="${glob%/**}"
            filters+=("--exclude-dir=${glob##*/}")
          else
            filters+=("--exclude=${glob##*/}")
          fi
        else
          # grep has no brace globs; expand the controlled suffix alternatives.
          if [[ "$glob" == *'{'*','*'}'* ]]; then
            local prefix="${glob%%\{*}" suffix="${glob#*\}}"
            local choices="${glob#*\{}" choice
            choices="${choices%%\}*}"
            local -a alternatives=()
            IFS=',' read -r -a alternatives <<< "$choices"
            for choice in "${alternatives[@]}"; do
              local expanded="${prefix}${choice}${suffix}"
              filters+=("--include=${expanded##*/}")
            done
          else
            filters+=("--include=${glob##*/}")
          fi
        fi
      else
        paths+=("$1")
        shift
      fi
    done
    [[ "${#paths[@]}" -gt 0 ]] || paths=(.)
    grep "${options[@]}" "${filters[@]}" -- "$pattern" "${paths[@]}" || status=$?
  fi
  if [[ "$status" -gt 1 ]]; then
    printf 'Search backend failed (exit %s)\n' "$status" >> "$SCAN_TMP/errors"
    return "$status"
  fi
  return 0
}

# JSON mode has one machine-readable stdout value; diagnostics go to stderr.
if [[ "$JSON_OUT" -eq 1 ]]; then
  exec 3>&1
  exec 1>&2
fi

if [[ "$JSON_OUT" -eq 0 && "$QUIET" -eq 0 ]]; then
  echo "engineer scan — $(pwd)"
  echo "---"
fi

# ─── Secrets & keys (always) — code only, not markdown docs ────────────────

SECRET_HITS=$(grep_rg -i \
  'SUPABASE_SERVICE_ROLE|service_role_key|sk_live_|sk_test_|STRIPE_SECRET' \
  --glob '!*.md' --glob '!engineer-scan.sh' --glob '!.env.example' \
  --glob '!node_modules/**' --glob '!.git/**' --glob '!research/**' \
  --glob '!docs/**' --glob '!**/CHANGELOG.md' \
  . | grep -v 'process\.env' | grep -v 'Deno\.env' || true)

if [[ -n "$SECRET_HITS" ]]; then
  fail "Possible secret literal in tracked files"
  echo "$SECRET_HITS" | sed -n '1,20p'
  hint "Use env vars only; add gitleaks in CI"
else
  pass "No obvious secret literals"
fi

PUBLIC_SERVICE=$(grep_rg 'NEXT_PUBLIC_.*(SERVICE|SECRET|ROLE)' \
  --glob '!node_modules/**' --glob '!.git/**' --glob '!research/**' \
  --glob '!scripts/engineer-scan.sh' --glob '!references/**' . || true)
if [[ -n "$PUBLIC_SERVICE" ]]; then
  fail "NEXT_PUBLIC_* exposes server secret pattern"
  echo "$PUBLIC_SERVICE" | sed -n '1,10p'
else
  pass "No NEXT_PUBLIC server-secret env names"
fi

# ─── Design ─────────────────────────────────────────────────────────────────

if [[ "$DESIGN" -eq 1 ]]; then
  echo ""
  echo "[design]"

  HARD_COLORS=$(grep_rg \
    'text-(red|blue|green|gray|grey|slate|zinc|neutral|stone|orange|yellow|purple|pink|indigo|cyan|emerald|lime|amber|violet|fuchsia|rose|sky|teal)-[0-9]{2,3}' \
    --glob '*.tsx' --glob '*.jsx' \
    --glob '!node_modules/**' \
    . || true)
  HARD_COLORS+=$(echo; grep_rg \
    'bg-(red|blue|green|gray|grey|slate|zinc|neutral|stone|orange|yellow|purple|pink|indigo|cyan|emerald|lime|amber|violet|fuchsia|rose|sky|teal)-[0-9]{2,3}' \
    --glob '*.tsx' --glob '*.jsx' \
    --glob '!node_modules/**' \
    --glob '!components/ui/**' \
    . || true)

  if [[ -n "$(echo "$HARD_COLORS" | tr -d '[:space:]')" ]]; then
    fail "Hardcoded Tailwind palette colors (use semantic tokens)"
    echo "$HARD_COLORS" | sed -n '1,15p'
    hint "Replace with text-foreground, bg-muted, text-destructive, etc."
  else
    pass "No hardcoded Tailwind palette in app components"
  fi

  UI_EDITS=$(git diff --name-only HEAD 2>/dev/null | grep 'components/ui/' || true)
  if [[ -n "$UI_EDITS" ]]; then
    warn "Modified shadcn components/ui/ files (prefer wrappers)"
    echo "$UI_EDITS"
  fi

  TASTE=$(grep_rg 'bg-gradient-to-|bg-linear-to-|from-indigo-|from-violet-|from-purple-|to-cyan-|bg-clip-text|shadow-indigo-|shadow-violet-|shadow-purple-|shadow-\[0_0_' \
    --glob '*.tsx' --glob '*.jsx' \
    --glob '!node_modules/**' \
    --glob '!components/ui/**' \
    . || true)
  # Krebs: 3–4px colored top/left card stripe. 2px is a divider/tab, not the tell.
  STRIPE=$(grep_rg 'border-l-[34]|border-l-4|border-t-[34]|border-t-4' \
    --glob '*.tsx' --glob '*.jsx' \
    --glob '!node_modules/**' \
    --glob '!components/ui/**' \
    . || true)
  # Krebs numbered 1-2-3 / design-taste 01 02 03 kickers. Zero-padded only — bare
  # <span>1</span> is a real list item, not the tell.
  STEPS=$(grep_rg '>0[1-3]</|>0[1-3] |\{"0[1-3]"\}|\{'\''0[1-3]'\''\}' \
    --glob '*.tsx' --glob '*.jsx' \
    --glob '!node_modules/**' \
    --glob '!components/ui/**' \
    . || true)
  # Krebs: Inter as the whole type system (next/font import or literal family).
  INTER=$(grep_rg 'import \{ Inter|Inter\(\{|font-\['\''Inter'\''\]|font-\["Inter"\]' \
    --glob '*.tsx' --glob '*.jsx' --glob '*.ts' \
    --glob '!node_modules/**' \
    --glob '!components/ui/**' \
    . || true)
  # Krebs badge-above-H1: pill then <h1>, or the stock "Now in Beta" copy.
  BADGE_COPY=$(grep_rg 'Now in [Bb]eta' \
    --glob '*.tsx' --glob '*.jsx' \
    --glob '!node_modules/**' \
    --glob '!components/ui/**' \
    . || true)
  BADGE_LAYOUT=$(python3 - <<'PY'
from pathlib import Path
import re
pat = re.compile(r"rounded-full[\s\S]{0,240}?</(?:span|p|div|a)>\s*<h1\b", re.I)
skip = {"node_modules", ".git", ".next", "dist", "build", "coverage", "ui"}
hits = []
for p in Path(".").rglob("*"):
    if p.suffix not in {".tsx", ".jsx"} or any(part in skip for part in p.parts):
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        continue
    if pat.search(text):
        hits.append(str(p))
print("\n".join(hits))
PY
)
  if [[ -n "$(echo "$TASTE$STRIPE$STEPS$INTER$BADGE_COPY$BADGE_LAYOUT" | tr -d '[:space:]')" ]]; then
    if [[ "$STRICT" -eq 1 ]]; then
      fail "AI-default visual tells (gradient/indigo/glow, 3–4px card stripe, 01–03 kickers, Inter, or badge-above-H1)"
    else
      warn "AI-default visual tells (gradient/indigo/glow, 3–4px card stripe, 01–03 kickers, Inter, or badge-above-H1) — design-taste.md"
    fi
    echo "$TASTE" | sed -n '1,8p'
    echo "$STRIPE" | sed -n '1,8p'
    echo "$STEPS" | sed -n '1,8p'
    echo "$INTER" | sed -n '1,8p'
    echo "$BADGE_COPY" | sed -n '1,8p'
    echo "$BADGE_LAYOUT" | sed -n '1,8p'
    hint "Replace with semantic tokens and a named type system; Inter-everywhere, 3–4px card stripes, glows, 01/02/03 kickers, and badge-above-H1 are 2026 AI tells"
  else
    pass "No common AI-default gradient/indigo/glow/stripe/kicker/Inter/badge classnames"
  fi
fi

# ─── Backend ────────────────────────────────────────────────────────────────

if [[ "$BACKEND" -eq 1 ]]; then
  echo ""
  echo "[backend]"

  GETSESSION=$(grep_rg 'getSession\(\)' \
    --glob '*.ts' --glob '*.tsx' \
    --glob '!node_modules/**' \
    --glob '!**/client.ts' \
    . || true)
  if [[ -n "$GETSESSION" ]]; then
    warn "getSession() found in server-side code — prefer getUser()"
    echo "$GETSESSION" | sed -n '1,10p'
    hint "getSession() alone is not valid for server auth decisions"
  else
    pass "No getSession() in server files"
  fi

  UPDATE_TAG_ROUTES=$(grep_rg 'updateTag\(' \
    --glob '**/route.ts' --glob '**/route.tsx' \
    . || true)
  if [[ -n "$UPDATE_TAG_ROUTES" ]]; then
    fail "updateTag() in Route Handler — use revalidateTag instead"
    echo "$UPDATE_TAG_ROUTES"
  else
    pass "No updateTag() in route handlers"
  fi

  WEBHOOK_JSON=$(grep_rg 'req\.json\(\)' \
    --glob '**/webhooks/**/route.ts' \
    . || true)
  if [[ -n "$WEBHOOK_JSON" ]]; then
    warn "req.json() in webhook route — use req.text() for signature verify first"
    echo "$WEBHOOK_JSON" | sed -n '1,5p'
  fi

  # Rate-limit / abuse surface (backend always; escalates under --strict)
  # Sensitive mutations should call a limiter (Upstash, arcjet, custom) or mark exempt.
  RL_RE='rateLimit|Ratelimit|ratelimit|limiter\.limit|arcjet|fixedWindow|slidingWindow|isRateLimited|rate_limit|checkRateLimit'
  SENSITIVE_RE='deleteAccount|exportUser|exportData|signIn|signUp|password|checkout|createCheckout|forgotPassword|resetPassword|sendEmail|sendMagic|webhook'
  RL_MISSING=0
  RL_CHECKED=0
  if has_rg; then
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      [[ "$f" == *node_modules* ]] && continue
      if grep -q 'engineer:ratelimit-exempt' "$f" 2>/dev/null; then
        continue
      fi
      # Sensitive name or mutating DB/API surface in Server Action / route
      if ! rg -q "$SENSITIVE_RE" "$f" 2>/dev/null; then
        if ! rg -q '\.(insert|update|delete|upsert)\(' "$f" 2>/dev/null; then
          continue
        fi
      fi
      RL_CHECKED=$((RL_CHECKED + 1))
      if ! rg -q "$RL_RE" "$f" 2>/dev/null; then
        RL_MISSING=$((RL_MISSING + 1))
        if [[ "$STRICT" -eq 1 ]]; then
          fail "rate-limit missing: $f (sensitive mutation / Server Action)"
          hint "Add limiter call or // engineer:ratelimit-exempt with justification"
        else
          warn "rate-limit missing: $f (add limiter or engineer:ratelimit-exempt)"
        fi
      fi
    done < <(
      {
        rg -l '"use server"' --glob '*.ts' --glob '*.tsx' --glob '!node_modules/**' . 2>/dev/null || true
        rg -l 'export async function (POST|PUT|PATCH|DELETE)' --glob '**/route.ts' --glob '**/route.tsx' --glob '!node_modules/**' . 2>/dev/null || true
      } | sort -u
    )
  fi
  if [[ "$RL_CHECKED" -eq 0 ]]; then
    pass "No sensitive Server Actions / mutation routes found for rate-limit scan"
  elif [[ "$RL_MISSING" -eq 0 ]]; then
    pass "Rate-limit present on scanned sensitive surfaces ($RL_CHECKED file(s))"
  else
    hint "See references/enforcement.md · rate-limit / abuse; package: @upstash/ratelimit or arcjet"
  fi

  # Public contact/subscribe forms without any rate defense (warn)
  CONTACT=$(grep_rg -l 'subscribe|contact|newsletter' \
    --glob '**/api/**/route.ts' --glob '**/api/**/route.tsx' \
    --glob '!node_modules/**' . 2>/dev/null || true)
  if [[ -n "$CONTACT" ]]; then
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      if grep -q 'engineer:ratelimit-exempt' "$f" 2>/dev/null; then continue; fi
      if ! rg -q "$RL_RE" "$f" 2>/dev/null; then
        warn "public form route may lack rate limit: $f"
      fi
    done <<< "$CONTACT"
  fi

  if [[ -f "scripts/check-rls-migration.sh" ]]; then
    bash scripts/check-rls-migration.sh && pass "RLS migration check" || fail "RLS migration check"
  elif [[ -d "supabase/migrations" ]]; then
    TABLES=$(grep_rg -i 'create table (public\.)?' supabase/migrations/ || true)
    if [[ -n "$TABLES" ]]; then
      warn "supabase/migrations exists but scripts/check-rls-migration.sh missing"
      hint "Copy from engineer/scripts/check-rls-migration.sh"
    fi
  fi
fi

# ─── Python (FastAPI / uv services) ─────────────────────────────────────────

if [[ "$PYTHON" -eq 1 ]]; then
  echo ""
  echo "[python]"

  if [[ -f pyproject.toml ]] || [[ -f uv.lock ]] || compgen -G '**/*.py' >/dev/null 2>&1; then
    if [[ -f pyproject.toml ]] && [[ ! -f uv.lock ]]; then
      fail "PY-LOCK: pyproject.toml without uv.lock (commit lockfile)"
      hint "uv lock && git add uv.lock — see references/python.md"
    elif [[ -f uv.lock ]]; then
      pass "uv.lock present"
    fi

    JOSE=$(grep_rg 'from jose|import jose|python-jose' \
      --glob '*.py' --glob '!**/.venv/**' --glob '!**/site-packages/**' . || true)
    if [[ -n "$JOSE" ]]; then
      fail "PY-JWT: python-jose usage — use PyJWT with algorithms="
      echo "$JOSE" | sed -n '1,10p'
    else
      pass "No python-jose import"
    fi

    ON_EVENT=$(grep_rg '@app\.on_event|on_event\([\"'\'']startup' \
      --glob '*.py' --glob '!**/.venv/**' . || true)
    if [[ -n "$ON_EVENT" ]]; then
      fail "PY-LIFESPAN: @app.on_event — use lifespan context manager"
      echo "$ON_EVENT" | sed -n '1,10p'
    else
      pass "No FastAPI on_event handlers"
    fi

    SA14=$(grep_rg 'session\.query\(' \
      --glob '*.py' --glob '!**/.venv/**' . || true)
    if [[ -n "$SA14" ]]; then
      fail "PY-SA14: session.query() — use SQLAlchemy 2.0 select()"
      echo "$SA14" | sed -n '1,10p'
    else
      pass "No session.query() (SQLAlchemy 1.4 style)"
    fi

    REQUESTS_ASYNC=$(grep_rg '^\s*import requests|^\s*from requests' \
      --glob '*.py' --glob '!**/.venv/**' . || true)
    if [[ -n "$REQUESTS_ASYNC" ]]; then
      warn "requests import found — prefer httpx.AsyncClient in async FastAPI routes"
      echo "$REQUESTS_ASYNC" | sed -n '1,8p'
      hint "See references/python.md HTTP clients"
    fi

    CORS_STAR=$(grep_rg 'allow_origins\s*=\s*\[\s*[\"'\'']\*[\"'\'']' \
      --glob '*.py' --glob '!**/.venv/**' . || true)
    if [[ -n "$CORS_STAR" ]]; then
      warn "CORS allow_origins=['*'] — forbidden with allow_credentials=True"
      echo "$CORS_STAR" | sed -n '1,5p'
    fi
  else
    pass "Python scan enabled but no Python project files found"
  fi
fi

# ─── Rust (crates / Cargo workspaces) ───────────────────────────────────────

if [[ "$RUST" -eq 1 ]]; then
  echo ""
  echo "[rust]"

  RS_MANIFESTS=$(find . -name Cargo.toml -not -path '*/target/*' -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null | sort || true)
  if [[ -n "$RS_MANIFESTS" ]]; then
    RS_LINTS=0
    while IFS= read -r m; do
      [[ -z "$m" ]] && continue
      if grep -Eq '^[[:space:]]*\[(workspace\.)?lints' "$m" 2>/dev/null; then
        RS_LINTS=1
      fi
    done <<< "$RS_MANIFESTS"
    if [[ "$RS_LINTS" -eq 1 ]]; then
      pass "Cargo [lints] table present"
    else
      warn "RS-LINTS: no [lints] table in any Cargo.toml — clippy policy is unenforced"
      hint "Paste templates/rust/lints.toml into Cargo.toml and copy templates/rust/clippy.toml beside it (references/rust-systems.md)"
    fi

    RS_DENY=$(grep_rg '#!\[deny\(warnings\)\]' --glob '*.rs' --glob '!**/target/**' . || true)
    if [[ -n "$RS_DENY" ]]; then
      fail "RS-DENY-WARNINGS: #![deny(warnings)] in source — a new toolchain breaks the build; pass -D warnings to clippy in CI instead"
      echo "$RS_DENY" | sed -n '1,10p'
    else
      pass "No #![deny(warnings)] in source"
    fi

    # Non-test code only: skip tests/, benches/, examples/, build.rs, comment lines, and
    # everything from a `#[cfg(test)] mod` to the end of the file.
    : > "$SCAN_TMP/rs-unwrap"
    : > "$SCAN_TMP/rs-unsafe"
    : > "$SCAN_TMP/rs-leftover"
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      case "$f" in
        */tests/*|*/benches/*|*/examples/*|*/build.rs) continue ;;
      esac
      awk -v file="$f" -v out="$SCAN_TMP" '
        pending && /^[[:space:]]*(pub(\([a-z]+\))?[[:space:]]+)?mod[[:space:]]/ { exit }
        { pending = 0 }
        /^[[:space:]]*#\[cfg\(test\)\]/ { pending = 1; next }
        /^[[:space:]]*\/\// { p3 = p2; p2 = p1; p1 = $0; next }
        /\.unwrap\(\)/ { printf "%s:%d: %s\n", file, NR, $0 >> (out "/rs-unwrap") }
        /(^|[^A-Za-z0-9_])(dbg|todo|unimplemented)!\(/ { printf "%s:%d: %s\n", file, NR, $0 >> (out "/rs-leftover") }
        $0 !~ /SAFETY:/ && /(^|[^A-Za-z0-9_])unsafe[[:space:]]*(\{|impl[[:space:]<])/ {
          if ((p1 p2 p3) !~ /SAFETY:/) printf "%s:%d: %s\n", file, NR, $0 >> (out "/rs-unsafe")
        }
        { p3 = p2; p2 = p1; p1 = $0 }
      ' "$f"
    done < <(find . -name '*.rs' -not -path '*/target/*' -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null | sort || true)

    RS_CLEAN=1
    for check in unwrap unsafe leftover; do
      case "$check" in
        unwrap) RS_ID="RS-UNWRAP"; RS_MSG='.unwrap() outside tests — use ? or expect("why this cannot fail")' ;;
        unsafe) RS_ID="RS-UNSAFE-SAFETY"; RS_MSG="unsafe block or impl without a // SAFETY: comment above it" ;;
        *) RS_ID="RS-DEBUG-LEFTOVER"; RS_MSG="dbg!/todo!/unimplemented! outside tests" ;;
      esac
      if [[ -s "$SCAN_TMP/rs-$check" ]]; then
        RS_CLEAN=0
        if [[ "$STRICT" -eq 1 ]]; then
          fail "$RS_ID: $RS_MSG"
        else
          warn "$RS_ID: $RS_MSG"
        fi
        sed -n '1,10p' "$SCAN_TMP/rs-$check"
        hint "references/rust-systems.md (Enforcement); templates/rust/lints.toml makes clippy enforce this"
      fi
    done
    if [[ "$RS_CLEAN" -eq 1 ]]; then
      pass "No unwrap, undocumented unsafe, or debug leftovers outside tests"
    fi
  else
    pass "Rust scan enabled but no Cargo.toml found"
  fi
fi

# ─── Strict ─────────────────────────────────────────────────────────────────

if [[ "$STRICT" -eq 1 ]]; then
  echo ""
  echo "[strict]"

  CLIENT_LAYOUTS=$(grep_rg '"use client"' \
    --glob '**/layout.tsx' \
    --glob '!node_modules/**' \
    . || true)
  if [[ -n "$CLIENT_LAYOUTS" ]]; then
    fail "'use client' on layout.tsx — push boundary down"
    echo "$CLIENT_LAYOUTS"
  else
    pass "No 'use client' on layouts"
  fi

  if has_rg; then
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      if grep -q 'engineer:auth-exempt' "$f" 2>/dev/null; then continue; fi
      if rg -q '\.(from|insert|update|delete|upsert)\(' "$f" 2>/dev/null; then
        if ! rg -q 'getUser\(\)|getCurrentUser' "$f" 2>/dev/null; then
          fail "$f mutates data without getUser()"
        fi
      fi
    done < <(rg -l '"use server"' --glob '*.ts' --glob '*.tsx' . 2>/dev/null || true)
  fi

  LOCALSTORAGE_JWT=$(grep_rg 'localStorage.*(token|jwt|session)' \
    --glob '*.{ts,tsx}' --glob '!node_modules/**' . || true)
  if [[ -n "$LOCALSTORAGE_JWT" ]]; then
    fail "JWT/session in localStorage — use cookie SSR flow"
    echo "$LOCALSTORAGE_JWT" | sed -n '1,5p'
  else
    pass "No localStorage JWT pattern"
  fi
fi

SCAN_END=$(date +%s 2>/dev/null || echo 0)
DURATION=$((SCAN_END - SCAN_START))
if [[ "$DURATION" -lt 0 ]]; then DURATION=0; fi

if [[ -s "$SCAN_TMP/errors" ]]; then
  fail "Search backend failed; scan coverage is incomplete"
  cat "$SCAN_TMP/errors" >&2
fi

if [[ "$JSON_OUT" -eq 1 ]]; then
  printf '{"ok":%s,"failures":%s,"warnings":%s,"duration_s":%s}\n' \
    "$([[ $FAILURES -eq 0 ]] && echo true || echo false)" \
    "$FAILURES" "$WARNINGS" "$DURATION" >&3
  [[ "$FAILURES" -eq 0 ]] && exit 0 || exit 1
fi

if [[ "$QUIET" -eq 0 ]]; then
  echo ""
  echo "---"
  echo "duration ${DURATION}s · warnings ${WARNINGS}"
fi
if [[ "$FAILURES" -gt 0 ]]; then
  [[ "$QUIET" -eq 0 ]] && echo -e "${RED}$FAILURES check(s) failed${NC}"
  exit 1
fi
[[ "$QUIET" -eq 0 ]] && echo -e "${GRN}All engineer scans passed${NC}"
exit 0
