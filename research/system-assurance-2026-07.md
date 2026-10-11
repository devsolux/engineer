# Goal-to-runtime system assurance research

**Verified**: 2026-07-16

## Decision

Engineer should not promise universal functional proof. It should construct a traceable assurance case
from accepted product goals and business rules through focused tests, critical full-stack journeys,
and correlated runtime evidence. The reusable pattern is a goal-to-evidence matrix plus a systematic
first-divergence debugging loop.

## Findings applied

- Playwright recommends isolated tests of user-visible behavior, resilient locators, web-first
  assertions, controlled data, CI execution, and relevant browser coverage.
- React Testing Library favors tests that resemble real use and avoid implementation details.
- Pact verifies consumer assumptions against providers for HTTP and asynchronous messages.
- Hypothesis generates inputs and shrinks failures for domain invariants and edge cases.
- Stryker mutation testing checks whether tests detect deliberately changed code; use it selectively.
- OpenTelemetry connects reliability debugging with correlated traces, metrics, and logs and notes
  that 100% uptime does not mean the product does what users expect.
- DORA pairs delivery throughput with instability. Deployment count alone is an unsafe target.

## Primary and implementation sources

- Playwright, [Best Practices](https://playwright.dev/docs/best-practices)
- Testing Library, [React Testing Library](https://github.com/testing-library/react-testing-library)
- Pact Foundation, [pact-js](https://github.com/pact-foundation/pact-js)
- Hypothesis, [hypothesis](https://github.com/HypothesisWorks/hypothesis)
- Stryker Mutator, [stryker-js](https://github.com/stryker-mutator/stryker-js)
- OpenTelemetry, [Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/)
- OpenTelemetry, [Log correlation](https://opentelemetry.io/docs/specs/otel/logs/)
- DORA, [Software delivery performance metrics](https://dora.dev/guides/dora-metrics/)

## Limits

Repository popularity does not establish suitability. Tools remain optional and must match project
language, architecture, risk, existing stack, maintenance cost, and a concrete missing evidence class.
