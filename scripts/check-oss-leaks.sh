#!/usr/bin/env bash
# check-oss-leaks.sh — private-context leak gate for public-repo changesets.
#
# Blocks internal, private, or sensitive content from entering an OSS repo:
# secrets/credentials, personal filesystem paths, infrastructure internals,
# personal data, and user-specific private markers (names the operator listed
# in a LOCAL config file that never ships with this repository).
#
# Usage (run from the target repo root):
#   check-oss-leaks.sh                      # scan the staged changeset (default)
#   check-oss-leaks.sh --all                # scan every tracked file
#   check-oss-leaks.sh --ref main..HEAD     # scan files changed in a commit range
#   check-oss-leaks.sh --allow '<ere>'      # exception pattern (repeatable)
#   check-oss-leaks.sh --warn-only          # MAJOR findings report without failing
#                                           # (CRITICAL always fails)
#   check-oss-leaks.sh --public-only        # exit 0 without scanning when the repo
#                                           # is not known to be public
#   check-oss-leaks.sh --markers <file>     # marker file override
#   check-oss-leaks.sh --gitleaks           # optional accelerator when installed
#   check-oss-leaks.sh --notes              # informational notes (never fail)
#
# Marker layer: $ENGINEER_PRIVATE_MARKERS, else ~/.config/engineer/private-markers.txt
# (XDG_CONFIG_HOME respected). Sections: [names] [business] [paths] scanned as
# fixed strings; [public] lists repos known public (visibility fallback).
# A missing marker file downgrades to the generic layer with one warning.
#
# Finding classes: SECRET, DROPPER, WORM, INVISIBLE_UNICODE (CRITICAL) · PATH,
# INFRA, PERSONAL, MARKER (MAJOR). WORM catches the committed-config-file JS worm
# (payload appended to a build/CSS config such as postcss.config.mjs or
# tailwind.config.js): a global['x']='N-dddd' campaign-tag assignment, a 200+
# space/tab run hiding code on one source line, or a javascript-obfuscator
# scaffold (`function _0x...(){var _0x...=[` or 5+ distinct `_0x...` identifiers)
# in a config/build file. DROPPER catches obfuscated code-execution shapes from
# poisoned starter templates: an ENCODER/deobfuscation stage (base64, hex,
# String.fromCharCode, \x/\u escape runs, reversed/custom-alphabet, XOR) feeding a
# dynamic-execution SINK (eval / new Function / vm.* / dynamic import / child_process
# / Python exec/compile/__import__ / PowerShell IEX/-EncodedCommand), fetch-then-exec
# line shapes, decode-of-env/argv reaching an exec sink, and base64 blobs under
# env-var keys in committed env files. INVISIBLE_UNICODE flags zero-width, bidi,
# PUA, tag, and supplementary variation-selector codepoints (the GlassWorm class)
# that hide executable text from human review and token scanners.
#
# KNOWN TIER-1 LIMITATION (deliberate, not a bug — see references/malware-detection.md):
# this is a SAME-FILE regex gate. The anchor incident's real payload was CROSS-FILE —
# a base64 URL parked in a committed .env under an env-var key, decoded and exec'd by
# a separate vite/vitest config. A single-file pattern cannot bridge that split, and
# this gate does NOT fake cross-file detection with a brittle heuristic. ENVB64 still
# flags the .env carrier in isolation; closing the config<->.env gap needs Tier-2
# AST/dataflow taint (decode-source -> exec-sink across files; Semgrep/CodeQL), named
# as the future closure in malware-detection.md and enforcement.md.
#
# Prioritized always-read surfaces (skim-not-read is where droppers hide): build/test
# config (vite/vitest/webpack/rollup/next), test setup, .husky/* + .git/hooks/*,
# package.json scripts, .github/workflows/*, .vscode/*, .devcontainer, .cursor/rules,
# AGENTS*, .mcp.json. CI action-pinning + pull_request_target checks live in
# scripts/scan-doc-supply-chain.py; this gate scans content shapes.
# Exit: 1 when CRITICAL > 0, or MAJOR > 0 without --warn-only; else 0.
set -euo pipefail

