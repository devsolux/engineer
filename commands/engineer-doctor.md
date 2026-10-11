---
description: Verify engineer installation identity, host surfaces, and evaluation readiness without reading secrets
---

# /engineer-doctor

Load `references/coding-agent-hosts.md` and run:

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
python3 "$ENGINEER/scripts/engineer-doctor.py" --hosts auto --json --strict
```

Native skill links and marketplace plugin copies (`engineer@devsolux-engineer` in the Claude or
Codex plugin cache) both count as installations. Pass `--hosts claude,codex` to check specific hosts.

Report canonical version/commit/hash, each host installation mode and status, secret-safe host
capabilities, and evaluation readiness. Never print credential values or treat installation identity
as proof of skill activation, authorization, sandbox enforcement, or behavioral quality.
