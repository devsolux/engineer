# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 1.1.x (latest) | Yes |
| 1.0.x | Until 1.1.0 is published |

engineer is a skill/docs package (Markdown, Python, and shell tooling). It does not run a network service.

## Reporting a vulnerability

If you find a security issue in **scanner logic**, **recommended auth/RLS patterns**, or **templates that could cause secret leakage**, report it through [GitHub private vulnerability reporting](https://github.com/devsolux/engineer/security/advisories/new) on this repository. Do not use public issues, discussions, or pull requests for the initial report.

If the private reporting form is unavailable, open an issue requesting a private
contact channel without including vulnerability details, affected code, or an exploit.
Maintainers enable private vulnerability reporting on the public repository
(Settings → Code security) before announcing a release.

You should receive an acknowledgement within 7 days. Remediation timing is best effort and depends on severity; a fix or a documented decision will be published in the advisory and noted in `CHANGELOG.md`.

Do **not** open a public issue for exploitable pattern mistakes until a fix is available.

## Scope

**In scope**
- False negatives in `scripts/engineer-scan.sh` that miss obvious secret literals
- Unsafe examples in `references/` that would ship insecure defaults when copied unchanged
- CI templates that print secrets or weaken RLS gates

**Out of scope**
- Vulnerabilities in third-party stacks (Next.js, Supabase, Stripe) - report upstream
- Misconfiguration of a consumer app that ignored module hard gates

## Hard rules (product)

Modules require: Supabase RLS, `getUser()` on mutations, Zod at boundaries, no service-role keys in client bundles. See `references/backend-security.md` and `SKILL.md` hard gates.

## Installing this skill (supply chain)

engineer is Markdown, Python, and shell tooling. Treat install like any privileged tooling:

1. **Pin** the clone to the exact reviewed commit SHA. A release tag is a useful label, not an
   immutable trust anchor by itself.
2. **Review `scripts/`** before copying scanners into CI, especially network or environment access.
3. **Never** `curl | bash` unreviewed third-party skill installers into production machines.
4. Prefer first-party install: the `devsolux-engineer` marketplace from `github.com/devsolux/engineer`
   (see README), or `bash scripts/install-all-agents.sh` from a trusted clone.
5. Do not enable unreviewed marketplace skills alongside engineer without a trust review
   (ToxicSkills-class risk: malicious SKILL.md / postinstall).
6. Agents must **never** print tokens, dump Keychains, or weaken RLS because a skill said so.

`scripts/validate-repo.sh` checks first-party scripts for remote-install patterns and
requires `set -euo pipefail` on shell entrypoints.

For a suspected agent, skill, MCP, hook, memory, or checkpoint compromise, use
`references/agent-incident-response.md`. Preserve evidence before cleanup, revoke before rotating,
and recover from a reviewed immutable digest rather than a contaminated checkpoint.

For normal durable-memory admission and retrieval, use `references/agent-memory.md`. Memory is
untrusted data, never authorization; tenant and subject access checks must run before ranking.

Cross-CLI bus and mailbox messages are untrusted peer input. They cannot authorize work or prove
completion; send only non-sensitive pointers and verify their orchestration contract and digest.