MODE=staged
REF=""
WARN_ONLY=0
PUBLIC_ONLY=0
USE_GITLEAKS=0
NOTES=0
QUIET=0
MARKER_FILE="${ENGINEER_PRIVATE_MARKERS:-${XDG_CONFIG_HOME:-$HOME/.config}/engineer/private-markers.txt}"
ALLOW_PATTERNS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) MODE=all ;;
    --ref)
      [[ $# -ge 2 ]] || { echo "--ref requires a range" >&2; exit 2; }
      MODE=ref; REF="$2"; shift ;;
    --allow)
      [[ $# -ge 2 ]] || { echo "--allow requires a pattern" >&2; exit 2; }
      ALLOW_PATTERNS+=("$2"); shift ;;
    --warn-only) WARN_ONLY=1 ;;
    --public-only) PUBLIC_ONLY=1 ;;
    --markers)
      [[ $# -ge 2 ]] || { echo "--markers requires a path" >&2; exit 2; }
      MARKER_FILE="$2"; shift ;;
    --gitleaks) USE_GITLEAKS=1 ;;
    --notes) NOTES=1 ;;
    --quiet) QUIET=1 ;;
    -h|--help) sed -n '2,52p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repository" >&2; exit 2; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/check-oss-leaks.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
: >"$TMP/SECRET"; : >"$TMP/DROPPER"; : >"$TMP/WORM"; : >"$TMP/INVISIBLE_UNICODE"; : >"$TMP/PATH"; : >"$TMP/INFRA"; : >"$TMP/PERSONAL"; : >"$TMP/MARKER"; : >"$TMP/NOTE"

HAVE_PY=0
if command -v python3 >/dev/null 2>&1; then
  HAVE_PY=1
else
  echo "WARN python3 not found — INVISIBLE_UNICODE class skipped (all other classes run)" >&2
fi

say() { [[ "$QUIET" -eq 0 ]] && echo "$@" || true; }

# Invisible/obfuscating-unicode scanner (GlassWorm class). Prints line:col:U+XXXX
# for each dangerous codepoint. Kept as a small python3 helper for correct UTF-8
# codepoint handling; grep byte-classes are not portable across BSD/GNU.
scan_invisible() { # $1 = content file
  python3 - "$1" <<'PY' 2>/dev/null || true
import sys
path = sys.argv[1]
def bad(cp):
    return (0x200b <= cp <= 0x200d or cp in (0x2060, 0xFEFF)
            or 0x202a <= cp <= 0x202e or 0x2066 <= cp <= 0x2069
            or 0xe0100 <= cp <= 0xe01ef or 0xe0000 <= cp <= 0xe007f
            or 0xe000 <= cp <= 0xf8ff)
try:
    text = open(path, encoding="utf-8", errors="strict").read()
except (OSError, UnicodeDecodeError):
    sys.exit(0)
for lineno, line in enumerate(text.splitlines(), 1):
    for col, ch in enumerate(line, 1):
        cp = ord(ch)
        if bad(cp):
            print(f"{lineno}:col{col}:U+{cp:04X} hidden/bidi/PUA codepoint in source")
PY
}

# ─── Marker layer (local config; never committed to this repository) ────────
MARKERS_ON=0
declare -a M_NAMES=() M_BUSINESS=() M_PATHS=() PUBLIC_REPOS=()
if [[ -f "$MARKER_FILE" ]]; then
  MARKERS_ON=1
  section=names
  while IFS= read -r raw; do
    line="${raw%%#*}"
    line="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [[ -z "$line" ]] && continue
    case "$line" in
      "[names]") section=names; continue ;;
      "[business]") section=business; continue ;;
      "[paths]") section=paths; continue ;;
      "[public]") section=public; continue ;;
      \[*\]) echo "WARN unknown marker section: $line" >&2; section=skip; continue ;;
    esac
    case "$section" in
      names) M_NAMES+=("$line") ;;
      business) M_BUSINESS+=("$line") ;;
      paths) M_PATHS+=("$line") ;;
      public) PUBLIC_REPOS+=("$line") ;;
      skip) ;;
    esac
  done <"$MARKER_FILE"
else
  echo "WARN marker layer off: no marker file at $MARKER_FILE (generic layer still runs)" >&2
fi

# The marker file maps the operator's private names; keep it private too.
if [[ "$MARKERS_ON" -eq 1 ]]; then
  MPERM="$(stat -f '%Lp' "$MARKER_FILE" 2>/dev/null || stat -c '%a' "$MARKER_FILE" 2>/dev/null || echo '')"
  if [[ -n "$MPERM" && "${MPERM: -2}" != "00" ]]; then
    echo "WARN marker file is group/world-readable (mode $MPERM) — run: chmod 600 $MARKER_FILE" >&2
  fi
fi

