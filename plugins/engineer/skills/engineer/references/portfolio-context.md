# Portfolio context: workspace and venture truth for cross-repo work

**Last verified**: 2026-10-22 · **Review cadence**: 6 months
**Related**: `project-detect.md`, `composition.md`, `company-operating-system.md`,
`hermes-agent-integration.md`, `coordination-transports.md`

Load when a task touches more than one repository, changes a contract another repo consumes,
needs venture/entity ownership, or must respect workspace policy and health. This module makes
Engineer portfolio-aware without making it a portfolio decision-maker.

The pattern below is abstract: an operator who runs several repositories and ventures keeps a
**control-plane repository** that publishes machine-readable policy and state. File names are
placeholders; adapt them to the local layout (`ENGINEER_CONTROL_PLANE_REPO` names the repo for
`scripts/plan-fleet-status.sh`, default `control-plane`).

## Workspace-truth contract

Portfolio facts are **read from declared sources, never inferred by rescanning the filesystem**:

| Source | Truth it owns | How to read |
|---|---|---|
| Workspace registry (a top-level README or manifest in the workspace root) | Canonical repository list, layout rules | Read the registry section on demand |
| Global agent policy file (host-neutral instructions shared across agents) | Cross-agent working, security, and hygiene rules | Already binding; do not re-derive |
| Control-plane repo `config/workspace-policy.json` | Canonical repositories, repo→venture mapping, generated-dir and container policy | Read the JSON; treat as machine-readable policy |
| Control-plane repo `data/workspace-health.json` | Latest workspace health snapshot (findings, severities, `healthy` flag) | **Read the snapshot**; never rescan the workspace yourself - this mirrors the proven runtime pattern of consuming published state |
| `scripts/plan-fleet-status.sh` → control-plane `data/plan-fleet.json` | **Who else is working here**: active plan streams, claims, branches, stale/orphan findings across canonical repos | Run the script (or read the snapshot it writes with `--snapshot`); never hand-rescan `.engineer/` dirs across repos |

Keep the snapshot contract even when the plan schema's formal `verification`/`integration`
objects go unused in practice (observed in one operator fleet: a fresh `plan-fleet.json` while
none of the active plans carried receipts). Treat a receipt-adoption gap as a known finding, not
as proof that fleet verification happened.

When the control-plane repo is absent on the current machine, mark portfolio facts `n/a` and
continue with single-repo truth; do not fabricate a workspace model.

## Venture and entity ownership resolution

Authoritative registries live in the control-plane repo. **Reference these paths at read time;
never copy their data into modules, prompts, or code** - copies go stale silently:

| Registry (placeholder names) | Owns |
|---|---|
| `config/venture-registry.json` | Venture keys, entity types (venture / internal_system / legal_entity), directories, aliases, accounts |
| `config/layers/registry.json` | Entity classes and channel/layer definitions |
| `config/venture-automation.json` | Per-venture automation switches (posting, replies, holds), keyed by registry key |
| `config/workspace-policy.json` → repo→venture map | Machine-readable repo→venture mapping |

**Resolution rule**: map the working repository to a venture via the repo→venture map in
`workspace-policy.json`. If the repo is not in the mapping, the venture is **"unknown - ask"**;
never guess ownership from directory names, README branding, or aliases alone.

## Cross-repo impact checklist

Before shipping a change with cross-repo surface, check who consumes it:

1. **Control plane** - flag any change that alters a path, schema, script name, or contract
   that control-plane configs, crons, or dashboards read.
2. **Agent runtime** (Hermes or similar) - does an agent profile, tool, cron, or gateway consume
   this repo's outputs or published state?
3. **Operator dashboards** - flag data whose shape or source this change moves while app/landing
   surfaces still render it.
4. **Skills workspace installs** - skills are installed into many hosts and referenced from many
   repos; renaming files, scripts, or verbs breaks consumers that never appear in this repo's
   own grep.
5. **Public contracts** - for a venture repo (e.g. an RPC edge-node venture), does the change
   alter an API, URL, or artifact that customers or sibling repos depend on?

Name each affected consumer in the plan and verify against the consumer's contract, not only
this repo's tests.

## Escalation rules (flag before shipping)

Stop and surface the fact - do not silently proceed - when portfolio truth shows:

- **FOUNDER HOLD** or `automation_enabled: false` for the venture in the automation registry
  (`config/venture-automation.json` above): build work may proceed, but nothing may activate,
  post, schedule, or enable automation for that venture without explicit founder confirmation.
- **Workspace unhealthy** (`healthy: false` or error-severity findings in
  `data/workspace-health.json`): report the findings that intersect the task before making
  structural changes (moves, renames, new checkouts, worktrees).
- **Repo not in the canonical registry**: confirm intent before treating it as a portfolio
  member or creating cross-repo dependencies on it.
- **Venture unknown**: ask; never attach work to a venture by guess.

## Hard boundary: facts, not decisions

Engineer loads portfolio **facts** (ownership, policy, health, consumers) to engineer correctly.
It never makes portfolio **decisions**: strategy, prioritization across ventures, pricing,
resourcing, holds and unholds, or venture lifecycle calls route to a private strategy skill (if
installed) and the accountable human, per the ownership matrix in `composition.md`. A generic
business-knowledge question (benchmarks, frameworks, formulas) is not a portfolio decision - a
business-knowledge reference skill answers it; only decisions about this portfolio route to the
strategy owner. If a task requires a portfolio decision that has not been made, stop at the
smallest decision gate and name the owner.

## Output line (append to project-detect template)

```
Portfolio: venture {key|unknown}, workspace {healthy|attention|n/a}
```

`attention` means the health snapshot has findings intersecting the task; `n/a` means no
control plane is available on this machine.

## Anti-patterns

- Rescanning the workspace root or globbing sibling repos when a published snapshot exists
- Copying registry data (venture keys, aliases, switches) into prompts, docs, or code
- Guessing repo→venture ownership from names instead of the machine-readable mapping
- Shipping automation for a venture on hold because "the code change was already approved"
- Letting portfolio facts escalate into portfolio decisions inside an Engineer session

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
