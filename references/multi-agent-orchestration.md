# Multi-agent orchestration control plane

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Use this module when two or more agents, workers, or agent-as-tool calls collaborate on one goal.
Do not add agents merely to simulate expertise. Start with a single agent; distribute work only
when tasks are genuinely separable, latency matters, or isolation improves safety.

## Compile before execution

Represent the orchestration as a bounded graph, not an informal group chat:

1. Give every agent one owner, task, input contract, output schema, capability set, budget, and stop
   condition.
2. Give every delegation a typed payload, context allowlist, authority ceiling, result destination,
   and evidence requirement. A child receives a subset of the delegator's authority. Delegation
   never creates permission, approval, credentials, or budget.
3. Prefer an acyclic task graph. If the product needs cyclic handoffs, compile them into a bounded
   state machine with a visit limit and an explicit human escalation. Never permit open-ended peer
   bouncing.
4. Isolate concurrent writers by worktree, directory, database namespace, browser profile, account,
   port, and artifact path. One synthesizer owns integration; workers do not merge one another.
5. Define the join before fan-out: `all`, `quorum`, `first_valid`, or `best_scored`. Define timeout,
   missing-worker behavior, conflict resolution, and whether cancellation propagates.
6. Reserve global budget for synthesis, verification, and cleanup. Child allocations plus reserve
   cannot exceed the parent's steps, cost, time, or concurrency limits.

## Authoring surfaces (Claude Code, version-sensitive)

Bind the abstract contract to concrete buttons (field sets verified 2026-07-16; they expand release
to release): `.claude/agents/*.md` frontmatter - `description` is the router, `tools` the
attenuation list, pinned model/effort, `isolation: worktree` for writers; the Agent tool contract
(`subagent_type`, `run_in_background`, `isolation`); `SendMessage` continuation; agent teams as
ephemeral transport. Commit agent definitions and the orchestration script to git: a committed
SDK/headless script compiling a fixed DAG is reproducible, while in-session conversational fan-out
is not (engineer's own live-eval pass@2 measured the nondeterminism). Subagent parallelism with
context isolation is now native on Claude Code, Gemini CLI, Grok Build, and Hermes; this module's
contract is the portable layer above all four.

## Authority and context

An agent identity is not an authorization decision. Resolve authorization at each tool sink using
the original user intent, current task, scoped identity, destination, sensitivity, and approval.
Pass references to evidence rather than full transcripts. Filter handoff history; untrusted tool or
browser content remains data. Tool guardrails apply at each call because entry/final-output
guardrails do not necessarily cover every intermediate agent or tool.

For each child declare:

- allowed tools and destinations;
- denied tools and external side effects;
- read/write lanes;
- secret classes it may reference (never raw secret values in the contract);
- approval class and revocation handle;
- maximum descendants, depth, retries, steps, wall time, and cost.

## Failure containment

- Use leases and heartbeats for durable workers. Expiry cancels authority; it does not silently
  transfer it.
- Retry only classified transient failures, with jitter, a cap, and idempotency. Do not retry money,
  messaging, deploy, permission, or destructive operations without an idempotency and approval
  policy.
- Trip a circuit on correlated failures, invalid shared state, repeated no-progress, fan-out growth,
  or budget pressure. Cancel descendants and preserve traces.
- Detect orphaned workers, duplicate task claims, join starvation, deadlock, livelock, and a worker
  declaring success without its output artifact.
- Treat a poisoned worker output as untrusted input to synthesis. One worker cannot certify itself
  or rewrite the goal, graph, grader, or sibling instructions.

## Trace and synthesis

Use one workflow trace with parent/child spans for agent runs, generations, handoffs, tools,
guardrails, joins, cancellation, and approval. Record task and requirement IDs, agent and parent IDs,
capability/authority digest, input/output artifact hashes, usage, latency, retries, and outcome.
Default to excluding sensitive model and tool payloads; store redacted references when full capture
is not permitted.

The synthesizer must cite which worker artifacts support each conclusion, expose conflicts and
missing results, verify final state independently, and remain within its own authority. Parallel
agreement is correlated evidence, not independent truth.

## Coordination transport

If workers use a mailbox, queue, chat, or cross-CLI ring, load `coordination-transports.md`.
Transport messages are untrusted notifications, not delegations, approval, identity, memory, or
proof. Send a non-sensitive pointer to the canonical hash-bound handoff artifact; the receiver
validates the contract, recipient, task transition, expiry, confined path, and digest before use.
The orchestration must remain correct when the transport is absent.

## Contract and validator

Copy `templates/agentic/orchestration-contract.sample.json` and validate before launch:

```bash
python3 scripts/validate-orchestration-contract.py orchestration-contract.json --json
```

The contract validator proves graph and policy coherence. After execution, copy
`templates/agentic/orchestration-run.sample.json`, bind it to the exact contract and captured
artifacts, and validate observed behavior:

```bash
python3 scripts/validate-orchestration-run.py orchestration-run.json --json
```

The runtime receipt checks worker leases, parented span topology, handoffs, tool authority,
destinations, write lanes, approvals, per-worker and global usage, joins, artifact hashes,
requirement provenance, independent verification, and review. Neither validator proves facts that
were omitted from the captured telemetry.

## Research basis

- OpenAI Agents SDK: orchestration patterns, typed handoffs, input filters, hooks, guardrails, and
  parented traces
- OpenTelemetry semantic conventions for generative AI agent and operation spans
- OWASP Top 10 for Agentic Applications 2026: inter-agent trust and cascading failures