# ─── Public-repo detection (--public-only) ──────────────────────────────────
repo_name() {
  local url
  url="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -n "$url" ]]; then
    url="${url%.git}"; echo "${url##*/}"
  else
    basename "$(git rev-parse --show-toplevel)"
  fi
}
if [[ "$PUBLIC_ONLY" -eq 1 ]]; then
  NAME="$(repo_name)"
  VIS="unknown"
  if command -v gh >/dev/null 2>&1; then
    VIS="$(gh repo view --json visibility --jq .visibility 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo unknown)"
  fi
  if [[ "$VIS" != "public" ]]; then
    for r in ${PUBLIC_REPOS[@]+"${PUBLIC_REPOS[@]}"}; do
      [[ "$r" == "$NAME" ]] && VIS=public
    done
  fi
  if [[ "$VIS" != "public" ]]; then
    say "SKIP --public-only: repository '$NAME' is not known public (gh: unavailable or non-public; not in [public] markers)"
    exit 0
  fi
fi

# ─── File list per scope ────────────────────────────────────────────────────
case "$MODE" in
  staged) git diff --cached --name-only --diff-filter=ACMR >"$TMP/files" ;;
  all) git ls-files >"$TMP/files" ;;
  ref) git diff --name-only --diff-filter=ACMR "$REF" >"$TMP/files" ;;
esac

# The gate's own pattern definitions and fixtures would self-match.
SELF_SKIP='(^|/)scripts/(check-oss-leaks|test-oss-leaks)\.sh$'
SKIP_DIRS='(^|/)(node_modules|\.git|dist|build|coverage|\.venv|__pycache__|\.next)(/|$)'

content_of() { # $1=path → prints file content for the active scope
  if [[ "$MODE" == "staged" ]]; then git show ":$1" 2>/dev/null || true
  else cat -- "$1" 2>/dev/null || true; fi
}

