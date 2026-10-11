# Codex, Claude Code, Hermes, and Portage host research - 2026-07

**Scope**: current host capabilities, security boundaries, orchestration, persistence, automation, and
portable handoff. Technical claims use official product documentation plus direct observation of local
CLI help/version output. Portage findings use the owner's private repository at the reviewed worktree.

## Observed local environment

| Runtime | Observed version | Important observed surfaces |
|---|---:|---|
| Codex CLI | 0.144.4 | exec, MCP/server, doctor, sandbox, resume, cloud experimental, feature flags, profiles, approvals, search |
| Claude Code | 2.1.209 | print/stream JSON/schema, agents/background/worktrees, plugins/MCP, settings, permission modes, bare/non-persistent, Chrome |
| Hermes Agent | 0.17.0 (2026.6.19) | profiles, gateway/cron, skills/curator, memory, MCP/plugins/hooks, browser, worktrees, terminal backends |
| Portage | private MVP 0.1.1 | provider discovery, snapshot, pack, strict doctor, delta, launch hints |

These observations establish installed surface only. They do not establish configured access,
authorization, runtime isolation, model quality, or that upstream documentation matches an older binary.

## Primary sources

### Codex

- Official Codex manual snapshot fetched 2026-07-15 through the OpenAI documentation helper: execution
  model/multi-agent, approvals and sandbox, configuration, CLI/app/cloud/browser/computer use, worktrees,
  AGENTS.md, skills/plugins/hooks/rules/MCP, app server/SDK/non-interactive mode, managed controls.
- Official manual is the source of truth for current Codex surfaces; local `codex --help`, `codex
  --version`, and feature inspection are the source of truth for installed availability.
- Official skill authoring documentation distinguishes explicit `$skill` invocation from implicit
  description matching, documents `policy.allow_implicit_invocation` (default true), and warns that
  the initial installed-skill catalog may shorten or omit descriptions under its context budget.
  Engineer therefore declares the policy explicitly and front-loads its routing intent. This configures
  eligibility; only a keyword-free captured behavioral run proves selection for a particular host/model.
- Source: <https://learn.chatgpt.com/docs/build-skills.md>
- Official non-interactive mode documents `--strict-config`: unknown `-c` overrides fail instead of
  being ignored. Engineer now requires that capability for sealed Codex jobs and compiles it beside
  `--ignore-user-config` so stale configuration cannot produce a valid-looking receipt.
- Source: <https://learn.chatgpt.com/docs/non-interactive-mode.md>

### Claude Code

- Overview: <https://code.claude.com/docs/en/overview>
- Settings and precedence: <https://code.claude.com/docs/en/settings>
- Permissions: <https://code.claude.com/docs/en/permissions>
- Bash sandbox: <https://code.claude.com/docs/en/sandboxing>
- Project memory/instructions: <https://code.claude.com/docs/en/memory>
- Skills: <https://code.claude.com/docs/en/skills>
- Hooks: <https://code.claude.com/docs/en/hooks>
- Subagents: <https://code.claude.com/docs/en/sub-agents>
- Agent teams: <https://code.claude.com/docs/en/agent-teams>
- Checkpointing: <https://code.claude.com/docs/en/checkpointing>
- CLI reference: <https://code.claude.com/docs/en/cli-reference>

### Hermes and Portage

- Hermes sources are cataloged in `hermes-agent-2026-07.md`.
- Portage (a private cross-provider job-handoff CLI, not published): reviewed README, AGENTS, schema,
  architecture/security docs, provider discovery, pack/delta/doctor implementation, and tests.

## Findings

1. The portable layer is policy and evidence, not flags. Instruction filenames, precedence, approval
   concepts, sandboxes, automation, memory, and parallelism are not interchangeable across hosts.
2. Surface matters as much as vendor. Local CLI, IDE, browser, desktop, cloud, CI, SDK, and gateway
   executions can have different filesystems, network, credentials, persistence, tools, and approvals.
3. A prompt cannot recreate an absent sandbox, managed policy, or identity boundary. Capability
   negotiation must fail closed or select a real alternative.
4. Parallel-agent features are schedulers. Correctness still requires a bounded DAG, isolated mutable
   resources, attenuated authority, captured child artifacts, deterministic join, and cancellation.
5. Persistent memory, skills, hooks, plugins, MCP, and context files are separate trust surfaces.
   Convenience increases the importance of provenance, scope, review, expiration, and incident recovery.
6. Portage fits as a separate cross-provider job carrier. Its git snapshot/delta reduces narrative drift,
   but its packet remains untrusted input and its provider/path hints do not prove identity or authority.
7. Portage schema v1 has `additionalProperties: true`; strict consumers should allowlist known fields.
   Path hints should never be opened automatically, and packets need secret scanning before sharing.
