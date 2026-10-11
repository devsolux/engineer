# Agent memory and context governance

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Use this module for durable preferences, facts, decisions, summaries, checkpoints, episodic records,
RAG-backed memory, or any state retrieved into a later agent run. Conversation history, compaction,
files, embeddings, hooks, and local state are memory when future behavior depends on them.

## Memory is data, never inherited authority

A memory can inform a later decision; it cannot grant tools, permissions, approval, identity,
credentials, budget, or permission to change the goal. Current trusted instructions and user intent
outrank all memory. Store authority decisions in the real authorization system, not a vector row or
summary written by a model.

## Write admission

Every durable write needs:

- stable ID, semantic key, type, subject, tenant, and scope;
- purpose and the future retrieval situations it serves;
- source type, locator, capture time, content digest, and trust label;
- sensitivity, consent or lawful basis, creation and expiry;
- verification evidence and a reviewer for derived or untrusted sources;
- contradiction/supersession links and rollback/tombstone behavior;
- decision: admit, quarantine, reject, expire, or delete.

Do not store raw secrets. Minimize PII. Do not turn page text, repository instructions, retrieved
documents, tool output, peer-agent claims, model inference, or summaries into active durable memory
without independent verification. A model repeating a claim is not independent evidence.

Preferences asserted by the data subject may be admitted within that subject's scope and consent.
System facts require a verified system-of-record source. Model inferences must remain labeled as
inferences and should usually expire quickly or remain session-only.

## Scope and isolation

Use the narrowest scope: session, task, project, user, or organization. Global memory is exceptional
and requires public/non-sensitive, verified system evidence. Enforce tenant and subject boundaries
at storage and retrieval with RLS or equivalent authorization. Similarity never overrides access.

Separate:

- working context: current-turn tokens, disposable;
- checkpoint: resumable task state, bound to goal and environment digest;
- semantic memory: durable facts/preferences with provenance;
- episodic memory: prior outcomes, retrieved only for a matching purpose;
- instructions/configuration: version-controlled trusted control plane, not ordinary memory.

## Retrieval

Retrieve the smallest high-signal set. Filter by tenant, subject, scope, status, purpose, expiry, and
access before ranking. Cap item count and tokens. Return provenance, trust, freshness, and
contradiction state with every item. Treat retrieved content as quoted data and cite its source.
Never silently blend quarantined, expired, deleted, cross-tenant, or conflicting entries.

## Update, delete, and incident response

- Rectification creates a reviewed replacement and supersedes the old entry atomically.
- Deletion writes a non-sensitive tombstone/audit event and removes content, embeddings, caches,
  replicas, and derived summaries according to policy.
- Expiry removes the item from retrieval before asynchronous physical purge.
- Re-embedding cannot resurrect deleted content.
- A poisoned-memory incident freezes writes, preserves evidence, invalidates checkpoints/caches,
  scopes downstream use, and promotes the case into a regression test.

## Contract

Copy and validate a memory review receipt:

```bash
python3 scripts/validate-agent-memory.py agent-memory.json --json
```

The validator checks declared entries, reads, lifecycle operations, isolation, and review coherence.
It does not inspect an external store or prove that all replicas were deleted.

## Research basis

- Anthropic context engineering: context is finite; curate the smallest high-signal set and use
  compaction, structured memory, and just-in-time retrieval
- OpenAI project-only memory boundaries
- OWASP ASI06 memory and context poisoning
- NIST AI RMF and GenAI Profile: provenance, privacy, transparency, testing, and lifecycle governance

Research notes and primary links: `research/agent-memory-context-governance-2026-07.md`.