# ─── Pattern layer (generic; shipping-safe — no operator data) ──────────────
# Personal-path regexes are assembled from segments so this file never contains
# a literal personal home path (repo path-hygiene gates scan scripts/ verbatim).
HOMESEG_MAC="Users"
HOME_RE="/(${HOMESEG_MAC})/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|[A-Za-z]:\\\\+${HOMESEG_MAC}\\\\+[A-Za-z0-9._ -]+"
NEUTRAL_HOME_RE="/(${HOMESEG_MAC}|home)/(example|user|users|username|yourname|you|jdoe|johndoe|janedoe|runner|__[a-z]+__|<[a-z-]+>)([^A-Za-z0-9._-]|$)"
DOTDIR_RE='(~|\$HOME|%USERPROFILE%)/\.(ssh|aws|kube|gcloud|azure|docker)([^A-Za-z0-9]|$)|\.ssh/(id_[a-z0-9]+|config|known_hosts)|\.aws/credentials|\.kube/config|\.docker/config\.json|\.config/gcloud/|application_default_credentials\.json'
KEYBLOCK_RE='BEGIN [A-Z ]*PRIVATE KEY'
TOKEN_RE='sk_live_[A-Za-z0-9]{8,}|sk_test_[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|glpat-[A-Za-z0-9_-]{15,}|AIza[0-9A-Za-z_-]{30,}|ASIA[0-9A-Z]{16}|sb_secret_[A-Za-z0-9_-]{20,}|fo1_[A-Za-z0-9_-]{20,}|nfp_[A-Za-z0-9]{20,}|dop_v1_[a-f0-9]{64}|AccountKey=[A-Za-z0-9+/=]{40,}|"private_key_id":[[:space:]]*"[a-f0-9]{40}"'
ASSIGN_RE='(api[_-]?key|apikey|api[_-]?secret|client[_-]?secret|secret|token|passwd|password|bearer|credential|access[_-]?key|private[_-]?key|session[_-]?(id|key)|cookie)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9_+/=.-]{20,}'
ENVLINE_RE='^[[:space:]]*(export[[:space:]]+)?[A-Z][A-Z0-9_]*(SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY|ACCESS_KEY|CREDENTIALS?)[A-Z0-9_]*=[^[:space:]]{8,}'
CONN_RE='(postgres(ql)?|mysql|mongodb(\+srv)?|redis|amqps?|mssql|ftp)://[^:/@[:space:]]+:[^@[:space:]]+@'
JWT_RE='eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
COOKIE_RE='(Set-)?Cookie:[^=]{0,80}=[A-Za-z0-9+/=_-]{16,}'
# Obfuscated code-execution droppers (starter-template supply-chain class).
# A finding needs a dynamic-execution SINK (EVALANCHOR) AND a deobfuscation
# ENCODER or a NETEXEC fetcher in the SAME FILE — a lone eval, lone base64 blob,
# lone vite config, or lone husky hook never matches (keeps false positives low so
# the gate is never disabled). Cross-file config<->.env splits are out of a
# same-file regex's reach by design; see the TIER-1 LIMITATION note in the header.
#
# SINKS: JS eval / new Function / vm.runInContext|Script|compileFunction / dynamic
# import(); Python exec/compile/__import__ (eval covered); PowerShell Invoke-Expression
# / IEX / -EncodedCommand.
EVALANCHOR_RE='eval[[:space:]]*\(|new[[:space:]]+Function[[:space:]]*\(|vm\.(runInContext|Script|compileFunction)[[:space:]]*\(|(^|[^.[:alnum:]_])import[[:space:]]*\(|(^|[^.[:alnum:]_])exec[[:space:]]*\(|(^|[^.[:alnum:]_])compile[[:space:]]*\(|__import__[[:space:]]*\(|Invoke-Expression|(^|[^A-Za-z-])IEX([^A-Za-z]|$)|-EncodedCommand'
# ENCODERS: base64 (atob/Buffer.from/*decode), hex + charCode + parseInt(_,16) +
# fromhex, long \x / \u escape runs, string-reversal, and XOR-byte reconstruction.
B64DECODE_RE='atob[[:space:]]*\(|Buffer\.from[[:space:]]*\([^)]*base64|base64[_-]?decode|b64decode|FromBase64String|String\.fromCharCode|\.charCodeAt[[:space:]]*\(|parseInt[[:space:]]*\([^)]*,[[:space:]]*16[[:space:]]*\)|bytes\.fromhex|\.fromhex[[:space:]]*\(|(\\x[0-9A-Fa-f]{2}){4,}|(\\u[0-9A-Fa-f]{4}){3,}|\.reverse[[:space:]]*\([[:space:]]*\)[[:space:]]*\.join|\^[[:space:]]*0x[0-9A-Fa-f]{1,2}'
# NETEXEC: second-stage fetchers whose result is commonly piped into a sink.
NETEXEC_RE='fetch[[:space:]]*\(|node-fetch|child_process|execSync[[:space:]]*\(|spawnSync[[:space:]]*\(|requests\.get[[:space:]]*\(|urllib\.request|Invoke-WebRequest|Invoke-RestMethod'
# Same-file fetch/decode-then-exec dataflow tells (fire on their own).
FETCHEVAL_RE='eval[[:space:]]*\([[:space:]]*await|eval[[:space:]]*\([[:space:]]*response|\.text\(\).*eval|eval.*\.text\(\)|exec[[:space:]]*\([[:space:]]*requests\.get|exec[[:space:]]*\([[:space:]]*urllib'
# decode-of-env/argv reaching a same-file exec sink (the anchor's shape when the
# decode and sink share a file; the cross-file variant needs Tier-2 taint).
ENVDECODE_RE='(atob|Buffer\.from|b64decode|base64[_-]?decode|String\.fromCharCode|bytes\.fromhex)[^;]*(process\.env|process\.argv|os\.environ|sys\.argv|\$\{?[A-Z_]+\}?)'
ENVB64_RE='^[A-Za-z_][A-Za-z0-9_]*=["'"'"']?[A-Za-z0-9+/_-]{24,}={0,2}["'"'"']?[[:space:]]*$'
# Committed-config JS worm (a real 2026 incident: obfuscated payload appended to a
# build/CSS config, e.g. postcss.config.mjs / tailwind.config.js). Same-file,
# network-free shape checks, no cross-file dataflow needed:
#   (a) campaign tag: global['x']='N-dddd' style assignment used as a payload marker
#   (b) whitespace-padded code: a long blank run hides code past the visible margin
#   (c) javascript-obfuscator scaffold: the generated dispatcher function, or a
#       cluster of _0x-named identifiers, inside a config/build file
WORMTAG_RE='global\[["'"'"'](!|_V)["'"'"']\][[:space:]]*=[[:space:]]*["'"'"']A?9-7678|global\[["'"'"'][^"'"'"']{1,3}["'"'"']\][[:space:]]*=[[:space:]]*["'"'"'][A-Z]?[0-9]{1,3}-[0-9*]{1,6}(-[0-9]{1,3})?["'"'"']|global\.i[[:space:]]*=[[:space:]]*["'"'"'][A-Z]?[0-9]{1,3}-\*?[0-9]{1,6}(-[0-9]{1,3})?["'"'"']'
WORMPAD_RE='[[:blank:]]{200,}[^[:blank:]]'
WORMOBFFN_RE='function[[:space:]]+_0x[0-9a-f]+[[:space:]]*\([[:space:]]*\)[[:space:]]*\{[[:space:]]*var[[:space:]]+_0x[0-9a-f]+[[:space:]]*=[[:space:]]*\['
WORMOBFID_RE='_0x[0-9a-f]{4,}'
# A unicode-escaped module name inside require(...) in a config/build file — an
# obfuscation tell (e.g. require("http") for require("http")); no legitimate
# reason for a build config to escape a plain ASCII module specifier this way.
WORMUCREQ_RE='require[[:space:]]*\([^)]*\\u00[0-9a-fA-F]{2}[^)]*\)'
WORMPADEXT_RE='\.(js|mjs|cjs|ts|mts|cts|jsx|tsx)$'
WORMCFGFILE_RE='\.config\.[cm]?[jt]sx?$|(^|/)(vite|vitest|webpack|rollup|jest|babel|next|svelte|astro|tsup|esbuild|postcss|tailwind)\.[cm]?[jt]s$'
PLACEHOLDER_RE='(x{4,}|X{4,}|your[-_]|example|placeholder|dummy|changeme|change-me|change_me|redacted|<[a-z_ -]+>|\$\{|\{\{|=\$|"\$|'"'"'\$|\.\.\.)'
PRIVIP_RE='(^|[^0-9.])(10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3})([^0-9.]|$)'
INTHOST_RE='[A-Za-z0-9][A-Za-z0-9-]*\.(internal|intranet|lan|corp)([^A-Za-z0-9.-]|$)'
SSHDEST_RE='ssh[[:space:]]+(-[A-Za-z][[:space:]]+[^[:space:]]+[[:space:]]+)*[A-Za-z0-9._-]+@[A-Za-z0-9.-]+'
EMAIL_RE='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
PHONE_RE='\+[0-9]{2}[0-9 ()./-]{6,13}[0-9]([^0-9]|$)|\([0-9]{3}\) ?[0-9]{3}-[0-9]{4}'
LOCALHOST_RE='https?://(localhost|127\.0\.0\.1):[0-9]+'

