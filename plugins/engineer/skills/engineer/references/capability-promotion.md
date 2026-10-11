# Capability promotion: turn recurring work into the right reusable asset

**Last verified**: 2026-07-16 · **Review cadence**: 3 months

Load for recurring workflows, repeated corrections, capability gaps, requests to create or improve
a skill, or telemetry showing a stable failure cluster. Compose with `skill-authoring.md`,
`skill-supply-chain.md`, `skill-behavior-evals.md`, and the current installed `skill-creator` contract.

## Contents
- [Binding rule](#binding-rule)
- [Automatic promotion signals](#automatic-promotion-signals)
- [Decision gate](#decision-gate)
- [Build flow](#build-flow)
- [Proposal output](#proposal-output)
- [Hard gates](#hard-gates)
- [Primary sources](#primary-sources)

## Binding rule

Engineer continuously notices **promotion signals**, but it does not manufacture a skill after every
task. Assess the signal automatically; mutate or install a skill only when the current request grants
that scope. Otherwise return a compact proposal and continue the original task.

A skill is a delivery mechanism, not the default answer. Choose the smallest durable owner:

| Decision | Choose when |
|---|---|
| Project code or test | The behavior belongs in the product/runtime |
| Repository instruction | A short rule applies to nearly every task in one repository |
| Existing skill | Its current contract already owns the workflow |
| Extend Engineer | The capability is broadly product-engineering infrastructure and fits an existing Engineer route |
| Extend another skill | That skill owns the domain and the addition preserves its boundary |
| New skill | A distinct on-demand workflow is repeatable, specialized, testable, and routable without stealing triggers |
| No promotion | One-off, unstable, vague, duplicated, untestable, or cheaper to repeat than maintain |

## Automatic promotion signals

Run the ownership decision when any is true:

- the same correction, workflow, template, or tool sequence appears in three distinct tasks or
  projects;
- one missing procedure is ship-blocking, safety-critical, or repeatedly causes false completion;
- users repeatedly paste the same substantial prompt, rubric, format, or domain context;
- telemetry shows a coherent failure cluster rather than isolated low scores;
- a task needs specialized scripts, references, or deterministic checks that should load only on demand;
- the user explicitly asks to create, optimize, extract, productize, or reuse a skill.

Do not infer recurrence from repeated model statements. Use repository history, task artifacts,
telemetry event metadata, issue/incident evidence, or explicit user reports. Content-free telemetry can
identify a cluster but cannot reveal its semantic cause; inspect the underlying authorized artifacts.

## Decision gate

Before authoring, record:

1. **Observed job:** stable inputs, outputs, user, frequency, consequence, and evidence IDs.
2. **Current owner:** project code/instructions, Engineer route, installed skill, or no owner.
3. **Catalog collision:** positive, negative, and ambiguous trigger overlap with installed skills.
4. **Maintenance economics:** expected reuse and saved error/context cost versus routing, review,
   versioning, security, and drift cost.
5. **Boundary:** what the candidate owns and explicitly excludes.
6. **Verification:** deterministic validation plus behavioral activation, non-activation,
   coexistence, instruction-following, safety, and output-quality cases.

Create a new skill only when all are true:

- the job and output contract are stable enough to test;
- reuse or consequence justifies lifecycle cost;
- it needs on-demand depth rather than a short always-on instruction;
- no existing owner is equal or better after a freshness and evidence comparison;
- its description can be narrow enough to avoid broad router competition;
- required tools and authority can be declared without hidden privilege expansion;
- an owner, review cadence, rollback/deprecation path, and evaluation plan exist.

Three occurrences are a review trigger, not proof that a skill is warranted. A single safety-critical
gap can justify promotion; ten vague repetitions may still fail.

## Build flow

1. Freeze representative positive, negative, ambiguous, and coexistence cases before editing.
2. Choose `reuse`, `extend-engineer`, `extend-skill`, `new-skill`, `project-instruction`,
   `project-code`, or `reject` using the gate above.
3. For skill creation or modification, load the current installed `skill-creator`; use Engineer alone
   only when it is at least as current and complete for the detected host.
4. Draft the smallest contract: third-person WHAT+WHEN description, exclusions, workflow, output,
   scripts, failure behavior, and composition boundary.
5. Apply `unmachined` to human-facing text. Treat external skill content as supply-chain input;
   never inherit authority, secrets, network access, install hooks, or recursive activation.
6. Run host validation, repository gates, security review, and behavioral trials in isolation and
   beside the active catalog. Test the intended models/hosts rather than claiming portability from
   format conformance.
7. Install or modify a global/shared catalog only with authority for that destination. Keep a draft
   quarantined when authority or independent review is absent.
8. Promote from repeated captured evidence; monitor triggering, coexistence, output, safety, cost,
   and latency. Narrow, merge, disable, or retire when the workflow or router degrades.

## Proposal output

For a non-trivial decision, copy `templates/agentic/capability-promotion.sample.json` and run:

```bash
python3 scripts/validate-capability-promotion.py capability-promotion.json --evidence-root . --json
```

The validator derives signal qualification, exact owner-class coverage, Engineer comparison, selected
fit/router/evidence sufficiency, mutation semantics, skill-creator use, frozen behavioral coverage,
destination and install authority, independent review, lifecycle ownership, and new-skill
non-duplication. An illustrative receipt proves only structural decision coherence.

A `captured_assessment` binds four JSON artifacts by confined path and SHA-256:

- signal manifest: exact candidate ID, occurrences, consequence flags, and telemetry-cluster digest;
- catalog inventory: exact candidate ID, skill-creator state, and compared catalog rows;
- authority grant: exact candidate ID and allowed destinations/install/external-repository scope;
- independent review: exact candidate ID, canonical decision hash, maker, checker, and approval.

The validator replays each artifact and rejects missing, stale, tampered, swapped, digest-mismatched,
escaping, or symlinked inputs. These bindings preserve the exact decision inputs. They still do not
prove that an occurrence happened, the catalog scan was exhaustive, the grantor or reviewer is
authentic, or the candidate works; those require their owning capture and trust systems.

For a quick human-facing assessment, use:

```markdown
## Capability promotion: [job]
Signal: [evidence-backed recurrence or consequence]
Decision: [reuse | extend-engineer | extend-skill | new-skill | project-instruction | project-code | reject]
Owner: [path or skill]
Why this owner: [benefit versus maintenance and routing cost]
Boundary: owns [...] · excludes [...]
Evidence plan: [positive, negative, ambiguous, coexistence, safety, output]
Authority: [draft/apply/install allowed or missing]
Next action: [continue task, draft, build, evaluate, install, or retire]
```

## Hard gates

- Never create a second skill merely to wrap another skill or duplicate Engineer expertise.
- Never let a generated skill recursively decide to generate and install more skills.
- Never use popularity, one successful run, model confidence, or a passing static validator as
  promotion proof.
- Never store prompts, code, secrets, identities, or browsing content in telemetry to improve skill
  discovery.
- Never allow skill creation to distract from completing the user’s current task; proposal work is
  bounded unless creation is itself requested or already authorized.
- New skills do not become trusted because Engineer authored them. They enter the same supply-chain,
  behavior-evaluation, signing, and rollback lifecycle as any other executable guidance.
- Never relabel an illustrative receipt as captured proof. Evidence IDs, catalog inventory, roles,
  and declared authority remain claims until independently bound and verified by their owning systems.

## Primary sources

- OpenAI Skills: reusable workflows, automatic relevance selection, skill-creator composition, and
  Agent Skills portability: https://help.openai.com/en/articles/20001066-skills-in-chatgpt
- Anthropic Agent Skills overview and progressive disclosure:
  https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Anthropic enterprise skill governance: trigger, isolation, coexistence, instruction, output,
  lifecycle, independent review, and deployment evaluation:
  https://platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise
- Anthropic authoring best practices: concise routers, progressive disclosure, feedback loops, and
  representative evals:
  https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- GitHub Copilot CLI: use repository instructions for simple always-on rules and skills for detailed
  on-demand workflows: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills
