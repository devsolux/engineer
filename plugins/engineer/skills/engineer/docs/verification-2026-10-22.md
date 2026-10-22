# Verification ledger — 2026-10-22

Currency review for release 1.1.0, started on the unmodified 1.0.0 tree (5ac51a3) on
macOS 27.0.0 (arm64) with Python 3.11.17, PyYAML 6.0.3, Node 24.22.0, TypeScript 5.8.3,
Claude Code 2.1.282, Codex CLI 0.163.0-alpha.11, gh 2.102.0, git 2.56.0. Research notes keep
their own dates; this ledger does not re-verify them.

## Baseline checks on the unmodified 1.0.0 tree

| Check | Result |
|---|---|
| `git status` / `git ls-remote origin` | Clean worktree; `main` and `origin/main` both at 5ac51a3 ("Release 1.0.0"). The public repository exists (the 2026-10-11 ledger predates its creation); no `v1.0.0` tag exists locally or on origin |
| `make check` | Passed (263 files parsed, repository gates, 208 static eval scenarios) |
| `make test JOBS=4` | 51/51 isolated offline suites passed |
| `make verify-build` | No drift |
| `python3 scripts/report-module-currency.py --today 2026-10-22` | 66 of 113 reference modules past their own review cadence; none missing a header (see "Not re-verified" below) |

## Sources checked

| Area | Finding | Primary source |
|---|---|---|
| Claude Code | 2.1.307 is the newest changelog entry; 2.1.304 capped skill hooks (1,024 per source per session, 16,384-character matcher), limited prompt/agent hooks to 12 per event, changed `/reload-skills`, and removed the hook-location notes from `claude plugin validate` | code.claude.com/docs/en/changelog |
| Codex CLI | 0.164.0-alpha.10 released 2026-10-22; `codex plugin` surface unchanged | github.com/openai/codex/releases |
| Next.js | 16.4.2 stable (2026-10-15); Next 15 reached end-of-life on 2026-10-21 | github.com/vercel/next.js/releases; Next.js support policy |
| Node.js | Node 24 → Maintenance LTS 2026-10-20 (EOL 2028-04-30); Node 26 → Active LTS 2026-10-28 (EOL 2029-04-30); one major per year from Node 27 | Node.js Release Working Group schedule |
| TypeScript | 7.0.2 is npm `latest`; 5.8.3 baseline still published | npm registry |
| PyYAML | 6.0.3 is the newest release | PyPI |
| GitHub Action pins | checkout v7.0.1 `3d3c42e5`, setup-python v7.0.0 `5fda3b95`, setup-node v7.1.0 `949feb24` remain the latest releases | GitHub releases pages |
| MCP specification | 2026-07-28 is current: stateless core (no sessions, no `initialize`, `_meta` versioning, `server/discover`, `resultType`, multi-round-trip requests); Roots, Sampling, Logging, HTTP+SSE and OAuth Dynamic Client Registration deprecated; Tasks moved to an optional extension | modelcontextprotocol.io/specification/latest/changelog |

## Applied in this release

- `COMPAT.md`, `references/stack-rules.md`, `references/project-detect.md`, `references/deploy-ops.md`,
  `templates/github/engineer-gates.yml`: Next 15 end-of-life and the Node 24 → 26 LTS handoff.
- `.github/workflows/validate.yml`: runs on `push` to `main` and on `pull_request`; adds a Node 26 lane.
- `references/mcp-security.md` and `commands/engineer-mcp-audit.md`: re-verified against the
  2026-07-28 changelog (deprecations, stateless core, client registration, Tasks extension).
  `scripts/compile-mcp-transcript.py` and `scripts/validate-mcp-session.py` now reject a
  2026-07-28 transcript or receipt with an explicit message instead of a generic one; the fixtures
  stay on 2025-11-25 as explicit scenario inputs (COMPAT.md). Eval 169 wording aligned.
- `references/coding-agent-hosts.md`: host versions and the 2.1.304 hook limits re-checked.
- `scripts/report-module-currency.py` + `scripts/test-module-currency.sh`: deterministic review-cadence
  report, printed informationally by `scripts/validate-repo.sh`.