# ─── Cloud identifiers (INFRA, MAJOR) ───────────────────────────────────────
# Account/project/team ids and provider hostnames map a private deployment
# topology (which account, which region, which team, which preview). Documented
# placeholders (example, my-app, <project>, the AWS docs sample account) are
# exempt via CLOUD_NEUTRAL_RE. Provider TOKENS live in TOKEN_RE (SECRET).
CLOUD_AWS_RE='arn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:[0-9]{12}:|[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com|[a-z0-9.-]+\.(rds|elb|execute-api|elasticbeanstalk)\.[a-z0-9-]+\.amazonaws\.com|[a-z0-9-]+\.s3\.[a-z0-9-]+\.amazonaws\.com|s3://[a-z0-9][a-z0-9.-]{2,62}([^a-z0-9.-]|$)|[a-z0-9]{8,}\.cloudfront\.net'
CLOUD_GCP_RE='[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com|projects/[a-z][a-z0-9-]{4,28}[a-z0-9]/(locations|secrets|serviceAccounts|topics|subscriptions|instances)|[a-z0-9-]+\.(run\.app|appspot\.com|cloudfunctions\.net)([^a-z0-9.-]|$)|gs://[a-z0-9][a-z0-9._-]{2,62}([^a-z0-9._-]|$)'
CLOUD_VERCEL_RE='prj_[A-Za-z0-9]{20,}|team_[A-Za-z0-9]{20,}|[a-z0-9-]+\.vercel\.app([^a-z0-9.-]|$)'
CLOUD_EDGE_RE='[a-z0-9-]+\.(workers\.dev|pages\.dev|fly\.dev|up\.railway\.app|onrender\.com|netlify\.app|azurewebsites\.net|blob\.core\.windows\.net|supabase\.(co|in))([^a-z0-9.-]|$)|(account_id|zone_id|accountId|zoneId)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"']?[a-f0-9]{32}'
CLOUD_NEUTRAL_RE='example|my-(app|project|site|team|service|bucket|proj|api)|your-|<[a-z_-]+>|\$\{|\{\{|acme|placeholder|123456789012|xxx|aaaa|0000|todo|foo|bar|demo|sample|test-|-test|dummy|project-id|bucket-name|\*\.'

