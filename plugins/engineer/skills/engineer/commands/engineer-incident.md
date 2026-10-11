---
description: Contain and recover a compromised agent system with validated evidence.
---

# /engineer-incident

Load `references/agent-incident-response.md`, `references/agent-red-teaming.md`, and
`references/ai-security.md`.

1. Declare severity, commander, affected trust boundaries, and uncertainty. Stop unsafe autonomous
   actions without destroying evidence.
2. Preserve volatile traces and state, hash artifacts, and record chain of custody.
3. Contain: isolate, deny egress where appropriate, disable agent capabilities and persistence,
   revoke sessions/credentials, and assess every blast-radius category.
4. Hunt agent-specific persistence; eradicate compromised state; invalidate poisoned memory and
   checkpoints; rebuild from an immutable known-good digest.
5. Recover read-only/canary first with monitoring and explicit exit criteria. Recontain on a new
   indicator.
6. Add malicious and benign-control regressions, make notification decisions, and obtain an
   independent closure review.
7. Emit and validate `agent-incident.json`.

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
python3 "$ENGINEER/scripts/validate-agent-incident.py" agent-incident.json --json
```

Do not claim forensic certainty, clean recovery, or closure from the template or validator alone.
