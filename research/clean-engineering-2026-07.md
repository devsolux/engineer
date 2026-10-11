# Clean engineering, SOLID, and anti-overengineering research — 2026-07

**Scope**: proportional architecture and code review for Engineer's default SaaS stack.
**Decision**: encode a plan-time proportionality receipt; do not turn subjective style into a noisy code scanner.

## Primary findings

1. Google Engineering Practices defines review success as improving overall code health while still
   allowing progress; it explicitly rejects perfection as the merge standard. This supports bounded,
   incremental review rather than speculative cleanup bundled into feature work.
2. Google SRE treats simplicity as a reliability prerequisite and separates essential complexity from
   accidental complexity. Dead code, grab-bag components, and architecture/process bloat are system
   risks, not merely readability issues.
3. AWS Well-Architected recommends frequent small reversible changes. Reversibility is therefore an
   architecture input: costly or irreversible choices need stronger evidence, a decision record, and
   a rollback or migration path.
4. SOLID originated as design principles for resisting rigidity, fragility, and immobility. Applying
   the acronym mechanically can recreate those problems through needless interfaces and layers.
   Engineer applies each principle only at a named boundary with observed change pressure.
5. Simplicity does not mean removing essential controls. Security, privacy, accessibility, payment
   integrity, idempotency, and recovery address present risks. The correct target is the simplest
   implementation that preserves those boundaries.

## Engineer operationalization

- Require present need and repository/requirement evidence before architecture expansion.
- Make the simplest viable design explicit and record why larger alternatives were rejected.
- Inventory new abstractions and runtime components; both spend complexity budget.
- Require SOLID justification for every new abstraction: principle, observed pressure, boundary.
- Require a simpler rejected option before adding a runtime component.
- Classify reversibility; costly/irreversible choices require a decision record.
- Prefer Rule of Three, modular monoliths, direct dependencies, existing primitives, and measured
  optimization. Exceptions require current evidence, not possible future scale.
- Keep deterministic validation structural. Do not infer overengineering from file length, class count,
  interface count, or dependency count alone; those metrics need human/contextual review.

## Sources

- Google Engineering Practices, review standard: <https://google.github.io/eng-practices/review/reviewer/standard.html>
- Google SRE Book, operational simplicity: <https://sre.google/sre-book/simplicity/>
- Google SRE Workbook, simplicity: <https://sre.google/workbook/simplicity/>
- AWS Well-Architected, operational excellence and reversible changes: <https://docs.aws.amazon.com/wellarchitected/latest/framework/ops-design-principles.html>
- Robert C. Martin, *Design Principles and Design Patterns* (original SOLID source, archived): <https://web.archive.org/web/20191116231621/http://www.objectmentor.com/resources/articles/Principles_and_Patterns.pdf>
