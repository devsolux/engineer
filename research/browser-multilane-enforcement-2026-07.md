# Browser multi-lane enforcement - 2026-07

## Finding

The browser modules correctly required isolated lanes and serialized shared-account writes, but
the template combined `fullyParallel: true` with one shared authenticated storage state. Guidance
alone did not prevent a consumer from placing mutating specs in the parallel auth project.

## Implemented contract

- `standard` includes public, quality, and authenticated read-only projects only.
- `auth/write/*.spec.ts` is undiscoverable in standard runs.
- `E2E_LANE=auth-write` is explicit, requires credentials, forces one worker, and disables full parallelism.
- Invalid lane names and unauthenticated auth lanes fail during config loading.
- Public and quality lanes remain independently selectable for CI sharding.

This controls shared-account concurrency. Parallel mutating data lanes still require unique
per-worker users or tenants and lifecycle cleanup; a namespace string alone does not create that
isolation.

## Primary sources

- Playwright browser contexts: tests receive isolated incognito-like contexts by default.
- Playwright parallelism: test files run in worker processes; fully parallel mode can parallelize tests within files.
- Playwright authentication: shared-account state is suitable when tests do not modify server-side state; modifying tests need separate accounts.
- Playwright projects: logical configurations can separate environments, retries, and test selection.
