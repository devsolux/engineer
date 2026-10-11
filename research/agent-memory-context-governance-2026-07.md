# Durable agent memory and context governance research

**Date:** 2026-07-15  
**Feeds:** `references/agent-memory.md`, `scripts/validate-agent-memory.py`

## Findings encoded

- Context is finite. Durable memory should preserve compact, high-signal state and retrieve it just
  in time instead of replaying an ever-growing transcript.
- Memory is a separate attack surface. Poisoned instructions, summaries, tool output, and peer-agent
  claims can persist across sessions, so admission needs provenance, trust, verification, scope,
  expiry, contradiction handling, and rollback.
- Access control precedes similarity ranking. Tenant, subject, purpose, status, and expiry filters
  are authorization constraints, not relevance features.
- Memory cannot inherit authority. A stored statement cannot approve a tool, expand permissions,
  change the current goal, or substitute for the live authorization system.
- Privacy rights extend to derived representations. Delete and rectification procedures must address
  content, embeddings, retrieval caches, summaries, replicas, and resurrection tests.
- Project-scoped memory boundaries are a useful product pattern, but the implementation still needs
  explicit isolation and lifecycle evidence.

## Primary sources

- Anthropic, [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- OWASP GenAI Security Project, [Memory Is a Feature. It Is Also an Attack Surface](https://genai.owasp.org/2026/05/13/memory-is-a-feature-it-is-also-an-attack-surface/)
- OWASP, [Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- NIST, [AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- NIST, [Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- OpenAI, [Projects in ChatGPT](https://help.openai.com/en/articles/10169521)
- OpenAI, [Designing AI agents to resist prompt injection](https://openai.com/index/designing-agents-to-resist-prompt-injection/)

## Limits

The receipt validates declared evidence. It does not connect to a live store, prove that RLS ran,
or prove physical deletion from every backup. Production assurance still needs store-specific tests,
audit logs, restore drills, and independent review.