8. Cross-host comparisons need the same frozen contract, fixtures, oracle, and post-capture grading.
   Otherwise model, prompt, permissions, context, tools, budget, or environment confound the conclusion.

## Integration decision

- Add one engineer host-adaptation router with native Codex, Claude Code, and Hermes adapters.
- Keep Hermes runtime and Portage CLI independent; compose through explicit contracts.
- Reuse engineer skill-behavior eval capture for cross-host evidence and extend its environment binding.
- Prefer native resume for same-host continuity, Portage for cross-provider job handoff, and llmquota only
  for untrusted quota/notification pointers. None is an orchestration authority or completion oracle.

## Executable evidence

`capture-host-capabilities.py` now probes bounded local version/help surfaces and emits hashes rather
than raw help output, environment values, configuration, credentials, or sessions. It records applicable
instruction files with relative or opaque ancestor labels and content digests. The paired validator
requires the exact known-host set, host-specific capability vocabularies, internally consistent probe
evidence, mandatory limitations, and an `inventory_only` outcome. This closes installed-surface drift;
it intentionally leaves effective managed policy, feature enablement, sandbox, approvals, network,
credentials, selected model, and persistence for task-specific host-native evidence.

## Sealed Codex config

The Codex capture adapter now treats strict config parsing as a required host capability. Jobs must
bind the exact adapter capability set, not a caller-selected subset. The compiled command includes
`--strict-config`, and live re-probing rejects hosts that no longer advertise it. This closes a
fail-open path where an unknown or renamed `-c` key could be ignored while the receipt still matched
the local command compiler. It does not prove provider execution, managed policy, or sandbox behavior.

## Capability playbooks

The earlier adapter answered what a host advertises and how to bind it. The new playbook answers which
surface fits a job and when the native feature adds more weight than value.

Current local help and official sources show several distinct execution classes:

- Codex exposes local interactive and non-interactive work, structured output, review, plugins, MCP,
  app-server, remote-control, session resume and forking, cloud tasks, profiles, and local providers.
- Claude Code exposes structured print and stream automation, background and custom agents,
  worktrees/tmux, safe and bare modes, Remote Control, and UltraReview. Remote Control leaves execution
  and tool authority on the local machine. UltraReview is a research-preview cloud multi-agent review
  surface with explicit data, entitlement, latency, and cost consequences.
- Hermes exposes profiles, provider fallback and credential pools, gateway/API/ACP, cron, worktrees,
  kanban, checkpoints, MCP, skills, bundles, plugins, curator, and several isolation backends.

The useful abstraction is task-to-surface selection: required boundary, lifetime, isolation, output,
then operational cost. Engineer now separates ordinary review from fleet review; same-host resume from
remote control and cross-host handoff; worktree isolation from runtime identity isolation; clean config
from OS isolation; and credential rotation from provider fallback.

Fallback is a change to the evaluated system. Safety refusals, policy denials, invalid credentials,
malformed input, failed acceptance, and suspected injection are not retryable provider events. Paired
eval arms pin one provider/model; a fallback is reported as an infrastructure failure.

Additional primary sources reviewed:

- Claude Code CLI reference: <https://code.claude.com/docs/en/cli-usage>
- Claude Code permission modes: <https://code.claude.com/docs/en/permission-modes>
- Claude Code Remote Control: <https://code.claude.com/docs/en/remote-control>
- Claude Code UltraReview: <https://code.claude.com/docs/en/ultrareview>
- Hermes CLI commands: <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md>
- Hermes fallback providers: <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/fallback-providers.md>
- Hermes credential pools: <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/credential-pools.md>

## Inventory parity

The capability playbook exceeded the executable inventory vocabulary. A valid receipt could report older
automation and sandbox features but could not name many surfaces the playbook selected. That created a
false unsupported result and encouraged agents to fall back to prose inspection.

The schema-v1 receipt remains compatible, but its allowlisted capability vocabulary now includes the
observed current surfaces:

- Codex review, plugins, app-server, remote control and remote client, session fork/archive, local
  providers, and hook trust controls;
- Claude safe mode, Remote Control, UltraReview, fallback models, effort and cost controls, strict MCP,
  session forks, tmux, and tool allowlists;
- Hermes fallback chains, credential pools, kanban, hooks, backup/checkpoints, bundles, curator,
  toolsets, computer use, sessions, ACP, dashboard, and clean-config controls.

The fixture contract now asserts exact equality between detector token names and validator allowlists.
It also requires a minimum playbook-critical set for each host. Local capture on 2026-07-15 detected the
new surfaces on Codex 0.144.4, Claude Code 2.1.209, and Hermes Agent 0.17.0. Help matching still proves
only advertised installed surface, not enablement, entitlement, authentication, authorization, safety,
or correct behavior.