# Emails already public in this repo's git identity are allowed.
{ git config user.email 2>/dev/null || true
  git log -500 --format='%ae%n%ce' 2>/dev/null || true
} | sort -u | grep -E "$EMAIL_RE" >"$TMP/known-emails" || true

apply_allow() { # stdin → stdout minus --allow patterns
  local out; out="$(cat)"
  for p in ${ALLOW_PATTERNS[@]+"${ALLOW_PATTERNS[@]}"}; do
    out="$(echo "$out" | grep -vE -- "$p" || true)"
  done
  [[ -n "$out" ]] && echo "$out" || true
}

record() { # $1=class $2=file $3=hits(line-numbered) [$4=suffix after truncation]
  [[ -z "$3" ]] && return 0
  if [[ -n "${4:-}" ]]; then
    echo "$3" | cut -c1-200 | sed "s|^|$2:|; s|\$| ${4}|" >>"$TMP/$1"
  else
    echo "$3" | cut -c1-200 | sed "s|^|$2:|" >>"$TMP/$1"
  fi
}

scan_file() {
  local f="$1" c="$TMP/content"
  content_of "$f" >"$c"
  [[ -s "$c" ]] || return 0
  grep -Iq . "$c" 2>/dev/null || return 0   # binary

  # SECRET (CRITICAL)
  record SECRET "$f" "$(grep -nE "$KEYBLOCK_RE" "$c" | apply_allow || true)"
  record SECRET "$f" "$(grep -nE "$TOKEN_RE" "$c" | apply_allow || true)"
  record SECRET "$f" "$(grep -inE "$ASSIGN_RE" "$c" | grep -viE "$PLACEHOLDER_RE" | apply_allow || true)"
  record SECRET "$f" "$(grep -nE "$ENVLINE_RE" "$c" | grep -viE "$PLACEHOLDER_RE" | apply_allow || true)"
  record SECRET "$f" "$(grep -nE "$CONN_RE" "$c" | grep -viE "$PLACEHOLDER_RE|(user|username):(pass|password)@" | apply_allow || true)"
  record SECRET "$f" "$(grep -nE "$JWT_RE" "$c" | apply_allow || true)"
  record SECRET "$f" "$(grep -nE "$COOKIE_RE" "$c" | grep -viE "$PLACEHOLDER_RE" | apply_allow || true)"

  # DROPPER (CRITICAL): obfuscated code-execution shapes
  record DROPPER "$f" "$(grep -nE "$FETCHEVAL_RE" "$c" | apply_allow || true)"
  record DROPPER "$f" "$(grep -nE "$ENVDECODE_RE" "$c" | apply_allow || true)" "← decode of an env/argv value feeding an exec sink (same-file dataflow tell)"
  if grep -qE "$EVALANCHOR_RE" "$c" && grep -qE "$B64DECODE_RE|$NETEXEC_RE" "$c"; then
    record DROPPER "$f" "$(grep -nE "$EVALANCHOR_RE" "$c" | apply_allow || true)" "← exec sink (eval/new Function/vm/import/exec/IEX) + encoder/fetch in the same file"
  fi
  local base; base="$(basename "$f")"
  if [[ "$base" == ".env" || ( "$base" == .env.* && "$base" != ".env.example" ) ]]; then
    record DROPPER "$f" "$(grep -nE "$ENVB64_RE" "$c" | apply_allow || true)" "← base64 blob under an env-var key in a committed env file"
  fi

  # WORM (CRITICAL): committed-config JS worm — see header for the shape.
  record WORM "$f" "$(grep -nE "$WORMTAG_RE" "$c" | apply_allow || true)" "← global[] campaign-tag assignment (obfuscator payload marker)"
  if [[ "$f" =~ $WORMPADEXT_RE ]]; then
    record WORM "$f" "$(grep -nE "$WORMPAD_RE" "$c" | apply_allow || true)" "← 200+ space/tab run before code on one line (payload padding)"
  fi
  if [[ "$f" =~ $WORMCFGFILE_RE ]]; then
    # Later waves drop the padding and append the payload directly, leaving one huge
    # line. grep/git grep reject {1000,} (255-repetition limit) — use awk.
    record WORM "$f" "$(awk 'length($0) > 1000 { printf "%d:%s\n", NR, substr($0, 1, 120); exit }' "$c" | apply_allow || true)" "← line over 1000 chars in a config/build file (appended payload)"
  fi
  if [[ "$f" =~ $WORMCFGFILE_RE ]]; then
    record WORM "$f" "$(grep -nE "$WORMOBFFN_RE" "$c" | apply_allow || true)" "← javascript-obfuscator dispatcher function scaffold"
    local obf_n
    obf_n="$(grep -oE "$WORMOBFID_RE" "$c" 2>/dev/null | sort -u | wc -l | tr -d ' ' || true)"
    if [[ "${obf_n:-0}" -ge 5 ]]; then
      record WORM "$f" "$(grep -nE "$WORMOBFID_RE" "$c" | head -1 | apply_allow || true)" "← ${obf_n} distinct _0x-obfuscated identifiers in a config/build file"
    fi
    record WORM "$f" "$(grep -nE "$WORMUCREQ_RE" "$c" | apply_allow || true)" "← unicode-escaped module name inside require() in a config/build file"
  fi

  # INVISIBLE_UNICODE (CRITICAL): zero-width, bidi, PUA, tag, and supplementary
  # variation-selector codepoints that hide executable text from human review and
  # token scanners (GlassWorm class). BMP variation selectors U+FE00-FE0F are
  # excluded — emoji legitimately use U+FE0F. python3 is an engineer dependency; when
  # it is absent the class degrades to a warning rather than a silent pass.
  if [[ "$HAVE_PY" -eq 1 ]]; then
    record INVISIBLE_UNICODE "$f" "$(scan_invisible "$c" | apply_allow || true)"
  fi

  # PATH (MAJOR)
  record PATH "$f" "$(grep -nE "$HOME_RE" "$c" | grep -vE "$NEUTRAL_HOME_RE" | apply_allow || true)"
  record PATH "$f" "$(grep -nE "$DOTDIR_RE" "$c" | apply_allow || true)"

  # INFRA (MAJOR)
  record INFRA "$f" "$(grep -nE "$PRIVIP_RE" "$c" | grep -vE '0\.0\.0\.0|/([89]|1[0-9]|2[0-9]|3[0-2])([^0-9]|$)' | apply_allow || true)"
  record INFRA "$f" "$(grep -nE "$INTHOST_RE" "$c" | apply_allow || true)"
  record INFRA "$f" "$(grep -nE "$SSHDEST_RE" "$c" | grep -viE 'example\.|@(host|hostname|server|localhost)([^A-Za-z0-9.-]|$)' | apply_allow || true)"
  # INFRA (MAJOR): cloud identifiers — see CLOUD_*_RE
  record INFRA "$f" "$(grep -nE "$CLOUD_AWS_RE" "$c" | grep -viE "$CLOUD_NEUTRAL_RE" | apply_allow || true)" "← AWS account/resource identifier"
  record INFRA "$f" "$(grep -nE "$CLOUD_GCP_RE" "$c" | grep -viE "$CLOUD_NEUTRAL_RE" | apply_allow || true)" "← GCP project/service-account identifier"
  record INFRA "$f" "$(grep -nE "$CLOUD_VERCEL_RE" "$c" | grep -viE "$CLOUD_NEUTRAL_RE" | apply_allow || true)" "← Vercel project/team/deployment identifier"
  record INFRA "$f" "$(grep -nE "$CLOUD_EDGE_RE" "$c" | grep -viE "$CLOUD_NEUTRAL_RE" | apply_allow || true)" "← edge/PaaS deployment identifier (Cloudflare/Fly/Railway/Render/Netlify/Azure/Supabase)"

  # PERSONAL (MAJOR)
  local emails
  emails="$(grep -noE "$EMAIL_RE" "$c" | grep -viE '@(example|test)\.[a-z]+|@[A-Za-z0-9.-]*example[A-Za-z0-9.-]*\.|\.(invalid|test|internal|local|lan|corp)$|noreply|no-reply|@localhost|@(my-[a-z0-9-]+|example[a-z0-9-]*|project-id|your-[a-z0-9-]+|<[a-z_-]+>)\.|^(my-|your-|example)[a-z0-9-]*@' || true)"
  if [[ -n "$emails" ]]; then
    while IFS= read -r hit; do
      local addr="${hit#*:}"
      grep -qiFx -- "$addr" "$TMP/known-emails" && continue
      echo "$hit" | apply_allow | sed "s|^|$f:|" >>"$TMP/PERSONAL" || true
    done <<<"$emails"
  fi
  record PERSONAL "$f" "$(grep -nE "$PHONE_RE" "$c" | grep -viE 'phone-?number|E\.164|\+[0-9]{1,3}[ -]?555' | apply_allow || true)"

  # MARKER (MAJOR) — operator-specific, from the local marker file only
  local m
  for m in ${M_NAMES[@]+"${M_NAMES[@]}"}; do
    record MARKER "$f" "$(grep -nF -- "$m" "$c" | apply_allow || true)" "← marker [names]"
  done
  for m in ${M_BUSINESS[@]+"${M_BUSINESS[@]}"}; do
    record MARKER "$f" "$(grep -nF -- "$m" "$c" | apply_allow || true)" "← marker [business]"
  done
  for m in ${M_PATHS[@]+"${M_PATHS[@]}"}; do
    record MARKER "$f" "$(grep -nF -- "$m" "$c" | apply_allow || true)" "← marker [paths]"
  done

  # NOTE (informational, --notes only): localhost endpoints presented in docs
  if [[ "$NOTES" -eq 1 && "$f" == *.md ]]; then
    record NOTE "$f" "$(grep -nE "$LOCALHOST_RE" "$c" || true)"
  fi
}

