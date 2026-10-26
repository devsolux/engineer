# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/); the single release version lives in
`SKILL.md` metadata.

## Unreleased

### Added

- Rust language modules: `rust-idioms.md` (ownership, naming, domain types, standard traits,
  constructors and visibility, traits and macros, errors and panics, everyday idioms,
  checklist), `rust-systems.md` (concurrency and async, unsafe and FFI, crates and
  dependencies, rustdoc, tests, performance, lint enforcement and scan IDs),
  `rust-review.md` (scope, tools first, five-tier priority order, audit-shaped report with
  rule citations and code fixes) and `rust-port.md` (behavior list, tests first, C/C++,
  Python and Go/JS/TS mapping tables, proportionality, verification, porting notes). Every
  rule cites a primary source (Rust API Guidelines, Effective Rust, Rust Design Patterns,
  Pragmatic Rust Guidelines, Google Rust Style Guide, clippy and Cargo references); the
  sources and the local lint verification are recorded in `docs/verification-2026-10-26-rust.md`.
- `templates/rust/lints.toml` and `templates/rust/clippy.toml`: a drop-in Cargo `[lints]`
  table and clippy thresholds (unwrap outside tests, undocumented unsafe, suppressions without
  a reason, bool parameters, lossy casts, missing `# Errors` / `# Panics` docs, debug
  leftovers). `scripts/test-rust-lints.sh` assembles a check crate with one tagged violation
  per lint and asserts that exactly the tagged set fires; it skips with a notice when cargo
  clippy is not installed.
- `engineer-scan.sh --rust` (auto-enabled when a `Cargo.toml` is present): `RS-LINTS`,
  `RS-DENY-WARNINGS`, `RS-UNWRAP`, `RS-UNSAFE-SAFETY` and `RS-DEBUG-LEFTOVER`, with
  pass / warn / fail fixtures in `scripts/fixtures/{pass,warn,fail}-rust/` covered by
  `test-scan.sh`. Unwrap, unsafe and leftover signals warn by default and fail under `--strict`;
  the unwrap and leftover checks stop at a `#[cfg(test)] mod` and skip `tests/`, `benches/`,
  `examples/` and `build.rs`.
- Four routing evals (217-220): Rust library API, Rust refactor, Rust review, Python-to-Rust port.

### Changed

- `SKILL.md` routes Rust code, review and port work to the new modules (service work stays on
  `rust.md`), adds the Rust and port pattern rows to the verb table, and widens the Rust hard
  gate to no `unwrap` outside tests, `// SAFETY:` on every `unsafe` block, no
  `#![deny(warnings)]` in source, and clippy `-D warnings` in CI. `rust.md`, `refactoring.md`,
  `coding-principles.md`, `project-detect.md` and `enforcement-rules.md` cross-link the modules
  and the lint template.

## 1.2.0 — 2026-10-22

### Added

- `scan-doc-supply-chain.py`: a `privileged-trigger-secrets` rule. A `pull_request_target` or
  `workflow_run` workflow that references repository secrets (`secrets.NAME`, `secrets['NAME']`,
  `toJSON(secrets)` or `secrets: inherit`) is rejected; `GITHUB_TOKEN` is exempt because
  `permissions:` bounds it. Each YAML fence in Markdown is now evaluated as its own workflow.
- `validate-repo.sh` rejects a bare `[[ … ]]` or `! cmd` statement in `scripts/*.sh`: macOS's
  bash 3.2 does not stop on a failing `[[ … ]]` under `set -e`, and no bash stops on `! cmd`.

### Changed

- Live-eval reports record `models_observed`, the resolved model ids the host reports in its
  per-model usage, with `model_resolution` set to `observed` or `not_reported`. The previous guess
  from a date suffix in the requested name misreported current dateless model ids.
- `make test` accepts `TEST_TIMEOUT` (seconds per suite, default 180). CI runs with 600 seconds, a
  30-minute job limit, and uploads `.build/tests/` suite logs when the fixtures step fails.
