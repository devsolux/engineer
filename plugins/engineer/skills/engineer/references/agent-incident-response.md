# Agent incident response

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Use this module after suspected prompt injection, poisoned context or memory, tool/MCP abuse,
credential exposure, unauthorized writes, agent-to-agent propagation, or compromise of a skill,
hook, browser profile, checkpoint, CI job, or automation identity. It complements prevention and
red-team modules; it is not an offensive playbook.

## Non-negotiable order

1. **Declare and bound** - name an incident commander, severity, clocks, affected identities,
   environments, agents, tools, repositories, data, external side effects, and current uncertainty.
2. **Preserve before cleanup** - capture volatile traces, tool arguments/results, process and network
   observations, configuration, hashes, audit logs, memory/checkpoint identifiers, and a monotonic
   chain of custody. Store no raw secrets in the receipt.
3. **Contain proportionately** - freeze autonomous loops and outbound actions; deny egress where
   safe; isolate workspaces and browser profiles; disable affected skills, hooks, MCP servers,
   schedules, CI jobs, and delegation; revoke sessions and credentials. Record evidence for each
   action. Bulk revocation is high impact and needs an explicit blast-radius decision.
4. **Scope repeatedly** - assess credentials, repositories, customer or internal data, production,
   money, external messages/writes, and downstream agents. New indicators return the incident to
   analysis and containment.
5. **Hunt persistence** - inspect skills/plugins, system and repo instructions, hooks/startup files,
   MCP configuration, scheduled tasks, CI/CD, browser extensions/profiles, RAG stores, durable
   memory, caches, checkpoints, cloud tasks, delegated agents, and generated credentials.
6. **Eradicate from the lowest compromised layer** - remove malicious state, fix the source-to-sink
   boundary, revoke first and rotate secrets in dependency order, invalidate poisoned memory and
   checkpoints, and rebuild from a reviewed immutable digest. Never restore “latest” or reuse a
   contaminated checkpoint merely because malware scanning is clean.
7. **Recover in stages** - restore least privilege, begin read-only or canary, monitor tool calls and
   side effects, prove exit criteria, then widen access. Recontain on any new indicator.
8. **Learn without laundering the incident** - record root cause and uncertainty, make required
   user/legal/vendor notification decisions, add the malicious case plus a benign control to the
   regression bank, and independently review closure.

## Agent-specific evidence

Capture exact prompt/context provenance, instruction precedence, retrieved documents, model and
host version, enabled skills/MCP/tools, approvals, tool arguments, outputs, handoffs, checkpoint and
memory digests, network destinations, external writes, and grader decisions. Treat model prose as a
claim; traces and end state are evidence. Preserve originals read-only and analyze copies.

## Closure gate

An incident may close only when containment, blast-radius assessment, persistence audit,
eradication, known-good staged recovery, monitoring, notification decisions, and regression tests
are evidenced; unresolved risks are empty; and incident commander and independent evidence
reviewer are different people. An illustrative template can never authorize closure.

Copy `templates/agentic/agent-incident.sample.json`, replace illustrative data with captured
evidence, then run:

```bash
python3 scripts/validate-agent-incident.py agent-incident.json --json
```

The validator checks receipt coherence, not whether a system is actually clean.

## Dev-machine / supply-chain appendix

When the incident is a compromised dependency, lifecycle script, cloned template, or dropper
that ran on a developer/CI machine, instantiate the order above with four specializations.
Install/build code runs with the **full ambient credential set**, so assume total exposure.

**Ambient-credential rotation order.** Revoke *live access first* - log out all GitHub/cloud/
browser sessions and revoke OAuth grants; a password reset does **not** kill a stolen session
cookie. Then rotate in dependency order (identity provider, then cloud admin, then source-
control PAT, then leaf secrets), regenerate SSH keys, and invalidate cookies. Rotate the whole
set, not only what you can prove leaked - the payload had all of it. Named 2025-2026 TTPs:
Chrome App-Bound-Encryption cookie bypass (LummaC2/C4 Bomb), the npm token-theft-and-republish
loop (Shai-Hulud), and AI-CLI weaponization with skip-permission flags (s1ngularity reached AWS
admin in ~72h). Credential stores to rotate: the npm, cloud, and SSH config stores, `.env`
files, CI environment secrets, and the browser cookie database.

**Persistence spot inventory (JS/dev workflow).** `.git/hooks` + `.husky`, shell rc files,
global npm packages (`npm ls -g`), IDE/agent config (`.vscode`/`.cursor`/rules), `.mcp.json`,
`.github/workflows` + CI secrets, and cron/launchd.

**IOC-hunt checklist.** Build/postinstall reads of credential stores; install-time egress to
non-registry hosts or fresh public repos; new PATs/OAuth grants/SSH keys; auto-republished npm
versions; an AI-CLI invoked with `--dangerously-skip-permissions`/`--yolo`/`--trust-all-tools`.
Preserve the dropper, `.env`, egress destinations, and hashes read-only before cleanup, and
rebuild from a reviewed immutable digest - discard the lockfile/checkpoint present during the
compromise. For the dropper taxonomy and detection tiers, see `malware-detection.md`.

## Sources

- NIST SP 800-61 Rev. 3, incident response across CSF 2.0 functions (2025)
- CISA Federal Government Cybersecurity Incident and Vulnerability Response Playbooks
- GitHub, “Responding to a security incident” and credential revocation guidance
- OWASP Top 10 for Agentic Applications 2026, including cascading failures
- Nx s1ngularity (2025-08) and Shai-Hulud / Shai-Hulud 2.0 (2025-09/11) npm worm campaigns - credential-stealer TTPs and token-theft-and-republish loop (vendor magnitudes differ)
- Chrome App-Bound-Encryption cookie-theft bypass (2025, LummaC2 / C4 Bomb)
