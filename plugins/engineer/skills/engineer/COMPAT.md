# Compatibility and verification boundaries

## Repository toolchain

| Component | Requirement / target | Verified 2026-10-11 |
|---|---|---|
| Python | 3.10+ for maintainer targets; CI runs 3.10 and 3.13 | 3.11.17 locally (macOS); installers also import under the stock macOS 3.9.6 |
| PyYAML | Exactly 6.0.3 (`requirements-dev.txt`) | 6.0.3 |
| Shell / Make | Bash and GNU Make | Bash 3.2.57 and GNU Make 3.81 (macOS system tools); Linux runs in CI |
| JavaScript fixtures | Node 24 LTS target | Node 24.21.0 |
| TypeScript fixtures | 5.8.3 baseline; 7.0.2 current target in CI | 5.8.3 locally; 7.0.2 is CI-only |
| Claude Code | Plugin marketplace support | 2.1.282: strict manifest validation and isolated local-marketplace install |
| Codex CLI | `codex plugin` marketplace support | 0.162.0-alpha.17.2: isolated local-marketplace install and skill registration |

Re-checked 2026-10-22: Node 24 moved to Maintenance LTS on 2026-10-20 and Node 26 becomes
Active LTS on 2026-10-28 (both run in CI); Claude Code 2.1.307 and Codex 0.164.0-alpha.10 are
current upstream, while the strict host validation below was last executed on the versions
listed. See the 2026-10-22 ledger for sources. Python 3.10 reached end-of-life on 2026-10-01
(devguide.python.org); the 3.10 floor and CI lane stay until a maintainer raises them.

GNU Make 3.81 ignores `.SHELLFLAGS`; recipes still fail on any nonzero command, but
3.82+ additionally applies `set -euo pipefail` inside each recipe line.

The upstream TypeScript compiler has advanced beyond 5.x. Preserve a consumer's
lockfile and compiler API dependencies; do not force an untested major upgrade.
This repository distributes templates, not an installed Next.js/React application.
No `node_modules`, secrets, or native runtime are shipped in the plugin.

## Packaging

Claude discovers `.claude-plugin/plugin.json` in the generated plugin and loads
`skills/engineer/SKILL.md`. Its plugin-namespaced commands (`/engineer:<workflow>`)
are thin wrappers; Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` in their bodies.
Codex reads `.codex-plugin/plugin.json` and registers the skill as `engineer:engineer`.
The portable root `plugin.json` follows Agent Plugins 1.0. All three manifests are
generated from `packaging/plugin.json` and the single `SKILL.md` version.

Git marketplace catalogs resolve `./plugins/engineer` from the repository root.
A ZIP containing only the installable plugin is not a marketplace repository and
is not an MCPB. Do not pass it to an incompatible desktop extension installer.
Local marketplace support in CLI does not establish support in every desktop,
web, mobile, account tier, or execution mode. See the verification source ledger.

## Consumer guidance, not bundled runtime dependencies

Next.js 16.x is Active LTS; 15.x reached end-of-life on 2026-10-21 (checked 2026-10-22), the end of
the support policy's two-year Maintenance LTS window; the policy page still listed 15.x that day.
Detected Next 15 apps keep their conventions and get an upgrade item; their request
boundaries should not be renamed blindly to Next 16's `proxy.ts`. React, Tailwind, Supabase, Zod, Stripe, and Playwright examples must be
adapted to the target application's installed and patched versions.

The current MCP specification is 2026-07-28. Engineer contains security guidance
and evidence validators; it does not implement a transport/server. The transcript
compiler and the session/content validators check both the 2025-11-25 handshake
shape and the 2026-07-28 stateless shape, each against its own synthetic fixture set
(`templates/agentic/mcp-evidence/` and `templates/agentic/mcp-evidence-2026-07-28/`).
Fixtures are scenario inputs, not a ceiling on what a capture may contain. Tasks,
multi-round-trip `input_required` results, and `subscriptions/listen` streams are
not admitted by the compiler. Reject unsupported or mixed modes rather than
silently downgrading.

`codex mcp-server` is no longer a current CLI entrypoint. `codex app-server` is a
different, experimental application protocol, not a drop-in MCP transport.

## Evidence terminology

The security-audit validators (`scripts/validate-security-findings.py`,
`scripts/validate-security-coverage.py`) prove record consistency, identifier derivation,
independence rules and evidence binding. They never prove exploitability, the absence of
vulnerabilities, or that a sandbox was actually enforced.

Static checks establish repository consistency. Offline fixture tests exercise
code against synthetic cases. Template tests use TypeScript/Node and controlled
stubs, not an installed browser or production application. Model quality,
marketplace review, host permissions, and live workflow success need separate
captured evidence. `research/` dates are not refreshed by a release bump.

Sources and exact review scope: [2026-10-11 ledger](docs/verification-2026-10-11.md),
[2026-10-22 ledger](docs/verification-2026-10-22.md),
[2026-10-22 module ledger](docs/verification-2026-10-22-modules.md) and
[2026-10-26 Rust module ledger](docs/verification-2026-10-26-rust.md).
