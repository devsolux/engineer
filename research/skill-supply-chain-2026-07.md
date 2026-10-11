# Agent skill and executable guidance supply-chain research

**Verified**: 2026-07-15

## Threat boundary

An agent skill is both operational instruction and a software package. It can influence which
dependencies an agent selects, request execution of bundled scripts, register hooks or MCP tools,
hide undeclared capabilities, and inherit the agent host's permissions. Ordinary malware scanning
sees only part of this boundary; prompt-only scanning misses executable behavior.

## Controls adopted

- Treat every third-party skill, plugin, hook, MCP server, installer, package runner, and bundled
  model as untrusted until source identity, immutable revision, files, permissions, and behavior
  have been reviewed.
- Never execute a network response directly with a shell or language interpreter.
- Prefer an already locked local executable. If bootstrapping is necessary, select an exact version,
  inspect registry provenance and integrity metadata, resolve into a lockfile, then execute locally.
- Pin GitHub Actions to full commit SHAs and retain the human-readable release in a comment.
- Inspect instruction semantics for dependency steering, impersonation, hidden capabilities,
  obfuscated text, encoded payloads, environment or credential access, telemetry, persistence,
  hook registration, and attempts to weaken approvals or sandboxes.
- Combine static policy, source review, isolated behavioral testing, and runtime observation. A clean
  deterministic scan is a narrow gate, not proof that a skill is benign.
- Bind the admission decision to a complete file tree and executable-mode digest. Reject symlinks,
  undeclared files, shadow capabilities, missing dependency integrity, stale review, and reviewer
  identity collisions. Record accepted elevated risks separately from unresolved risks.

## Evidence

- GitHub states that a full-length commit SHA is the only immutable way to reference an Action.
- npm documents that `npx` may install a missing package into its cache before execution; exact
  version specifiers are required to match an exact local package version.
- Current agent-skill research demonstrates dependency steering through persistent skill text,
  semantic manipulation of discovery and governance, and attacks spanning code plus instructions.

### Action pins verified 2026-07-15

| Repository | Reviewed release | Commit |
|---|---|---|
| `actions/checkout` | `v7.0.0` | `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0` |
| `actions/setup-python` | `v6.3.0` | `ece7cb06caefa5fff74198d8649806c4678c61a1` |
| `actions/setup-node` | `v7.0.0` | `820762786026740c76f36085b0efc47a31fe5020` |
| `gitleaks/gitleaks-action` | dereferenced `v2` | `ff98106e4c7b2bc287b24eaf42907196329070c7` |

The commits were resolved from the canonical repositories with `git ls-remote`. A full SHA makes
the reference immutable; it does not replace source review or future update checks.

## Sources

- GitHub, [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).
- npm, [npx command](https://docs.npmjs.com/cli/commands/npx/).
- Astral, [uv resolution and dependency cooldowns](https://docs.astral.sh/uv/concepts/resolution/).
- Liu et al., [Trust Me, Import This](https://arxiv.org/abs/2605.09594), 2026.
- Saha et al., [Under the Hood of SKILL.md](https://arxiv.org/abs/2605.11418), 2026.
- Guo et al., [MalSkillBench](https://arxiv.org/abs/2606.07131), 2026.