SCANNED=0
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  [[ "$f" =~ $SELF_SKIP ]] && continue
  [[ "$f" =~ $SKIP_DIRS ]] && continue
  scan_file "$f"
  SCANNED=$((SCANNED + 1))
done <"$TMP/files"

# Optional accelerator — never required, never replaces the deterministic layer.
if [[ "$USE_GITLEAKS" -eq 1 ]]; then
  if command -v gitleaks >/dev/null 2>&1; then
    GL_ARGS=(detect --no-banner --redact)
    [[ "$MODE" == "staged" ]] && GL_ARGS=(protect --staged --no-banner --redact)
    if ! gitleaks "${GL_ARGS[@]}" >/dev/null 2>&1; then
      echo "gitleaks:0:gitleaks reported leaks (run: gitleaks ${GL_ARGS[*]})" >>"$TMP/SECRET"
    fi
  else
    echo "WARN --gitleaks requested but gitleaks is not installed (deterministic layer ran)" >&2
  fi
fi

# ─── Grouped report + severity model ────────────────────────────────────────
CRITICAL=0
MAJOR=0
scope_label="$MODE"
[[ "$MODE" == "ref" ]] && scope_label="ref $REF"
say "check-oss-leaks — scope: $scope_label · $SCANNED file(s) · marker layer: $([[ $MARKERS_ON -eq 1 ]] && echo on || echo off)"

