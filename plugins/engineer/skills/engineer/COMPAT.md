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

Next.js 16.x is Active LTS and 15.x is Maintenance LTS as checked on 2026-10-11.
Existing Next 15 request boundaries should not be renamed blindly to Next 16's
`proxy.ts`. React, Tailwind, Supabase, Zod, Stripe, and Playwright examples must be
adapted to the target application's installed and patched versions.

The current MCP specification is 2026-07-28. Engineer contains security guidance
and evidence validators; it does not implement a transport/server. Older protocol
versions in fixtures are explicit scenario inputs, not promises of full support for
the newest protocol. Reject unsupported modes rather than silently downgrading.

`codex mcp-server` is no longer a current CLI entrypoint. `codex app-server` is a
different, experimental application protocol, not a drop-in MCP transport.

## Evidence terminology

Static checks establish repository consistency. Offline fixture tests exercise
code against synthetic cases. Template tests use TypeScript/Node and controlled
stubs, not an installed browser or production application. Model quality,
marketplace review, host permissions, and live workflow success need separate
captured evidence. `research/` dates are not refreshed by a release bump.

Sources and exact review scope: [2026-10-11 ledger](docs/verification-2026-10-11.md).
