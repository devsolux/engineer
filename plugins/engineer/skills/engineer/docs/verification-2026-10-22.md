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
