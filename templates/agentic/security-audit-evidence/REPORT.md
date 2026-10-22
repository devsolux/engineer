# Security audit report: fixture-notes-service (run-001)

Illustrative fixture. The target, its paths, principals, and results are synthetic.

## Summary

| Verdict | Count |
|---|---|
| confirmed | 1 |
| needs_validation | 1 |
| rejected | 1 |
| hardening notes | 1 |

The run is complete: all 12 coverage cells have a terminal status, one wave of two
isolated hunters was reviewed by a distinct coverage critic, every candidate was
refuted or confirmed by a verifier who did not hunt it, and each surviving record
passed an independent record review.

## Sandbox and safety

Source inspection was read-only. Target code ran only inside an OS-enforced sandbox
with no network, an empty environment allowlist, a read-only target mount, scratch-only
writes, and CPU, memory, and wall-clock limits. No live, shared, or production system
was probed. All principals and secrets were synthetic.

## Confirmed

- Any member can read another owner's note by id (access_control, data_isolation).
  Severity high: likelihood high, impact high. Remediation in the data access layer.

## Needs validation

- The attachment worker fetches a member-supplied URL without an egress check
  (resource_handling, cloud_infra). The blocker is a deployment fact: whether the
  worker's egress policy denies private and link-local ranges. No severity is assigned
  until the owner-observed or sandboxed local step resolves it.

## Rejected

- Note export path built from the note title: the slugify allowlist removes every
  path separator before the value reaches the filesystem.

## Hardening notes

- JSON API accepts state changes without a CSRF token; the JSON content-type gate,
  the custom request header, and the SameSite=Strict cookie prevent the attack today.

## Limits

Deferred: the admin CLI at the member-to-owner boundary (operator shell only; deep
profile). Not applicable: the admin CLI at the anonymous-to-member boundary.
