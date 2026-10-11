# External agent-method research - 2026-07

**Scope**: capabilities in `karpathy/autoresearch`, `garrytan/gstack`, and `obra/superpowers` that
should influence Engineer without turning it into another suite.

## Sources reviewed

- Karpathy autoresearch repository, README, and `program.md`:
  <https://github.com/karpathy/autoresearch>
- gstack repository and current README workflow/catalog:
  <https://github.com/garrytan/gstack>
- Superpowers repository and current README methodology/catalog:
  <https://github.com/obra/superpowers>

These are primary project sources. Popularity and author claims are not behavioral proof.

## Comparison and decision

| Source | Distinct method | Engineer decision |
|---|---|---|
| autoresearch | one mutable file, protected evaluator, fixed wall-time metric, baseline-first autonomous keep/discard loop, trial ledger, simplicity preference | Generalize as bounded autonomous experimentation; add guardrails for uncertainty, holdout, resource accounting, dirty trees, kill switches, and normal production gates |
| gstack | role-oriented product pipeline, live browser QA, security/review/ship tools, DevEx plan-to-live "boomerang," retrospective and learning surfaces | Keep gstack as an optional executor; add native Developer Experience engineering because it is a product-engineering domain, not a runtime duplicate |
| Superpowers | automatic workflow activation, design approval, bite-sized plans, red/green TDD, isolated task workers, ordered spec then quality review, verification before completion | Retain Engineer's proportional plan and orchestration contracts; strengthen ordered review and behavior-change red/green guidance without forcing subagents or TDD where they add no evidence |

## Autoresearch findings

The small system works because it confines the search: `prepare.py` and evaluation stay fixed,
`train.py` is the sole mutable surface, each run receives the same five-minute training budget, and
`results.tsv` records keep/discard/crash outcomes. The branch advances only on improvement. The metric is
hardware-specific under a fixed wall-time budget, so results across machines are not directly comparable.

Literal indefinite looping and reset-based discard are unsafe defaults for general repositories. Engineer
adds a total deadline, spend/resource/disk limits, no-progress and crash circuits, reversible worktrees,
protected holdout, metric-gaming review, uncertainty, and independent promotion. The user may authorize a
long-running goal without granting new external mutations or unlimited resources.

## gstack findings

Most gstack value already has an explicit Engineer composition boundary: browser/QA, security, review,
debugging, plan review, ship, canary, and destructive-operation guards remain optional specialist passes.
Copying its runtime or command catalog would create competing owners.

The missing native domain was Developer Experience engineering. gstack separates predicted DX from a
live onboarding attempt and measures time to a working result. Engineer generalizes that to SDK, API, CLI,
plugin, integration, and contributor journeys, with clean-environment replay, error recovery, privacy,
production next steps, and regression promotion.

## Superpowers findings

Existing Engineer coverage includes intent routing, plan artifacts, worktrees, bounded orchestration, systematic debugging,
maker/checker separation, completion receipts, and anti-overengineering. Superpowers reinforces three
useful details:

- validate behavior changes with a failing test or reproducible failing check before the fix when
  feasible;
- perform spec/acceptance review before code-quality review so style cannot mask missing behavior;
- use fresh isolated workers only for independent tasks, then verify their output at a deterministic join.

The integration does not adopt mandatory subagents, deletion of every pre-test implementation, or full planning
ceremony for tiny work. Its proportionality and authority gates remain binding.

## Resulting capability boundary

This release gains autonomous experimentation and Developer Experience knowledge, plus sharper review/TDD
rules. autoresearch remains a specialized training implementation, gstack remains an optional execution
suite, and Superpowers remains a separate methodology/plugin. Third-party installation still requires
the skill supply-chain admission workflow.