## Not re-verified (recorded, not redated)

- The remaining reference modules past their review cadence as of 2026-10-22 (list:
  `python3 scripts/report-module-currency.py --today 2026-10-22`). Only `mcp-security.md`,
  `coding-agent-hosts.md` (host versions and hook limits), `stack-rules.md`, `project-detect.md` and
  `deploy-ops.md` received source re-checks in this release.

## Not established

- `make host-validate` ran on Claude Code 2.1.282 (see post-change gates); the local-marketplace install
  and Codex registration were last executed on 2026-10-11 and were not repeated on 2.1.307 / 0.164.0-alpha.10.
- Linux, Python 3.10/3.13, TypeScript 7.0.2 and Node 26 run only in GitHub Actions; the workflow was
  manual-trigger only before this release, so no CI run exists yet for the Node 26 lane.
- Vercel and AWS runtime support for Node 26 was not checked; app templates keep `node-version: 24`.
- No authenticated model session was run; live skill activation remains unverified here.
- A full 2026-07-28 stateless MCP transcript is rejected, not validated: the compiler and validators
  have no stateless fixture coverage yet.

## Post-change gates (1.1.0 working tree, same machine)

| Check | Result |
|---|---|
| `make lint` | Passed (275 files parsed; local links and marketplace identity) |
| `make fixtures` | Rebound the illustrative skill-eval hash chain (SKILL.md, bundle, 214-scenario bank); grader-verified |
| `make build` → `make check` → `make verify-build` | Built `plugins/engineer`; static gates passed (36 repository gates, 214 static eval scenarios, verb load budgets ≤800); no drift |
| `make test JOBS=4` | 55/55 isolated offline suites passed (51 prior + module currency, security findings, security coverage, security ledger tool) |
| `make package` | Deterministic `dist/engineer-1.1.0-plugin.zip` with its SHA-256 sidecar (the digest is not recorded here because this ledger ships inside the bundle it would describe) |
| `make host-validate` | `claude plugin validate --strict` passed for the marketplace and the plugin on Claude Code 2.1.282 |
| `python3 scripts/scan-doc-supply-chain.py` | Clean after pinning the three documented action references it newly caught |
| Security-audit samples | `validate-security-findings.py` and `validate-security-coverage.py` report `valid: true` with no errors or gates |

Not repeated here: local-marketplace install into throwaway host profiles, the Codex `codex plugin`
registration, and any live model run (see "Not established").

## Follow-up after 1.1.0 (e4d6f9a): MCP 2026-07-28 stateless evidence

Same machine and toolchain. This follow-up supersedes the "Not established" item above that said a
2026-07-28 transcript is rejected, not validated; that item stays as the 1.1.0 record.