report_class() { # $1=class $2=severity
  local n
  n="$(grep -c . "$TMP/$1" 2>/dev/null || true)"
  [[ "$n" -eq 0 ]] && return 0
  if [[ "$2" == "CRITICAL" ]]; then CRITICAL=$((CRITICAL + n)); else MAJOR=$((MAJOR + n)); fi
  say ""
  say "[$1 · $2 · $n finding(s)]"
  [[ "$QUIET" -eq 0 ]] && sed 's/^/  /' "$TMP/$1"
  return 0
}
report_class SECRET CRITICAL
report_class DROPPER CRITICAL
report_class WORM CRITICAL
report_class INVISIBLE_UNICODE CRITICAL
report_class PATH MAJOR
report_class INFRA MAJOR
report_class PERSONAL MAJOR
report_class MARKER MAJOR
if [[ "$NOTES" -eq 1 && -s "$TMP/NOTE" ]]; then
  say ""
  say "[NOTE · informational · $(grep -c . "$TMP/NOTE") line(s): localhost endpoints in docs — verify they are examples, not real topology]"
  [[ "$QUIET" -eq 0 ]] && sed 's/^/  /' "$TMP/NOTE"
fi

say ""
say "---"
say "CRITICAL $CRITICAL · MAJOR $MAJOR"
if [[ "$CRITICAL" -gt 0 ]]; then
  say "FAIL: secrets and code-execution droppers must never enter the repository (no --warn-only downgrade)"
  exit 1
fi
if [[ "$MAJOR" -gt 0 ]]; then
  if [[ "$WARN_ONLY" -eq 1 ]]; then
    say "WARN-ONLY: $MAJOR MAJOR finding(s) reported without failing"
    exit 0
  fi
  say "FAIL: private-context findings — move personal config to local files outside the repo, use neutral placeholders, or pass --allow for public-identity exceptions"
  exit 1
fi
say "CLEAN — no private-context findings"
exit 0
