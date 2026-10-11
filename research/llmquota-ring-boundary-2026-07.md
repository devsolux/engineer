# llmquota and engineer composition boundary

**Date:** 2026-07-15  
**Reviewed:** local `devsolux/llmquota` worktree at commit `a2f50bb` plus its current README,
`src/bus.ts`, `src/bus-arm.ts`, tests, hook, package metadata, and security policy.  
**Upstream:** [devsolux/llmquota](https://github.com/devsolux/llmquota)

## Decision

Keep llmquota separate. It is a quota and local cross-CLI transport product. engineer is an
engineering and orchestration policy system. Combining them would duplicate provider-specific
credential collectors and make engineer dependent on one transport.

Integrate only a documented adapter contract:

- llmquota owns collection, provider routes, quota display, LIVE state, JSONL delivery, cursors,
  presence, addressing, hooks, and transport lifecycle;
- engineer owns the orchestration graph, delegation, permissions, budgets, lanes, typed handoffs,
  artifact hashes, joins, synthesis, and verification;
- the ring carries a short non-sensitive pointer to a canonical hash-bound artifact;
- quota is a scheduling signal, never authority or proof.

## Evidence

The ring is intentionally daemonless and local. It stores append-only JSONL under the user's data
directory, uses per-identity byte cursors, records current directory and Git root for scoped
addressing, limits sent text to 2,000 characters, and installs host-specific instructions or a
Claude prompt hook. Files and directories are created with user-only modes.

Those choices make it useful for lightweight notification, but they do not authenticate sender
labels or turn routing selectors into authorization. Hook output enters model context. Messages can
therefore carry prompt injection, social-engineering claims, stale success reports, replayed
pointers, path disclosure, or spoofed identities. Same-user file permissions reduce cross-account
exposure; they do not make peer text trusted.

The implementation already has useful foundations: bounded pull counts, cursor seeding at LIVE,
unique identity support, no TTY injection, no CLI spawning, same-directory/repository addressing,
and tests for cursor advancement and routing. engineer should build on those properties without
claiming stronger guarantees.

## llmquota-side hardening backlog

These remain llmquota concerns, not code to copy into engineer:

- document that ring messages and sender identities are unauthenticated and must be treated as
  untrusted context;
- add explicit retention/rotation and maximum ring/chunk size policy;
- add a structured envelope mode with message ID, contract/task IDs, artifact digest, expiry,
  sensitivity label, and acknowledgment while retaining plain human shouts;
- test duplicate delivery, identity/cursor collision, stale LIVE markers, oversized files, partial
  records, concurrent appends, symlink/path replacement, and repository-address spoof attempts;
- make disarm behavior symmetric for generated host skills and document residual files;
- expand the security policy to cover local credential reads, bus metadata/text, hook injection,
  screenshot/JSON exposure, and same-user trust assumptions.

## Revisit trigger

Consider a first-class engineer adapter only after llmquota exposes a stable structured-envelope CLI
or JSON schema. Even then, the adapter should translate pointers; it should not import collectors,
mailbox storage, or hook management.

engineer now ships a transport-neutral coordination-envelope receipt and validator. This does
not change that ownership decision: llmquota may later emit the envelope, while engineer validates
its orchestration/delegation/artifact meaning independently.

Follow-up hardening validates the referenced orchestration contract with its canonical validator,
checks the artifact against the receiver's declared output schema, and enforces observation/send/
receive/acknowledgment/review chronology. Hash agreement alone is no longer sufficient.
