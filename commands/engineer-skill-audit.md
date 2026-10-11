---
description: Audit a third-party skill or plugin before installation and emit a validated admission receipt.
---

# /engineer-skill-audit

Load `references/skill-supply-chain.md`, `references/ai-security.md`, and
`references/agent-red-teaming.md`.

1. Keep the candidate quarantined and resolve its canonical owner plus immutable revision.
2. Inventory every file, executable bit, dependency, permission, hook, MCP server, endpoint, model,
   capability, and secret boundary.
3. Review instructions and code jointly for dependency steering, hidden behavior, obfuscation,
   credential access, persistence, telemetry, approval bypass, and sandbox weakening.
4. Run static checks and authorized disposable sandbox cases using synthetic secrets and denied or
   simulated egress. Include benign controls and adversarial triggers.
5. Emit `skill-admission.json` from `templates/agentic/skill-admission.sample.json` and validate it.
6. Report `reject`, `quarantine`, or `trust` with unresolved risks, rollback, owner, and review date.

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
python3 "$ENGINEER/scripts/validate-skill-admission.py" skill-admission.json --json
```

Never install into a trusted host merely because a scanner, marketplace, signature, or model review
passed. Installation remains an explicit user-authorized action after admission.