- Module currency (2026-10-22 module ledger): all sixty-six past-due reference modules re-verified
  against primary sources and redated — the host and agent-security modules
  (`coding-agent-capability-playbooks.md`, `hermes-agent-integration.md`,
  `web-discovery-engineering.md`, `agent-red-teaming.md`, `implementation-completeness.md`,
  `skill-supply-chain.md`, `malware-detection.md`), the language modules (`python.md`,
  `typescript.md`, `rust.md`), the three-month stack modules (`backend-supabase.md`,
  `backend-database.md`, `billing-seats.md`, `billing-metered.md`, `deploy-ops.md`,
  `frontend-performance.md`, `frontend-state.md`, `frontend-testing.md`, `seo-metadata.md`,
  `observability.md`) and the backend and growth modules (`api-data-flows.md`,
  `backend-api.md`, `backend-storage.md`, `backend-webhooks.md`, `backend-testing.md`,
  `code-quality.md`, `growth-funnels.md`, `audit-log.md`, `backend-multitenant.md`,
  `background-jobs.md`) and the AI, admin and product modules (`ai-agents.md`,
  `ai-boundary.md`, `ai-evals.md`, `ai-security.md`, `backend-admin.md`, `backend-fts.md`,
  `backend-pgvector.md`, `email-notifications.md`, `feature-flags.md`,
  `product-onboarding.md`) and the process and product modules
  (`autonomous-experimentation.md`, `decision-engineering.md`, `coding-principles.md`,
  `developer-experience.md`, `engineer-telemetry.md`, `prd-to-evidence.md`,
  `git-signing-deploy.md`, `gtm-engineering.md`, `product-analytics.md`,
  `product-marketing.md`) and the architecture, security, agent and operations modules
  (`system-architecture.md`, `infra-security.md`, `enforcement.md`, `oss-maintainer.md`,
  `long-horizon-agents.md`, `prompt-optimization.md`, `skill-behavior-evals.md`,
  `capability-promotion.md`, `system-assurance.md`, `root-cause-engineering.md`,
  `epistemic-honesty.md`, `company-operating-system.md`, `portfolio-context.md`,
  `product-business-engineering.md`) and the design modules (`visual-communication.md`,
  `design-taste.md`). Corrections include current Claude Code hook, fallback and plan-file
  behaviour, Hermes v0.22.4 approval defaults, Python 3.14 as the default with refreshed pins,
  Supabase's explicit Data API grants (all projects from 2026-10-30), secret keys and Storage
  upload limits, Stripe meter events and thin events, Next 16 `preload`, async `params`, Proxy
  and `allowedOrigins` behaviour, MSW 3, Inngest v4, the Sentry wizard 8 / SDK v11 setup,
  Vercel Global Config (ex-Edge Config) and the `flags` package, React Email 6, Gmail / Yahoo /
  Outlook bulk-sender rules, pgvector filtered ANN, the renamed Claude Code Agent tool and
  `AGENTS.md` loading, the OWASP agentic and MCP lists, GitHub's "Partially verified" trigger,
  Claude Code OTel identity attributes,
  retired FAQ and HowTo rich results, re-sourced growth benchmarks, llms.txt v2,
  re-attributed incident figures, GitHub's workflow dependency lockfile, SSH keyboard-interactive
  authentication, npm 12 `allowScripts` and pnpm 11 `allowBuilds`, `actions/checkout` v7's
  fork-checkout guard, OSPS Baseline v2026.08.28 and Fly `fm2_` tokens, tool search without a
  beta header, RULER and METR horizon figures, `--bare` runs that send no skill list, and the
  sycophancy figures from Sharma et al.
- Review cadence: `implementation-completeness.md`, `audit-log.md`, `backend-multitenant.md`, `backend-fts.md`,
  `ai-boundary.md`, `product-onboarding.md`, the eight version-insensitive batch-five modules
  (all but `engineer-telemetry.md` and `git-signing-deploy.md`), `capability-promotion.md`,
  `system-assurance.md`, `root-cause-engineering.md`, `company-operating-system.md`,
  `portfolio-context.md` and `product-business-engineering.md` move to a 6-month cadence and
  `web-discovery-engineering.md` to 2 months.

### Fixed

- `install-host-activation.py --remove` deleted only Engineer's block and left 1-byte files behind,
  such as `~/AGENTS.md`, `~/.codex/AGENTS.md` and `~/.gemini/GEMINI.md`. A file that held only
  Engineer's block is now deleted; files with other content and dotfile symlinks are kept.
- Shell suites asserted with bare `[[ … ]]` and `! grep` statements that never failed on macOS
  (bash 3.2) or, for `!`, anywhere. All 25 now end in an explicit failure; the activation test
  fails before the fix above and passes after it.
