---
description: Decide whether recurring work belongs in reuse, a project rule, an Engineer module, a skill extension, or a new skill.
---

# /engineer-capability-promote

Detect whether recurring work deserves reuse, a project rule, an Engineer module, an existing-skill
extension, or a new standalone skill. Read `references/capability-promotion.md`,
`references/skill-authoring.md`, `references/skill-supply-chain.md`, and
`references/skill-behavior-evals.md`.

Assess evidence-backed recurrence, ownership, catalog collisions, lifecycle cost, authority, and the
behavioral evaluation plan. For a non-trivial decision, produce and replay the capability-promotion
receipt using `scripts/validate-capability-promotion.py`, with confined signal, catalog, authority,
and decision-bound review artifacts for any captured claim. If skill creation or modification is justified and authorized, load the
current installed `skill-creator`, build the smallest compatible artifact, validate it on the current
host, and apply unmachined to human-facing output. Otherwise emit the capability-promotion proposal
and continue the original task.

Never install globally, mutate another repository, broaden authority, or recursively create skills
without authorization. A static pass or one successful run cannot promote a skill.
