# gstack → engineer: what to steal (and what not to)

**Date:** 2026-07-13  
**Reference:** `~/.claude/skills/gstack` (ARCHITECTURE, ETHOS, router skill, plan-eng-review, health, qa/browse)

## What gstack does well

| Pattern | gstack | engineer adoption |
|---|---|---|
| **Router + specialists** | Thin `gstack` skill routes to plan/qa/ship/cso | Already: `SKILL.md` verbs + leaves. **Added** `composition.md` so partners (including gstack skills) own domains |
| **Completeness bias** | ETHOS “boil the ocean” / cheap last 10% | Aligns with complete modules + scanners over half-docs |
| **Plan before code** | plan-eng-review locks architecture | **PVE**: plan artifact + `validate-plan.sh` + plan command |
| **Browser vs unit tests** | Persistent Chromium daemon for QA | **Split**: Playwright templates for CI paths; gstack qa/browse for exploratory |
| **Localhost security** | Dual listeners, no casual token leak | Skill supply-chain install pin + no curl\|bash in scripts |
| **Health composite** | Wraps project tools → score | Optional later; for now `engineer-scan` + app’s own `tsc`/lint |
| **Session preamble** | Branch, proactive, repo mode | Keep light — avoid gstack-style bash preamble tax on every verb |

## What not to copy

- **Bun compiled browse binary** — out of scope for a docs/scanner skill  
- **Auto-generated multi-host skill trees** — overkill until public multi-host packaging is the goal  
- **Ethos wall in every command** — keep ethos in research/docs; agents load modules on demand  

## Research backlog

| Idea | Priority | Status |
|---|---|---|
| `engineer health` thin wrapper | P2 | ✅ `scripts/engineer-health.sh` |
| Eval harness runner | P1 | ✅ static `run-evals.sh` (model runs stay manual) |
| Scan fixtures (pass/fail) | P1 | ✅ `test-scan.sh` + fixtures |
| Audit-log + seat billing modules | P1 | ✅ shipped |
| Multi-host installer matrix | P1 | ✅ `--hosts hermes,opencode,gemini` |
| Description token re-budget | P1 | open (L1 ≤1024 polish) |
| Live model eval CI | P2 | needs API budget + harness host |

## Bottom line

engineer should remain a **stack OS** (patterns + gates). gstack remains a **workflow + browser OS**. Composition contract is the seam — not a merge.