- Wrong code samples: a whitespace-accepting Zod schema, a deprecated tower-http
  `TimeoutLayer::new` with reversed layer order, a removed Stripe `createUsageRecord` call, a
  synchronous Next 16 `params` read, a webhook handler that marked events processed before
  processing them, pgTAP tests with wrong plans and unmatchable `throws_ok` messages, a
  Route Handler that answered 409 to every insert error, a multi-tenant helper in an exposed
  schema with a hijackable `search_path`, an Inngest v3 call shape, a feature-flag table whose
  primary key made global rows impossible and whose one-byte bucket put 58.6% of users in a
  "50%" rollout, a non-IMMUTABLE email-log index, a FastAPI union return type that fails at
  startup, and an RLS explanation that misdescribed `WITH CHECK`.
- `coding-agent-hosts.md`: hook JSON is read on any exit code, `onFailure: "block"` fails
  closed, native plan files persist, and the hook event count is 33. `billing-stripe.md` reads
  the period end from the subscription item; `frontend.md` uses `z.flattenError()`.
- `backend-testing.md` and `enforcement.md` run the RLS migration gate on the migrations
  directory; the documented file glob and the lint-staged entry passed file paths, which made it
  skip with exit 0.
- `backend-security.md` names npm 12's `allowScripts` and pnpm 11's `allowBuilds` for dependency
  lifecycle scripts; eval 186 expects RULER's "half or less" effective context; the onboarding
  event `growth-funnels.md` gained is named `onboarding_step_completed`.
- `design-taste.md` no longer cites an unsupported 34% permanent-dark-theme share, calls Krebs's
  lowest tier "0–1 patterns" rather than clean, attributes the em-dash comparison to the designer
  Krebs quotes, and no longer credits Chanel with an adage Quote Investigator could not trace to her.
  `visual-communication.md` states YouTube's thumbnail and banner sizes, safe area, test eligibility,
  and X's header crop margin.
- `malware-detection.md` no longer claims the leak gate stays clean on this tree or that a
  path pattern passed to `--allow` exempts it.
- `COMPAT.md` records that Python 3.10, still the maintainer floor, reached end-of-life on
  2026-10-01, and that Next 15's 2026-10-21 end date follows from the support policy's
  two-year window.

## 1.1.0 — 2026-10-22

### Added

- `engineer security-audit <target>`: an evidence-graded codebase vulnerability audit —
  guidance mode by default, a six-phase full run (reconnaissance, coverage ledger, isolated
  hunting waves, refutation by a verifier that did not hunt, three-verdict `findings.json`,
  independent record review, target-neutral report) on request. Ships as three reference
  modules (`security-audit.md`, `security-attack-classes.md`, `security-audit-domains.md`),
  the `/engineer-security-audit` command, four role prompt bodies, the
  `validate-security-findings.py` and `validate-security-coverage.py` validators, the
  `security-ledger.py` ledger tool, illustrative receipts with bound evidence, JSON schemas,
  regression suites, and six static eval scenarios. Severity exists only on confirmed records
  and never exceeds demonstrated impact; target code runs only in an OS-enforced sandbox.
- `scripts/report-module-currency.py`: reference-module review-cadence report, printed
  informationally by `validate-repo.sh`, with a `--fail-after-days N` gate mode.
- `scan-doc-supply-chain.py`: a `privileged-trigger-fork-checkout` rule
  (`pull_request_target` / `workflow_run` checking out fork code) and YAML-fence scanning in
  Markdown; the CI template now ships the documented `supply-chain` job.
- MCP 2026-07-28 ("stateless core") evidence: `compile-mcp-transcript.py`,
  `validate-mcp-session.py` and `validate-mcp-content.py` now validate stateless transcripts
  and receipts, chosen by the per-request `_meta` protocol version, next to the unchanged
  2025-11-25 handshake path. Stateless rules: no `initialize` or session id, one version per
  transcript with matching HTTP version headers, optional `server/discover` (its capabilities
  bound later operations; its instructions quarantine), required `resultType`, `ttlMs` and
  `cacheScope` on cacheable results, stable client/server identity, and rejection of
  `input_required`, task results, task methods, a negotiated tasks extension, and
  `subscriptions/listen`. Roots, Sampling, Logging and dynamic client registration exposure is
  recorded as `deprecated_feature_exposure` and must be acknowledged in the session receipt; a
  stateless receipt without a captured `server/discover`, or with a discovered server extension,
  is gated.
- Synthetic fixtures under `templates/agentic/mcp-evidence-2026-07-28/`, the
  `mcp-session-2026-07-28.sample.json` and `mcp-content-2026-07-28.sample.json` receipts, and
  stateless mutation cases in `test-mcp-transcript.sh`, `test-mcp-session.sh` and
  `test-mcp-content.sh`.