| Fact encoded in the compiler/validators | Primary source (fetched 2026-10-22) |
|---|---|
| No `initialize` / `notifications/initialized` handshake and no `Mcp-Session-Id`; every request carries `io.modelcontextprotocol/protocolVersion` and `io.modelcontextprotocol/clientCapabilities` in `_meta`; clients SHOULD send `clientInfo`, servers SHOULD send `serverInfo` in each result's `_meta`; `ttlMs`/`cacheScope` required on list results and `resources/read`; Roots, Sampling, Logging and Dynamic Client Registration deprecated; Tasks moved to `io.modelcontextprotocol/tasks` | modelcontextprotocol.io/specification/latest/changelog |
| Missing required `_meta` fields are malformed (`-32602`); `resultType` is required, `complete` or `input_required`, unknown values invalid; `serverInfo` belongs in result `_meta` | modelcontextprotocol.io/specification/2026-07-28/basic/index |
| No negotiation handshake; servers MUST implement `server/discover`, clients MAY skip it; a dual-era server treats `initialize` as legacy semantics | modelcontextprotocol.io/specification/2026-07-28/basic/lifecycle |
| `DiscoverResult` carries `supportedVersions`, `capabilities`, optional `instructions`, `serverInfo` in `_meta`, plus `ttlMs`/`cacheScope` | modelcontextprotocol.io/specification/2026-07-28/server/discover |
| `MCP-Protocol-Version` header MUST equal the `_meta` version; a modern-only server ignores `Mcp-Session-Id` and never mints one; `Last-Event-ID` resumability removed | modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http |
| `input_required` results only on `prompts/get`, `resources/read`, `tools/call`; their `inputRequests` are server-to-client requests | modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr |
| `subscriptions/listen` replaces `resources/subscribe` and the GET stream; notifications carry `io.modelcontextprotocol/subscriptionId` | modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions |
| Deprecated registry: Roots, Sampling, Logging, Dynamic Client Registration deprecated in 2026-07-28, earliest removal in the first revision on or after 2027-07-28 | modelcontextprotocol.io/specification/2026-07-28/deprecated |
| Client `roots`/`sampling` and server `logging` capabilities marked Deprecated; `ReadResourceResult`/`DiscoverResult` `ttlMs` is a number | modelcontextprotocol.io/specification/2026-07-28/schema |
| Tasks extension: `resultType: "task"`, `tasks/get` / `tasks/update` / `tasks/cancel`, negotiated under `capabilities.extensions` | modelcontextprotocol.io/extensions/tasks/overview |

Applied: stateless lifecycle in `scripts/compile-mcp-transcript.py`, stateless receipt rules in
`scripts/validate-mcp-session.py`, a session/manifest version binding in
`scripts/validate-mcp-content.py`, fixtures under `templates/agentic/mcp-evidence-2026-07-28/`
with two receipt samples, and stateless mutation cases in the three MCP suites. The 2025-11-25
path kept its verdicts; an old-versus-new comparison over 40,000 random mutations of the
2025-11-25 transcript found no accept/reject change, only former tracebacks now reported as
`captured result invalid`.

Not established: no live 2026-07-28 server or SDK capture was observed; the fixtures are
synthetic. URL-mode elicitation receipts still carry the 2025-11-25 `completion_ids_validated`
control, although 2026-07-28 removed `elicitationId` in favour of retries with `requestState`.

## Release gates on the final 1.1.0 tree

The 1.1.0 release folds in both follow-ups: the MCP 2026-07-28 stateless evidence above and
`engineer fix --findings` (remediation from a validated `findings.json`, with
`validate-security-findings.py --remediated`). Both were merged on `main` before 1.1.0 was
published, so their changelog entries sit under 1.1.0. Same machine; Claude Code 2.1.282 and
Codex CLI 0.163.0-alpha.11 installed locally.

| Check | Result |
|---|---|
| `make fixtures` | Skill-eval chain already bound to the merged tree (bundle and 216-scenario bank digests); grader-verified |
| `make build` → `make lint` | No generated drift; source lint passed |
| `make release-check JOBS=4` | Static gates passed (216 static eval scenarios); 55/55 isolated offline suites passed; no bundle drift |
| `make host-validate` | `claude plugin validate --strict` passed for the marketplace and the plugin on Claude Code 2.1.282 |
| `python3 scripts/scan-doc-supply-chain.py` | Passed |
| `scripts/check-oss-leaks.sh --ref origin/main..HEAD` and the staged changeset | Clean (marker layer off: no private marker file on this machine) |
| `scripts/check-oss-leaks.sh --all` | 4 critical and 31 major findings, all in files unchanged since the public 1.0.0 commit: the deliberately fake key in the failing scan fixture, the exec-sink taxonomy row in `malware-detection.md`, and Python decorators in the `research/` corpus read as e-mail addresses |

Not executed for this release: the local-marketplace install into throwaway Claude Code and Codex
profiles, the Codex `codex plugin` registration, Claude Code 2.1.307 and Codex 0.164.0-alpha.10, and
any live model run. The 66 modules past their review cadence stay recorded under "Not re-verified".

## Publication

