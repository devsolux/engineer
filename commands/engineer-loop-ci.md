---
description: Loop every 2m watching GitHub CI until green or actionable failure - needs gh CLI.
---

# /engineer-loop-ci

**Loop command** - load engineer `SKILL.md`, `references/workflows.md`, and the active host’s **`loop`** capability when available.

## Purpose

Watch PR/branch CI after push; fix scoped failures and re-push when user approves commits.

## When invoked via /loop

User runs: `/loop 2m /engineer-loop-ci`

Prefer **fixed 2m** interval (not busy-poll). If rate-limited by GitHub API, back off to **5m**.

## Prerequisites

- `gh` CLI authenticated (`gh auth status`)
- On a branch with open PR or recent workflow run

## Each iteration

1. Check CI status (prefer PR context):
 ```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
 gh pr checks
 ```
   If there is no PR, inspect branch runs separately with `gh run list`. A successful list command is not a passing CI result; preserve authentication, network, and check failures.
2. **All pass** → stop loop, notify user with run URL ✅
3. **Pending** → wait for next interval (do not thrash `gh`)
4. **Fail** → fetch failed job log:
 ```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
 gh run view <id> --log-failed | tail -n 200
 ```
5. Classify:
 - **engineer-scoped** (typecheck, lint, scan, tests, evals) → `/engineer-fix` minimal diff
 - **flake** (same test intermittent) → report; do not weaken CI
 - **infra / secrets / permissions** → stop and list manual steps
6. Commit/push **only if user asked**
7. Re-check on next interval

## Backoff

| Situation | Interval |
|---|---|
| Default | 2m |
| API rate limit / abuse | 5m |
| Long build (release matrix) | 3-5m |
| Max iterations | 30 (~1h at 2m) then stop |

## Stop conditions

- CI green
- User says stop
- 30 iterations → report stuck with last failure summary
- Failure outside PR scope → escalate (do not rewrite unrelated workflows)

## Rules

- Never change CI workflows only to make checks pass
- Never force push to main
- Never use `--no-verify` to skip hooks unless user explicitly asked
- Maker≠checker: local green is not enough if required CI checks still red
