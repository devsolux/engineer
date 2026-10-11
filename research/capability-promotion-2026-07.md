# Capability-to-skill promotion research

**Date**: 2026-07-16

## Decision

Engineer should automatically **detect and assess** reusable capability candidates. It should create or
modify a skill only when the capability passes an ownership and lifecycle gate and the current task
authorizes that destination. This preserves the convenience of automatic skill selection without
turning incidental work into catalog growth.

Current primary guidance converges on five points:

1. Skills fit repeatable, specialized, on-demand workflows; short repository-wide rules belong in
   repository instructions.
2. Progressive disclosure makes skills efficient, but every enabled description still competes for
   routing and coexistence.
3. A production candidate needs positive, negative, ambiguous, isolation, coexistence,
   instruction-following, output-quality, and safety evaluation.
4. Creation and deployment are separate transitions. Security review, ownership, versioning,
   monitoring, rollback, and deprecation are lifecycle requirements.
5. Automatic relevance selection makes narrow descriptions and non-trigger cases essential. Format
   validation alone does not prove correct activation or useful behavior across hosts and models.

The implementation belongs in Engineer as a meta-routing capability because Engineer already owns
project detection, composition, skill authoring, supply-chain admission, behavioral evaluation, and
telemetry. Generated domain skills remain separate owners; Engineer must not absorb their expertise or
become a recursive skill factory.

The v1 receipt makes the decision deterministic where structure can be checked. It requires exact
comparison of every owner class, distinct evidence identities, a Engineer catalog row, selected-option
fit and routing safety, complete behavioral case categories, authority for apply/install, independent
review, and lifecycle ownership. It does not pretend hashes or declared roles prove semantic
recurrence, catalog completeness, reviewer identity, behavioral quality, or authorization truth.

The captured form therefore binds separate signal, catalog, authority, and review artifacts rather
than trusting `receipt_kind`. Review includes the canonical decision hash, preventing a decision from
changing after approval. Lexical confinement, digest replay, and symlink rejection preserve local
artifact identity. Authentication and semantic truth remain explicitly outside this local receipt.

## Sources

- https://help.openai.com/en/articles/20001066-skills-in-chatgpt
- https://openai.com/academy/skills/
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise
- https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills
