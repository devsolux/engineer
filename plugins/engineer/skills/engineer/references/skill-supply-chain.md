# Agent skill supply chain

**Last verified**: 2026-10-22 · **Review cadence**: 2 months

Use this module before installing or trusting a third-party skill, plugin, hook, MCP server,
package runner, installer, or bundled model. A skill is executable influence, even when it contains
only Markdown.

## Admission sequence

1. Resolve the canonical owner and repository. Reject typosquats, mirrors without provenance, and
   mutable download URLs.
2. Pin an immutable commit or artifact digest. Record the version label separately for humans.
3. Inventory every file, executable bit, dependency, hook, MCP registration, model artifact,
   network destination, requested secret, and write boundary.
4. Read both instructions and code. Look for dependency steering, hidden capabilities, encoded or
   invisible text, credential discovery, telemetry, persistence, approval bypass, and sandbox
   weakening.
5. Resolve dependencies without running lifecycle scripts where the package manager permits it. Review
   lockfile changes, integrity metadata, maintainer history, package age, and unexpected transitive
   additions.
6. Run static scanners, then detonate realistic benign and adversarial tasks inside a disposable
   sandbox with synthetic secrets, denied egress, filesystem and process observation, and cleanup.
7. Compare advertised behavior with observed sources and sinks. Reject shadow features.
8. Install into a low-privilege host first. Promote only with an owner, review date, rollback path,
   and recurring update review.

## Source class is not trust

Classify the source before admission, but evaluate the exact skill and immutable revision:

| Source class | Useful signal | Engineer treatment |
|---|---|---|
| First-party product skill | Narrow, current product or SDK knowledge | Prefer for that product after version, license, instruction, tool, and evidence review |
| Signed or evaluated vendor catalog | Publisher identity, integrity, and benchmark artifacts | Verify signatures and reproduce relevant evals; neither proves safe behavior in this task |
| Specialist methodology pack | Deep review or testing technique | Compose for a bounded pass with Engineer retaining authority and acceptance gates |
| Curated mirror or catalog | Discovery, provenance links, sometimes scanning | Follow the canonical source; curation and scanner labels do not transfer trust |
| Community marketplace | Breadth and emerging patterns | Discovery only until the individual candidate completes quarantine admission |
| Installer or registry CLI | Cross-host distribution | Treat the CLI, registry, resolved source, and installed payload as separate supply-chain subjects |

Never bulk-install a catalog, infer safety from stars or organization ownership, or let an update
silently replace the reviewed revision. A deprecated catalog is historical input, not a current
installation source. Prefer read-only inspection before quarantine execution.

For product-specific work, current first-party documentation remains the authority when a skill and
the product disagree. For specialist security work, compose the smallest relevant pass - such as
differential review, insecure-default analysis, property-based testing, mutation testing, or
spec-to-code comparison - then reproduce findings in the project test and threat model.

## Executable guidance

- Never pipe a network response into a shell or interpreter.
- Prefer `pnpm exec`, `npm exec --offline`, or equivalent local locked binaries.
- Do not use floating `latest` package runners in instructions or CI.
- Pin GitHub Actions to a full 40-character commit SHA and annotate the reviewed release. GitHub's
  workflow dependency lockfile (`.github/workflows/actions.lock`, public preview) also pins transitive
  actions and supersedes SHA pins where adopted; the repository gate below still requires SHA pins.
- Treat installer signatures, checksums, and attestations as provenance evidence, not behavior proof.
- A scanner pass is one layer. Semantic instruction review and runtime observation remain required.
- Plugins bundle `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, monitors, and `bin/` executables that
  run code behind the project trust gate - personal-scope plugins have no such gate, and `allowed-tools`
  is not enforced on every host, so admission reviews the bundled code itself. Cross-host exposure is
  real: Grok Build reads and runs Claude-format hooks and plugins, and Cursor imports
  `.claude/settings*.json` hooks by default, so a Claude-scoped hook is their attack surface too.
  Hosts such as Codex follow symlinked skill folders, so symlinked skills can bypass digest-walk
  admission gates (measured locally, 2026-07-16); pin gates must resolve symlinks.

Run the repository gate:

```bash
python3 scripts/scan-doc-supply-chain.py
```

It scans executable Markdown fences and active workflow actions. Defensive prose is intentionally
out of scope so warnings remain actionable.

## Scaffold, surface, and description checks

- **Cloned starter templates are a first-execution surface** distinct from a published package:
  a `create-*` / `degit` / git-cloned scaffold has **no registry provenance** - Socket/Snyk/
  OpenSSF never see it - so a malicious build/test config that runs on the first `npm run dev`
  must be caught by *reading the config*, not by a provenance check. Run the leak/dropper gate
  over a cloned template as part of admission (`malware-detection.md` for the taxonomy).
- **Always-read scan surfaces** (read in full, do not skim): build/test config (`vite`/`vitest`/
  `webpack`/`rollup`/`next`), test setup, `.husky/*` + `.git/hooks/*`, `package.json` scripts,
  `.github/workflows/*`, `.vscode/`, `.devcontainer`, `.claude/settings*.json`, `.cursor/rules` +
  `.cursor/hooks.json`, `.grok/hooks/`, `AGENTS*`, `.mcp.json`.
- **Tool-description linter class**: a tool description that should be declarative but carries
  imperatives, credential/file-path references, hidden unicode/ANSI, or another server's tool
  names is a poisoning/shadowing signal - flag it (see `mcp-security.md`).
- **MINJA persistence**: query-only memory poisoning leaves no admission-time artifact and fires
  later, so treat durable memory/RAG as a standing admission surface, not a one-time gate.

## Admission receipt

Copy `templates/agentic/skill-admission.sample.json` into the quarantine review workspace. The
receipt binds the canonical immutable source to every local file hash and executable bit, exact
dependencies and integrity, declared and observed capabilities, permissions, endpoints, hooks,
MCP servers, models, analysis results, sandbox cases, reviewers, rollback, and review expiry.

```bash
python3 scripts/validate-skill-admission.py skill-admission.json --json
```

`trust` is allowed only when the receipt and evidence agree. High-privilege permissions are not rejected
merely for existing; each must map to an advertised and observed capability and an explicit accepted
risk. Networked candidates require simulated allowlisted-egress evidence. Symlinks, shadow
capabilities, forged tree state, self-review, expired review, and unresolved trust fail closed.

The shipped sample is an `illustrative_fixture` and remains quarantined. Only a
`captured_review` with real preserved evidence can authorize `trust`.

The validator confirms receipt consistency. It does not independently establish repository
ownership, execute the sandbox cases, or prove benign intent. Preserve the raw evidence it cites.

**Related**: `ai-security.md`, `agent-red-teaming.md`, `skill-authoring.md`

**Research basis**: `../research/skill-supply-chain-2026-07.md`
