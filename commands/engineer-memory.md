---
description: Review durable agent memory writes, retrieval, scope, expiry, and deletion.
---

# /engineer-memory

Load `references/agent-memory.md`, `references/agentic-engineering.md`,
`references/ai-security.md`, and `references/compliance-privacy.md` when personal data is involved.

1. Inventory every durable memory surface, tenant/subject boundary, source, sink, cache, embedding,
   checkpoint, and replica.
2. Separate working context, checkpoint, fact, preference, decision, episode, and trusted
   configuration. Memory never carries authority.
3. Review writes for provenance, sensitivity, purpose, consent, verification, expiry,
   contradiction, supersession, and rollback.
4. Review reads for access-before-ranking, purpose/scope match, freshness, token/item budgets,
   citations, and exclusion of quarantined, expired, deleted, conflicting, or cross-tenant state.
5. Verify rectification, export, expiry, deletion, derived-cache purge, and incident invalidation.
6. Emit and validate `agent-memory.json` before admission or release.

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
python3 "$ENGINEER/scripts/validate-agent-memory.py" agent-memory.json --json
```

Do not infer that a valid receipt proves the external store or every replica obeyed it.

