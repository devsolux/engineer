# Browser lane evidence - 2026-07

## Gap

Playwright configuration can keep shared writes out of parallel projects, and a browser-session
receipt can validate one worker. Neither proves that a captured multi-worker run used distinct
principals, tenants, namespaces, evidence paths, and cleanup boundaries. A namespace label is not
an account-isolation control.

## Implemented contract

- Every aggregate lane references a confined, SHA-256-bound session receipt.
- The canonical browser-session validator runs for every referenced receipt.
- Session and aggregate agree on lane, worker, namespace, hashed account, and hashed tenant.
- Public lanes have no principal; authenticated lanes have one; fixture writes have a tenant.
- Isolated writes cannot reuse account or tenant identities.
- Shared-write lanes and same-account write/read lanes cannot overlap in time.
- Observed interval concurrency cannot exceed the declared maximum.
- Receipt files and artifact roots are unique; each artifact remains beneath its lane root.
- Aggregate approval requires a reviewer independent from every session reviewer.

The identities are pseudonymous correlation values. This contract proves internal agreement and
collision policy, not that the identity provider issued each account or that server-side tenancy
was enforced. Provisioning attestations and backend audit-event correlation are deeper boundaries.

## Primary sources

- Playwright parallelism and worker-index guidance for process isolation and per-worker data.
- Playwright authentication guidance separating shared read-only accounts from modifying tests that need separate accounts.
- Playwright browser-context guidance for isolated cookies and storage.
- OWASP guidance on tenant isolation and auditability at authorization boundaries.
