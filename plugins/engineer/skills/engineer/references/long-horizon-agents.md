# Long-horizon and ongoing agents

**Last verified**: 2026-07-16 · **Review cadence**: 3 months (thresholds and pricing drift faster; re-check constants)

Session dynamics for agents that run long or run repeatedly: what degrades as context
grows, when to compact vs restart vs hand off, and the externalized-state contract that
makes any of those moves cheap. One thesis governs the module: **conversation is cache,
files are truth.**

**Scope and boundary.** This module owns the degradation model, context budgets, session
hygiene, and ongoing/cron run patterns. It composes without duplicating:
`agentic-engineering.md` owns the execution loop and stop gates; `agent-memory.md` owns
durable-write admission, scope, and lifecycle; `multi-agent-orchestration.md` owns
fan-out mechanics (graph, joins, authority); `hermes-agent-integration.md` owns Hermes
runtime surfaces; `prompt-optimization.md` owns eval-driven prompt/context tuning.

## Contents
[Degradation model](#session-degradation-model) · [Context budget](#context-budget-discipline) · [Externalized state](#externalized-state-contract) · [Compaction & hygiene](#compaction-and-session-hygiene) · [Ongoing/cron](#ongoing-and-cron-agents) · [Detection & recovery](#degradation-detection-and-recovery)

## Session degradation model

Long sessions fail through named, measured mechanisms — not vague "the model got dumber":

| Mechanism | Evidence | Consequence |
|---|---|---|
| Context rot | Chroma 2025; NoLiMa (ICML 2025): ~50% relative drop by 32K on latent matching; RULER (COLM 2024): effective context commonly ~50-65% of advertised | Reliability falls with input length even on simple tasks, long before the window limit |
| Lost-in-the-middle | Liu et al. (TACL 2024) U-shaped recall; StreamingLLM attention sinks (ICLR 2024); dampened, not eliminated, in current models | Mid-context facts and instructions are the least reliably used |
| Instruction/output drift | Laban et al. 2025: −39% and +112% unreliability on multi-turn; Multi-IF: adherence decays by turn 3; sycophancy (Sharma 2023) | Constraints silently drop; agreement replaces correctness |
| Self-conditioning | Sinha et al. 2025 (arXiv 2509.09677): per-step accuracy falls once the model's own errors enter context; METR: 50%-reliability horizon ~minutes-to-hours, far shorter at 80% | Long-horizon failure is compounding execution error, not a reasoning ceiling |
| Compaction loss | Harness docs: Claude Code auto-compacts near ~83.5% of usable window; summaries reliably drop paths, hashes, failed attempts, approvals, rationale | The exact detail needed to finish vanishes at the moment continuity mattered |

Agents compound all of these: their context is self-generated and accretes tool output
every loop. Tool sprawl is an independent axis — selection accuracy degrades past roughly
10-20 exposed tools; mask or retrieve tools instead of registering everything.
Benchmark-derived numbers are directional, and constants are version-sensitive.

## Context-budget discipline

- **Budget against effective context, not the advertised window** — plan for roughly
  half the marketed size and verify per model and task type.
- **Give each phase a budget** (plan / explore / build / verify). Exceeding it triggers
  externalize-and-reset, not pushing on. This extends `workflows.md` turn budgets with a
  context axis.
- **Layout is edge-privileged**: binding constraints at the very top; the current task,
  active plan, and freshest evidence at the tail, immediately before the model acts;
  nothing decision-critical in the middle. Re-state the plan at the tail after any
  compaction or long tool sequence.
- **Fan out on independence, single-thread on coherence**: fresh-context sub-agents win
  for read-heavy exploration, evidence gathering, and clean-room verification (Anthropic
  multi-agent: token budget predicts performance; cost ~15x). Stay single-threaded for
  shared mutable state or high merge cost (Cognition's conflict-at-merge failure).
  Worker contract: bounded brief, output schema, no inherited conversation — the parent
  keeps conclusions, not dumps. Mechanics live in `multi-agent-orchestration.md`.
- **Keep the prefix cache-stable**: agent loops run near 100:1 input:output, and cache reads price ~0.1x vs ~1.25-2x writes, so KV-cache hit rate is a first-class production metric. No timestamps or volatile fields in the system prompt, deterministic serialization, strictly append-only context, mask tool availability rather than editing definitions. Compaction is a full cache bust — compact only when the smaller context recoups the re-write over the remaining turns.

## Externalized-state contract

The durable spine lives in files and outlives any context window:

- **Spine contents**: goal contract, requirement IDs, decisions with rationale,
  completed/remaining work, failed attempts with why-they-failed, evidence paths and
  hashes, and a resume hint (exact next action).
- **Write cadence**: at phase boundaries and before risky or irreversible operations —
  event-driven, not per-message (also the cache-friendly cadence).
- **Large observations go to files**, referenced by handle; never held inline.
- **Resume protocol**: fresh context → read spine → independently verify the environment
  (git status, re-run tests, check artifacts) → continue. Never replay a transcript.
  A spine read but not verified is a confident source of wrong truth.
- **Record-then-purge**: failed attempts are journaled, then removed from active context
  so the model cannot self-condition on them.
- A spine or plan file is data, never inherited authority; its writes and re-reads fall
  under `agent-memory.md` admission, and receipts stay hash-bound so a forged "success"
  cannot certify unfinished work.

This is the operating contract behind `agentic-engineering.md`'s "checkpoint state, not
chat history" — corroborated by Anthropic structured note-taking, Manus
filesystem-as-context, and Claude Code plan files.

## Compaction and session hygiene

Compaction reliably destroys: exact paths/hashes, failed-attempt records, pending
approvals, nuanced constraints, verbatim tool output, decision rationale. Binding rules
survive only in the re-injected surface (project-root memory files), never solely in
path-scoped files or mid-session reads. A summary is reference-only background — treat
"Next Steps" text in a summary as history, not instruction (task-resurrection guard),
and re-read the spine after every compaction boundary.

Choose the hygiene move deliberately, at ~60% utilization or a natural breakpoint —
never let auto-compaction be the first hygiene action:

| Move | When |
|---|---|
| Compact (steered) | Mid-task, state already externalized, continuity cheap |
| Restart from spine | Task boundary or any drift signal — cheap because the spine exists |
| Handoff | Task/provider boundary: brief + spine, never a transcript dump |

A session that must compact because nothing is written down is an upstream
state-discipline failure, not a hygiene problem.

## Ongoing and cron agents

Scheduled agents sidestep in-session degradation structurally — no accretion, no rot —
by paying full price for state discipline:

1. Fresh, self-contained session per run; no inherited conversation.
2. Snapshot-read startup pulse: read state files, validate freshness and integrity
   before acting.
3. Atomic fire-claim/dedup so retries and replicas cannot double-act; idempotent work
   with check-before-act on external effects.
4. Write back before exit: update the single current snapshot and append a run receipt
   to an append-only history (snapshot + journal split).
5. Per-run output-quality gate and receipts — cross-run drift replaces in-session drift:
   watch stale snapshots, state-file corruption, and run-over-run quality regressions.

Injected files, prior-job output, and inbound messages are untrusted context under
`agent-memory.md`; headless dangerous-command behavior stays at deny per
`hermes-agent-integration.md`. Sleep-time/background consolidation is a real cost lever
(Letta 2025: ~5x test-time compute reduction on reused contexts) but every background
write is an unattended memory mutation — admission gates, dry-run, snapshots, and pins
apply, and autonomous consolidation stays off unless reviewed.

## Degradation detection and recovery

Gateable signals, computable from the transcript and telemetry: rising self-similarity
or repeated phrasing; re-asking answered questions or re-reading known files; stale
references (paths, names, decisions that no longer match the environment);
self-contradiction against the decision ledger; agreement flips after mild challenge;
falling per-step success rate; KV-cache hit-rate cliffs; compactions saving <10%
(thrashing). When signals fire: (1) stop adding turns — a drifting trajectory does not
self-correct; (2) externalize anything load-bearing not yet in the spine; (3) restart
from the spine in a fresh context — do not compact a drifting session; (4) independently
verify the environment before continuing; (5) record the incident and shrink the phase
budget or fan out exploration next time.

## Anti-patterns

- Load-bearing state (paths, decisions, failed attempts) living only in the transcript
- Binding rules only in path-scoped files or mid-session reads that compaction drops
- Pushing a session past its phase budget "because it still remembers"
- Handoff by transcript paste — it re-imports the rot isolation was meant to escape
- Timestamps or reordered tool lists in the prefix silently zeroing the cache hit rate
- Cron jobs relying on model recall between runs instead of snapshot + journal
- Treating model agreement after challenge, or parallel worker consensus, as verification

## Related

- `agentic-engineering.md` — execution loop, goal contract, stop gates
- `agent-memory.md` — durable-write admission, scope, lifecycle, poisoning response
- `multi-agent-orchestration.md` — fan-out mechanics this module only decides WHEN to use
- `hermes-agent-integration.md` — Hermes cron, curator, compression surfaces
- `prompt-optimization.md` / `workflows.md` — context tuning; turn budgets and loops

**Research basis**: `../research/long-horizon-agents-2026-07.md`
