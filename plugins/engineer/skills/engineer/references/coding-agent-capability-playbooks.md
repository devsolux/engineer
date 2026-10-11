# Coding-agent capability playbooks

**Last verified**: 2026-08-19 · **Review cadence**: monthly
**Scope**: task-to-surface selection for Codex, Claude Code, and Hermes Agent
**Related**: `coding-agent-hosts.md`, `multi-agent-orchestration.md`, `skill-behavior-evals.md`, `ai-security.md`

Use this module after host capability negotiation. It selects an execution shape. It does not grant
authority, prove a feature is enabled, or replace acceptance tests.

Contents: [Selection order](#selection-order) · [Task-to-surface matrix](#task-to-surface-matrix) ·
[Build vs ride](#build-vs-ride) · [Review ladder](#review-ladder) ·
[Long-running and remote continuation](#long-running-and-remote-continuation) ·
[Parallel work and joins](#parallel-work-and-joins) ·
[Clean-room troubleshooting](#clean-room-troubleshooting) ·
[Extension-surface decision](#extension-surface-decision) ·
[Fallback and model-routing discipline](#fallback-and-model-routing-discipline) ·
[Structured automation receipt](#structured-automation-receipt)

## Selection order

Choose in this order:

1. required boundary: local files, cloud clone, browser identity, provider, data residency, or offline;
2. required lifetime: one command, interactive session, background task, remote continuation, or schedule;
3. required isolation: clean configuration, worktree, container, separate account, or separate service data;
4. required result: prose, patch, review findings, JSON/schema output, trace, or durable job artifact;
5. cost and operational weight.

Prefer the smallest surface that meets all five. Experimental, remote, background, and multi-agent
features require an explicit benefit and an exit path. A native feature is transport; Engineer still owns
scope, authority, evidence, tests, cancellation, and completion.

## Task-to-surface matrix

| Need | Codex | Claude Code | Hermes Agent | Gate |
|---|---|---|---|---|
| Fast local patch or review | interactive CLI, `exec`, `review` | interactive CLI, `-p`, local review | CLI/TUI, one task | Keep repository and verification local |
| Machine-readable automation | `exec --json` and output schema | print/stream JSON and JSON schema | API/ACP or bounded oneshot | Bind model, tools, budget, persistence, artifacts, and exit semantics |
| Parallel independent work | native subagents or cloud tasks when exposed | background agents, worktrees, tmux, agent teams | subagents, worktrees, batch, kanban | Isolate writes and runtime identities; deterministic join |
| Continue away from terminal | app/cloud/remote-control surface when exposed | Remote Control | gateway, API/ACP, persistent session | Remote client inherits local authority; authenticate and add a kill switch |
| Deep pre-merge review | local `review`; cloud task only when justified | local review; UltraReview for substantial high-risk change | independent reviewer profile or bounded subagents | Reproduce findings; cloud data, cost, entitlement, and retention approved |
| Clean-room diagnosis | ephemeral run, ignored user config/rules, strict config | safe mode or bare mode, depending on what must be removed | safe mode, ignored config/rules, isolated profile | Record what was excluded; clean configuration is not OS isolation |
| Provider resilience | explicit profile/model; local provider only when intended | explicit model and print fallback | credential pools and fallback chain | Never silently change an eval, security boundary, cost class, or data destination |
| Reusable extension | skill, plugin, MCP, rules/instructions, hooks | skill, plugin, MCP, subagent, hook, project memory | skill, bundle, plugin, MCP, hook, toolset | Pick by ownership and lifecycle; admit executable supply chain |

Names describe currently observed or documented surfaces. Probe the installed version before use.

## Build vs ride

Climb the ladder in order; each rung must fail before the next: extension surfaces (instructions →
skills → hooks/MCP → subagents) → Agent SDK (the host as a library) → raw custom harness. Four
requirements genuinely force custom: a non-terminal/gateway surface, multi-provider routing,
persistent server-side sessions, or a product-embedded agent. Vendor guidance is interested on both
sides; the neutral local datum is the deliberate split - engineer rides hosts, hermes builds custom -
and hermes also shows what "full" costs (a large security surface plus monthly upgrade churn).
Managed Agents and OSS harnesses now occupy the middle, so raw custom is rarely the first answer.
Write the forcing requirement as one sentence and check it against the extension-surface table
first; keep state in files/git and behavior in skills/MCP so the decision stays reversible.

### Hook patterns (deterministic gates)

| Pattern | Event | Return channel |
|---|---|---|
| Format-on-edit, lint gate | PostToolUse (Edit\|Write) | exit 2 blocks; JSON parsed on exit 0 |
| Dangerous-command deny, protected-path guard | PreToolUse (Bash/Edit) | `permissionDecision: "deny"` |
| Context injection | SessionStart | stdout on exit 0 |
| Completion gate - no "done" until verify + scan pass | Stop / SubagentStop | `decision: "block"` until green; no hook surface → same gate in CI |

### Skill composition and plan surfaces

Four composition shapes: skill→reference router (engineer itself), skill→skill delegation, command
chain (the research → research-deep → research-report pipeline is the worked example), and the
one-plugin bundle. Plan surface: native plan mode is read-only explore + approve and
session-ephemeral; a file plan (`.engineer/plans/<slug>.json`) is the durable record for multi-file,
cron, or cross-host work - carry plan-file references, never native plan state, in Portage packets.

## Review ladder

1. Use ordinary local review for a small or medium diff when repository context and standard checks are
   enough.
2. Add a second independent local reviewer for security-sensitive or ambiguous findings.
3. Use cloud or fleet review only when independent reproduction across a substantial change is worth
   upload, retention, entitlement, latency, and cost. Claude UltraReview is a research-preview cloud
   fleet, not a stronger permission boundary or a merge oracle.
4. Convert accepted findings into tests, static gates, or exact code evidence. Reviewer confidence and
   consensus are not proof.

Never upload an unreviewed dirty tree, secrets, regulated data, customer content, or private fixtures to
a remote review surface. Confirm the exact target and service policy first.

## Long-running and remote continuation

- Prefer same-host resume for an ordinary interrupted session. Use Portage only for cross-host handoff.
- Codex app-server and remote-control surfaces, Claude Remote Control, and Hermes gateway/API/ACP are
  control planes. Re-negotiate authentication, bind address, session identity, workspace, tools,
  approvals, network, persistence, and timeout for that surface.
- Claude Remote Control keeps execution on the local machine. The web or mobile client does not reduce
  the local process's filesystem, MCP, tool, or credential reach.
- A local process that must remain alive needs liveness, disconnect, cancellation, log redaction, and
  recovery behavior. A remote UI is not durable job orchestration by itself.
- Prefer Hermes for an intentionally persistent gateway, cron, profile, provider-routing, or ACP job.
  Keep unattended approval fail-closed and verification independent.

## Parallel work and joins

Parallelize only when the critical path shrinks enough to justify coordination and model cost.

- Partition by independent files, packages, investigations, or read-only review questions.
- Use worktrees for Git writes, but allocate separate accounts, tenants, browsers, ports, queues, and
  fixture namespaces when those resources mutate.
- Give every worker a bounded input, output schema, allowed tools/destinations, budget, timeout, and
  cancellation rule. Workers may not widen their own task.
- The join checks artifact hashes, conflicts, tests, omissions, and cross-cutting invariants. It does not
  concatenate summaries and trust consensus.
- Kanban, background agents, agent teams, and cloud task lists show scheduling state. They do not prove
  correctness or ownership of shared resources.

## Clean-room troubleshooting

Use a clean run to answer whether customization caused a failure.

- Codex: pair ignored user configuration with strict parsing and ephemeral persistence where supported.
- Claude: safe mode disables customizations broadly; bare mode is a minimal automation context. Treat
  them as distinct experiment variants and record the effective instructions and tools.
- Hermes: use safe/ignored-config modes plus an isolated profile or external terminal backend when the
  test also requires credential or filesystem separation.

Repeat the same frozen task in normal and clean modes. One successful clean run identifies a candidate
cause; it does not identify which removed customization was responsible. Bisect admitted components.

## Extension-surface decision

| Surface | Choose it when | Do not choose it when |
|---|---|---|
| Project instructions | Stable repository policy and commands apply to most work | The procedure is optional, large, or unrelated to most tasks |
| Skill | A reusable, on-demand procedure and knowledge package should route by intent | A deterministic lifecycle control or external service is required |
| Plugin/bundle | Several related skills, commands, hooks, or integrations need one versioned distribution unit | One small skill or repository rule is enough |
| MCP | A process or remote service must expose typed tools/resources across hosts | A local script or direct API inside the product is simpler and safer |
| Hook | A deterministic lifecycle event must run a bounded check | Judgment, broad mutation, or untrusted generated shell is involved |
| Subagent/custom agent | A stable bounded role needs its own context and tool policy | The task is sequential or the parent can do it without coordination overhead |
| Memory | A small durable fact improves later work | The content is a procedure, secret, transient state, or unverified instruction |

Prefer one owner for a rule. Do not copy the same policy into instructions, skill, hook, and memory.

## Fallback and model-routing discipline

Fallback improves availability but changes the evaluated system.

1. Declare allowed provider/model sequence, retryable error classes, maximum attempts, total cost/time,
   and data destinations before execution.
2. Do not fallback on safety refusal, policy denial, invalid credentials, malformed task input, failed
   acceptance, or suspected prompt injection.
3. Re-negotiate tools, context limits, structured-output behavior, data policy, and cost after a provider
   change. Mark the run with the actual provider/model and attempt chronology.
4. For benchmarks and prompt optimization, pin one provider/model per paired arm. A fallback is an
   infrastructure event, not a valid substitute trial.
5. Hermes credential pools may rotate credentials within one provider; fallback chains may change
   providers. Both require redacted attempt evidence and quota-aware backoff. Claude's print fallback
   and Codex profiles likewise need explicit binding.

## Structured automation receipt

For non-interactive work capture: host/version/surface, exact task artifact, repository revision,
instruction/customization mode, provider/model, allowed tools, sandbox/approval/network, schema, maximum
turns/time/cost, persistence, output paths and hashes, exit/timeout/cancellation, actual fallback path,
verification commands, and known limitations.

JSON conformance proves shape, not truth. Re-run acceptance checks outside the agent process when the
outcome matters.

---

Research: `../research/coding-agent-hosts-2026-07.md`. Refresh after host releases or monthly.