| Check | Result |
|---|---|
| `make github-push` | `main` pushed to `origin` as a fast-forward, 5ac51a3..2713d00 |
| `make github-release` | Release "Engineer 1.1.0" published 2026-10-22T07:44:59Z, not a draft or prerelease, with `engineer-1.1.0-plugin.zip` and its SHA-256 sidecar |
| `git ls-remote --tags origin` | `v1.1.0` → 2713d00; `v1.0.0` → 5ac51a3 (created outside this review, after the baseline above) |
| Release assets | The uploaded ZIP digest `3377003801c512f49f27123b4a5049b445299b64ae2db101f7f6e6ebd8a4fffe` and the sidecar equal the locally packaged files |
| GitHub Actions | The first push-triggered "Validate Engineer" run on 2713d00 was still in progress when this was recorded |

Not executed: installing 1.1.0 from GitHub into Claude Code and Codex to confirm both hosts resolve
`engineer@devsolux-engineer` at the new version (release procedure step 6).

## Install from GitHub into throwaway profiles

This supersedes the "Not executed" line under Publication. Same machine; Claude Code 2.1.282 and
Codex CLI 0.163.0-alpha.11. Every command ran under `env -i` with `HOME`, `CLAUDE_CONFIG_DIR`,
`CODEX_HOME` and the XDG directories pointing at a fresh scratch directory, with auto-update off.
Both hosts install from the default branch, so they received 817b950, which differs from the
`v1.1.0` tag (2713d00) only in this ledger and its plugin copy.

| Check | Result |
|---|---|
| `claude plugin marketplace add https://github.com/devsolux/engineer` → `claude plugin install engineer@devsolux-engineer` | Marketplace cloned at 817b950; `claude plugin list` shows `engineer@devsolux-engineer` at version 1.1.0, user scope, enabled |
| Installed Claude Code tree (`plugins/cache/devsolux-engineer/engineer/1.1.0`) | Identical to `plugins/engineer` apart from Claude Code's own `.in_use` marker; `SKILL.md` version 1.1.0; 51 commands including `engineer-security-audit` |
| `codex plugin marketplace add devsolux/engineer` → `codex plugin add engineer@devsolux-engineer` | Marketplace cloned at 817b950; `codex plugin list` shows `engineer@devsolux-engineer` installed and enabled at 1.1.0 |
| Installed Codex tree (`plugins/cache/devsolux-engineer/engineer/1.1.0`) | Identical to `plugins/engineer` |
| `codex debug prompt-input` (renders the prompt, no model call) | Skill registered as `engineer:engineer` from the 1.1.0 cache |
| Real host profiles | Claude Code marketplace catalog, installed-plugin record and settings, and the Codex config, had the same SHA-256 before and after. The throwaway Claude Code profile wrote its own state file. The shared `~/.claude.json` changed during the run but holds no reference to the throwaway directory; running desktop sessions write it |

Not exercised: the update and removal commands, Claude Code 2.1.307 and Codex 0.164.0-alpha.10, and
any live model run.

## CI after publication

The first push-triggered runs of "Validate Engineer" failed on all four lanes (runs 39742961104 on
817b950 and 39743604832 on 052b3c1; 39742646660 on 2713d00 was cancelled by the next push). Causes,
from the run logs and a local reproduction:

| Lane | Failure | Cause |
|---|---|---|
| Linux (three lanes) | `test-host-activation.sh` | `install-host-activation.py --remove` leaves 1-byte files behind. The test's `[[ ! -e … ]]` assertion catches it under the runners' bash 5; this Mac's bash 3.2.57 does not stop on a failing `[[ … ]]` under `set -e`, so the suite passed locally |
| macOS | `test-repo-validation.sh` | Exceeded the 180-second per-suite limit on the GitHub macOS runner (about 57 seconds on this machine) |

The fixes are recorded in the CHANGELOG "Unreleased" section. CI run 39758633347 on 022fdf5 passed on
all four lanes: Ubuntu with Python 3.10, TypeScript 5.8.3 and Node 24; Ubuntu with Python 3.13,
TypeScript 7.0.2 and Node 24 or Node 26; macOS with Python 3.13, TypeScript 7.0.2 and Node 24.
