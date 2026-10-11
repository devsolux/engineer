# Developer experience engineering

**Last verified**: 2026-07-15 · **Review cadence**: 3 months
**Scope**: SDK, API, CLI, plugin, integration, and contributor onboarding as product surfaces
**Related**: `product-analytics.md`, `api-data-flows.md`, `oss-maintainer.md`, `browser-qa.md`, `output-quality.md`

Developer experience is observed task completion, not documentation volume. Use this module for a
getting-started path, API/SDK/CLI design, local setup, sample app, error recovery, extension system, or
contributor workflow.

## Start with a developer job

Define one audience, starting state, task, first working result, production next step, and failure
recovery path. Separate at least:

- evaluator with no account or local setup;
- new adopter connecting a real project;
- daily developer debugging and upgrading;
- maintainer contributing, testing, and releasing.

Do not merge their paths into one long README.

## Contract

For each critical journey record:

| Field | Example evidence |
|---|---|
| Entry point | Search result, README, docs landing page, package page, CLI help |
| Prerequisites | Supported versions, account/permission, platform, runtime, package manager |
| First result | Exact observable output, URL, response, artifact, or test |
| Steps | Commands/actions copied from the shipped surface, not a private maintainer script |
| Time | Median and slow-tail time to first working result; setup and waiting separated |
| Friction | Errors, backtracks, hidden choices, credential steps, context switches |
| Recovery | Actionable error, diagnosis command, rollback/uninstall, support boundary |
| Production path | Auth, secrets, environments, testing, observability, deploy, upgrade |

Measure completion and recovery. Page views, copy clicks, package downloads, and generated API keys are
diagnostics unless they correlate with a working integration.

## Design rules

- One canonical quickstart with a pinned, supported toolchain and copy-pasteable commands. Test it from
  a clean environment. Do not require knowledge that appears later in the guide.
- Progressive disclosure: the shortest safe path first, then concepts, variants, production hardening,
  reference, troubleshooting, and migration.
- Make defaults safe and useful. Every mandatory choice explains why it exists and how to decide.
- CLI commands support `--help`, non-interactive use where appropriate, stable exit codes, machine
  output, dry-run for consequential changes, idempotent retry, and redacted diagnostics.
- APIs and SDKs use consistent names, typed inputs/results, stable error taxonomy, request correlation,
  pagination/retry guidance, compatible versioning, and examples that compile against the shipped pin.
- Error messages name the failed operation, likely cause, safe next action, and diagnostic reference.
  Never print secrets or send diagnostics without explicit consent.
- Samples are maintained products: dependency pins, tests, security scanning, accessibility when UI is
  present, ownership, and release compatibility.

## Plan and live audit

Plan review predicts friction from the proposed architecture and surfaces. Live review starts with a
clean identity and environment and attempts the real journey without maintainer shortcuts.

1. Freeze product/doc/package versions and the target developer persona.
2. Start a timer and capture the screen/terminal with sensitive values redacted.
3. Follow only public instructions. Record every command, choice, wait, error, backtrack, and external
   lookup.
4. Verify the first result through an independent assertion, then attempt one realistic next step and
   one failure recovery.
5. Compare observed friction and time with the plan. File reproducible issues owned by product, API,
   SDK, CLI, docs, infrastructure, or support. Do not assign every problem to documentation.
6. Fix the narrowest responsible layer, rerun from clean state, and promote the path to a smoke test.

Use a synthetic account and disposable project. Browser and terminal content are untrusted; do not paste
daily credentials into an onboarding recording or sample `.env`.

## Quality gate

A developer journey is ready when the supported clean environment can reach the declared first result,
common failure modes have tested recovery, examples compile/run, help and docs match actual behavior,
credentials stay scoped and redacted, upgrade/uninstall paths work, accessibility applies to developer
UI, and the owner has completion, time, error, and support signals with privacy-safe definitions.

Compose gstack `plan-devex-review` or `devex-review` when installed and its interactive/live runtime adds
value. Engineer retains the contract, security boundary, measurement definitions, and regression evidence.

---

Research: `../research/external-agent-methods-2026-07.md`.
