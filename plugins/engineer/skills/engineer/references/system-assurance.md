# System assurance: goals to runtime truth

**Last verified**: 2026-10-22 · **Review cadence**: 6 months
**Related**: `product-business-engineering.md`, `prd-to-evidence.md`, `api-data-flows.md`,
`frontend-testing.md`, `backend-testing.md`, `browser-qa.md`, `observability.md`

Use this module when Engineer must understand a product as a whole, verify business logic across
frontend and backend, debug cross-system behavior, or assess whether a project works as intended.

## Assurance boundary

No finite suite proves 100% functionality for a non-trivial system. Inputs, schedules, dependencies,
browsers, devices, data histories, permissions, and production conditions create an open state space.
Challenge absolute-proof requests. Replace them with explicit scope, traceable coverage, independent
evidence, operational confidence, and residual risk. Never translate "all tests pass" into "no bugs."

## Build the product truth model first

Inspect rather than infer:

1. Product promise, ICP/jobs, current goals, success metrics, guardrails, and non-goals.
2. Roles, tenants, permissions, plans, entitlements, lifecycle states, and allowed transitions.
3. Critical journeys from entry through value, payment, recovery, support, cancellation, and deletion.
4. Business rules and invariants: eligibility, calculations, limits, ownership, idempotency, time,
   ordering, reconciliation, audit, privacy, and failure behavior.
5. System map: UI, API/actions, auth, database/RLS, jobs, webhooks, caches, vendors, analytics,
   observability, deployment, and support operations.
6. Existing evidence: PRDs, schemas, code, tests, incidents, telemetry, customer reports, and known gaps.

If the offer, goal, or rule is contradictory or unknown, stop at the smallest decision gate. Engineer
may implement accepted business policy; the private strategy skill remains the owner of company strategy.

## Goal-to-evidence matrix

For every material rule or journey, record:

| Field | Required content |
|---|---|
| ID and outcome | Stable requirement/rule ID plus user and business outcome |
| Actors and scope | role, tenant, plan, locale, device, data preconditions |
| State transition | allowed start, command/event, resulting state, forbidden transitions |
| Invariants | conditions true before, during, and after success or failure |
| Boundaries | UI, API/event, auth, data, job/vendor, analytics, operational owner |
| Evidence | named unit, property, integration, contract, browser, security, and runtime checks |
| Failure/recovery | timeout, retry, duplicate, partial failure, rollback, reconciliation, support path |
| Confidence | observed result, environment/date, untested dimensions, residual risk, owner |

Reject orphaned requirements, tests with no requirement, and critical rules supported only by mocks.
Compile stable IDs through `prd-to-evidence.md` and its execution/completion receipts.

## Layered verification

Choose layers by failure mode, not a fixed test-count target:

- **Static and schema:** types, lint, validation schemas, migrations, policy scans.
- **Domain unit and property:** calculations, state machines, invariants, boundaries, generated edge
  cases. Property tests complement examples; they do not prove an unbounded domain.
- **Component/integration:** user-visible states, forms, accessibility, API adapters, real database and
  queue behavior where mocks would hide integration risk.
- **Consumer/provider contract:** requests, responses, events, compatibility, and provider replay.
- **Security and permissions:** anonymous, role, tenant, plan, ownership, abuse, injection, secrets,
  rate limits, RLS, and negative paths; a requested vulnerability hunt runs through
  `security-audit.md`, and its validated findings receipt feeds residual risk.
- **Browser journeys:** isolated user-visible critical flows across relevant viewports/browsers, with
  console, network, accessibility, loading, empty, error, retry, and recovery evidence.
- **System and failure injection:** real service composition, duplicates, out-of-order events,
  dependency failure, retry, rollback, reconciliation, and data integrity.
- **Production assurance:** canary/synthetic journeys, user-centered SLIs, correlated traces/logs/
  metrics, business-event reconciliation, alerts, rollback, and incident learning.
- **Test-quality checks:** mutation testing or deliberate fault seeding on high-risk pure logic to
  detect assertions that pass without protecting behavior. Apply selectively because cost is real.

Do not invert the test pyramid or force every edge case through Playwright. Browser tests prove
integrated journeys; focused layers localize business-rule failures faster.

## Systematic debug loop

1. State the violated outcome, rule ID, expected transition, actual observation, environment, and time.
2. Reproduce from the nearest deterministic layer; capture request/trace ID and immutable inputs.
3. Follow the real path UI → network → auth → domain → data → async/vendor → returned state.
4. Find the first divergence from the invariant. Distinguish root cause from downstream symptoms.
5. Add the smallest failing regression at the lowest sufficient layer; watch it fail for the reason.
6. Repair the cause, then run the focused check, adjacent contract tests, critical journey, and
   affected security/data/analytics reconciliations.
7. Verify in the closest safe environment to the failure. Instrument missing blind spots rather than
   adding speculative logs. Record residual risk and a production detection or rollback path.

Stop repeated blind fixes. Re-plan when the observation invalidates the assumed system map, the same
state repeats without information gain, or evidence points outside current authority.

## Completion language

Report: verified scope, requirement coverage, environments, commands and artifacts, production
signals, known gaps, residual risk, and the next confidence-raising check. Say "all declared gates
passed" only when they did. Never say "100% functional," "fully tested," or "bug-free" unless the
claim is explicitly bounded to a closed finite contract that was exhaustively checked.

**Research basis**: `../research/system-assurance-2026-07.md`