- `engineer fix --findings <run>/findings.json`: remediation from a validated security-audit
  receipt, traceable from fingerprint to fix to regression test. Only `confirmed` records are
  fixed, in severity order, one per atomic change at the record's remediation layer and paths,
  each behind a regression test built from the trace and boundary that fails before the repair
  and passes after; `needs_validation` records are never patched (their local plan runs in a
  sandbox or the owner-observed checks go back to the user, and a vulnerable result returns to
  the audit for re-verification); `rejected` records are skipped and listed. Documented in the
  fix command, a "From findings to fixes" section of `security-audit.md`, and a pointer in
  `root-cause-engineering.md`.
- `validate-security-findings.py --remediated remediation.json`: cross-checks the fix receipt
  against the findings it binds by digest (confirmed only, severity order, changed paths inside
  `remediation.paths`, the matching layer, a red-then-green regression test, passing
  verification commands, a declared mitigation when not root-cause fixed, every record
  accounted for exactly once), with an illustrative
  `templates/agentic/security-remediation.sample.json`, mutation cases, and two eval
  scenarios (215, 216).

### Changed

- Currency (2026-10-22 ledger): Next 15 end-of-life (2026-10-21) and the Node 24 → 26 LTS
  handoff in `COMPAT.md`, stack rules, project detection, deploy-ops and the CI template; the
  repository workflow runs on push to `main` and on pull requests with a Node 26 lane; host
  versions and the Claude Code 2.1.304 hook limits in `coding-agent-hosts.md`.
- MCP: `mcp-security.md` and the mcp-audit command re-verified against the 2026-07-28 revision
  (stateless core; Roots, Sampling, Logging and dynamic client registration deprecated; Tasks
  as an optional extension). A 2026-07-28 version negotiated through `initialize`, mixed
  versions, a receipt whose version differs from its compiled transcript, and a content
  receipt whose capture manifest version differs from its bound session are rejected, never
  downgraded; `mcp-security.md` (Contract), `COMPAT.md` and the mcp-audit command describe
  both validated revisions.
- One severity mapping across surfaces (`code-quality.md`) and a confidence tag in the
  `engineer audit` template; live-eval reports record whether the model was an alias or a
  pinned id; release and contribution docs state the module-currency policy.
- Web-search strategy packs translated to English with currency headers.

### Fixed

- Documentation that disagreed with code: documented workflows now pin `gitleaks-action`,
  `actions/checkout` and `supabase/setup-cli` by commit; `oss-maintainer.md` lists the WORM
  leak class; the enforce command no longer repeats its guard line; enforcement docs match
  the shipped CI template; eval 169 names 2026-07-28 as the current MCP revision; the
  2026-10-11 ledger's "public repository does not exist yet" statement is superseded.
- `compile-mcp-transcript.py` rejected a non-object JSON-RPC `result` with a Python traceback;
  it now reports `captured result invalid: <method>` (regression case in `test-mcp-transcript.sh`).

## 1.0.0 — 2026-10-11

Initial public release.

- `engineer` skill: a progressive-disclosure router (`SKILL.md`) over 108 reference
  modules and 51 task workflows covering planning, auditing, building, fixing,
  refactoring, design, security, testing, research, and shipping.
- Plugin distribution from the public `devsolux/engineer` repository: Claude Code
  and Codex marketplace catalogs (`devsolux-engineer`) serving one generated
  bundle, `plugins/engineer`, installable as `engineer@devsolux-engineer` with no
  build step. Claude commands appear as `/engineer:<workflow>` with descriptions
  taken from the canonical workflows.
- Deterministic, standard-library plugin builder with ownership and drift checks,
  reproducible ZIP packaging with a SHA-256 sidecar, drift reports that name the
  missing, unexpected, or changed generated files, and desktop metadata files
  (`.DS_Store`, `._*`) ignored rather than blocking rebuilds.
- Offline verification: source linting, repository structure and supply-chain
  checks, a 208-scenario static eval bank, and 51 isolated test suites wired
  through `make` and a pinned GitHub Actions matrix (Linux/macOS, Python 3.10/3.13).
- Optional native skill and command installers for hosts without plugin
  marketplaces, with receipt-owned uninstall.
- Explicit publishing targets: `make release-check`, `make github-bootstrap`
  (public repository), and `make github-release`.
