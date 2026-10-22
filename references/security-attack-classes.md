# Security attack classes (hunting catalog)

**Last verified**: 2026-10-22 · **Review cadence**: 2 months

Loaded by every hunter and verifier in an `engineer security-audit` wave, next to the matching
section of `security-audit-domains.md`. `security-audit.md` owns the verb's contract, phases,
verdicts, and validators; this catalog owns what to look for and what it takes to confirm it.
The eight class names are the `attack_class` enum and the only values a unit, candidate, or
record may carry. Each class gives hunting questions (ask them of every assigned path) and a
validation rule (what a verifier must show before `confirmed`).

Defensive-documentation note: this catalog names execution sinks and decoders as taxonomy words,
never as call syntax, and keeps encoder and sink vocabulary apart so the repository's leak gate
(`check-oss-leaks.sh`) stays clean; `malware-detection.md` carries the same discipline.

## Contents
- [Using the catalog](#using-the-catalog)
- [Injection](#injection)
- [Access control](#access-control)
- [Resource and file handling](#resource-and-file-handling)
- [Cryptography and secrets](#cryptography-and-secrets)
- [Business logic](#business-logic)
- [Feature abuse and data leakage](#feature-abuse-and-data-leakage)
- [Chained trust boundaries](#chained-trust-boundaries)
- [Wildcard](#wildcard)
- [Obvious-things checklist](#obvious-things-checklist)
- [Validation rules by class](#validation-rules-by-class)
- [Anti-patterns](#anti-patterns)

## Using the catalog

1. Read the assigned paths in full before asking any question; skimming is where findings hide.
2. Write each answer as observed (file and symbol cited), inferred, assumed, or unknown. An
   unknown becomes an `uncovered` unit with a reason, never silence.
3. A "yes" to a hunting question is a **candidate**, not a finding. Draft the five boundary
   fields and a trace; the verifier owns the verdict.
4. Record every path read in `reviewed_paths` and every check in `checks[]`, including those
   that found nothing: a `covered` unit with no candidate is the audit's main product.
5. Name the sink precisely in `root_cause.sink`: the query builder call, the file API, the
   process spawn, the template render, the response writer. Fingerprints depend on it.

## Injection

`attack_class: injection`. Untrusted bytes reach an interpreter that gives them meaning.

Hunting questions:
- Where does request, message, file, or environment input reach a SQL or NoSQL query string, an
  ORM raw fragment, a shell argument list, a template engine, an expression language, a regular
  expression compiled at runtime, an LDAP or XPath filter, a log line, or a response header?
- Which parameterized layer exists, and which call sites step around it (string formatting into
  a query, a raw-query escape hatch, dynamic column or table names, `ORDER BY` from input)?
- Which encoder or validator is on the path, and does it match the sink's grammar (HTML encoding
  before a shell, URL encoding before SQL, a denylist where the grammar needs a parser)?
- Where is dynamic code evaluation present at all: JavaScript `eval` or `new Function`, the `vm`
  module, dynamic `import` of a computed specifier, Python `exec`, `compile`, or `__import__`,
  shell spawning through `child_process` or `subprocess` with a string command, PowerShell
  expression invocation or encoded-command flags? Any reachable one is a candidate on its own.
- Does a second-order path exist: stored input later read into a query, a job, or a template?

Validation: the verifier shows the exact byte path from an entrypoint to the sink with no
neutralizing step, or a concrete bypass of the step that exists. Parameterization, a typed schema
that cannot carry the payload, or an allowlist on the path refutes the candidate unless the
bypass is shown. "Looks like string concatenation" without the string's source is rejected.

## Access control

`attack_class: access_control`. A principal acts beyond its authority.

Hunting questions:
- Enumerate every route, action, handler, job, and RPC method. For each: which check runs before
  the body, where does it run (middleware, decorator, inline, database policy), and which routes
  lack it? The one route without the interceptor is the finding.
- Object level: does the handler load the resource by an id from input and then check that the
  principal owns it, or does it trust the id? Which queries lack a tenant or owner predicate?
- Function level: which admin, export, impersonation, billing, or configuration operations are
  gated only by UI visibility, a client-side flag, or a role string the client sends?
- Mass assignment: which update paths bind request bodies to models with privileged fields
  (role, tenant, price, verified, owner) without an allowlist?
- Token scope: which tokens, API keys, or sessions are accepted where a narrower audience, scope,
  tenant, or lifetime was intended? Which refresh or recovery flow mints broader authority than
  the credential that started it?
- Database policies: is row-level security enabled on every tenant table, do policies use the
  authenticated principal rather than a client-supplied claim, and does any server path use a
  service-role connection for user-driven requests?

Validation: name the principal, show the check that is absent or bypassed on the exact path, and
show the resulting read or write with its scope. A client-side-only check is confirmed when the
server path lacks the equivalent; a missing check behind a layer that still enforces (RLS,
gateway policy) is a hardening note naming that layer.

## Resource and file handling

`attack_class: resource_handling`. Paths, URLs, archives, and serialized objects from outside.

Hunting questions:
- Path traversal: which file reads, writes, deletes, or includes take a name from input, and is
  the resolved path checked against a base directory after normalization and symlink resolution?
- Server-side request forgery: which server code fetches a URL, host, or port from input, from a
  stored record, from a webhook payload, or from a document URL? Does validation run before or
  after redirects, DNS resolution, and scheme changes? Can it reach loopback, the link-local
  metadata address, internal services, or file-scheme targets?
- Deserialization: which endpoints or queues accept serialized objects, pickles, YAML with tags,
  XML with entities, or signed-but-not-encrypted blobs where the signature check can be skipped
  or the type is attacker-chosen?
- Archives: does any upload or import extract archives without rejecting absolute paths, `..`
  entries, symlinks, oversized members, or nested archives?
- Time-of-check to time-of-use: where is a permission, existence, size, or hash checked on one
  handle and the operation performed on another (path re-resolved, file re-opened, re-fetched)?
- Uploads and temp files: where are content type, size, name, and location decided by the
  client; where are temp files predictable, world-readable, or left behind?

Validation: show the exact resolution or fetch call, the input that controls it, the missing or
bypassable check, and the target reached (a path outside the base, an internal host). SSRF whose
reachability depends on an unknown egress rule is `needs_validation` with a `network_routing`
blocker, a local plan (sandbox with a fake upstream), and an owner-observed plan.

## Cryptography and secrets

`attack_class: crypto_secrets`. Keys, randomness, comparisons, and credential handling.

Hunting questions:
- Which algorithms and modes serve hashing, signing, encryption, and password storage? Flag
  unsalted or fast password hashes, static IVs or nonces, non-authenticated encryption,
  home-grown constructions, and secret comparison with early-exit equality.
- JWT and signed tokens: is the algorithm pinned server-side, is `none` rejected, are issuer,
  audience, expiry, and key id validated, can a public key be supplied as an HMAC secret, is the
  verification key chosen from token content?
- Randomness: which tokens, ids, reset codes, invite links, or session ids come from a
  non-cryptographic generator, a timestamp, or a predictable counter?
- Key lifecycle: where do keys live, who can read them, how are they rotated, and does any code
  path log, echo, or send them (error pages, debug endpoints, client bundles, URLs)?
- Secrets in the tree: committed env files, private-key material, provider-prefixed tokens,
  connection strings with passwords, fixture tokens that reach production configs.

Validation: a weak primitive is confirmed only with a shown consequence (a forgeable token, a
recoverable secret, a predictable id that grants access). A committed secret is confirmed when it
is live-shaped and reaches a real system path; a placeholder or rotated value is a hardening
note. Never test a found credential against anything.

## Business logic

`attack_class: business_logic`. The code does what it says, and what it says is exploitable.

Hunting questions:
- State machines: which transitions are enforced by code and which only by UI order? Can a step
  be skipped, repeated, or performed after a terminal state (pay after refund, approve after
  reject, verify before upload)?
- Check-then-act races: where is a balance, quota, inventory, uniqueness, or one-time token
  checked and then consumed without a lock, a conditional update, or an idempotency key?
- Numeric and time logic: negative quantities, zero or fractional prices, integer overflow,
  rounding direction on money, currency mixing, expiry compared in the wrong time zone, clocks
  taken from the client.
- Defaults mid-migration: a feature flag, schema column, or config default that leaves a window
  where the new check is absent and the old one already removed.
- Trust in client state: prices, discounts, roles, step results, or totals taken from the request
  rather than recomputed from the server record.

Validation: show the sequence of requests or events, the state before and after, and the gain.
A race is confirmed only with both interleavings named at the code level and the conditional
update shown absent; a database constraint that rejects the second write refutes it.

## Feature abuse and data leakage

`attack_class: feature_abuse`. Intended features that return more than they should.

Hunting questions:
- Export and import: which exports include fields the UI hides, other tenants' rows, soft-deleted
  data, or secrets; which imports accept references to objects the importer cannot read?
- Search, filter, and sort oracles: can a filter on a hidden field reveal its value through result
  presence, ordering, count, or timing?
- Enumeration: which responses, timings, or error messages distinguish an existing user, tenant,
  file, or invite from a missing one?
- Preview, draft, share, and signed URL tokens: lifetime, scope, revocation, and whether the token
  alone suffices without the principal.
- Server-side fetch features (link previews, image proxies, webhooks on save, PDF rendering) that
  act with the server's network identity.
- Notifications, emails, logs, analytics events, and error responses that carry data across a
  boundary (another tenant, a third party, a public channel).

Validation: show the request, the field or row that crosses the boundary, and the rule in the
brief's Protected resources that it violates. Volume sets impact; "could be scraped" without a
shown boundary crossing is a hardening note.

## Chained trust boundaries

`attack_class: chained_trust`. Each hop is weak only together.

Hunting questions:
- Which internal services, jobs, webhooks, and admin tools accept input from another component
  without re-validating because "it is internal"? Where does an external principal reach that
  component through the first one?
- Which headers (forwarded host, client address, user id, role) are trusted behind a proxy, and
  can a direct caller set them?
- Which shared secrets, service accounts, or static tokens let one compromised component act as
  every other?
- Where does a low-impact primitive on one side (open redirect, stored text, file write) become
  high impact with a trusted hop (SSO callback, template include, config reload)?

Validation: one record per chain, a trace covering every hop, impact from the final hop, and
each intermediate control shown absent or bypassed. A chain with one unverified hop is
`needs_validation` with that hop as the blocker.

## Wildcard

`attack_class: wildcard`. What no checklist asks.

Hunting questions:
- Odd or half-finished code: dead branches, commented-out checks, "temporary" bypasses,
  `TODO`/`FIXME` near auth or money, duplicated handlers where one copy lost its guard.
- Hidden routes: debug, health, metrics, admin, GraphQL introspection, old API versions,
  feature-flagged paths still mounted.
- Feature interactions: two safe features whose combination is unsafe (file upload plus
  server-side rendering; impersonation plus audit-log suppression; API keys plus rate-limit
  exemption).
- Git history: a check removed in a refactor, a security fix reverted by a merge, a secret
  committed then deleted but still in history, a test deleted with the feature it guarded.
- Environmental assumptions: code that is safe only with a specific proxy, header, flag, or
  deployment topology the brief could not confirm.
- Test gaps: security-relevant paths with skipped, mocked-through, or absent tests.

Validation: the rules of the class the candidate turns out to belong to. Re-label
`attack_class` to that class before verification when it fits; keep `wildcard` only for
candidates that fit none.

## Obvious-things checklist

Run the deterministic part first (`bash "$ENGINEER/scripts/engineer-scan.sh" --strict` for
policy, `bash "$ENGINEER/scripts/check-oss-leaks.sh" --all` for secrets, droppers, and hidden
unicode), then read each hit in context.

| Item | Where to look |
|---|---|
| Secrets and credentials in source, config, fixtures, history | env files, config, tests, CI, git log |
| Security `TODO`/`FIXME`/`XXX`, "temporary", "bypass" | grep, then the surrounding handler |
| Debug and diagnostic gating | debug flags, verbose errors, profiler and admin endpoints, stack traces in responses |
| Test credentials and default accounts | seeds, fixtures, compose files, first-run code |
| Committed secret-bearing files | env files, key and certificate files, keystores, cloud CLI credential files, kubeconfigs |
| Dependency pins and known vulnerabilities | lockfiles, floating versions, advisories for the pinned versions, lifecycle scripts |
| Dynamic execution and code loading | the sinks named under Injection, plugin loaders, template includes |
| CORS, cookies, redirects, TLS, verbose errors | origin allowlists with credentials, cookie flags, open-redirect parameters, TLS verification disabled, error detail in responses |

**Binding rule: a flag alone is not a finding.** Every hit becomes a candidate only after the
full code path is read: who can reach it, which control sits in front, and what it yields. A
debug endpoint behind a working admin gate is a hardening note. A `TODO` next to a check that is
present is nothing. A pinned dependency with a published advisory is a finding only when the
vulnerable function is reachable from an entrypoint in this codebase; otherwise it is a hardening
note naming the upgrade.

## Validation rules by class

| Class | Confirmed needs | Refuted by |
|---|---|---|
| `injection` | entrypoint → sink byte path, no neutralizing step or a shown bypass | parameterization, typed schema, allowlist on the path |
| `access_control` | principal, absent or bypassed check on the path, resulting read/write scope | an enforcing layer behind the gap (then: hardening note) |
| `resource_handling` | controlling input, the resolution or fetch call, the reached target | post-normalization base check; egress policy shown in code or config |
| `crypto_secrets` | the weak primitive plus its consequence; a live-shaped reachable secret | placeholder or rotated value; consequence not reachable |
| `business_logic` | sequence, state before and after, the gain; both race interleavings | constraint or conditional update that rejects the second path |
| `feature_abuse` | request, crossing field or row, Protected-resources rule it violates | data is public by the brief; principal already owns it |
| `chained_trust` | every hop traced, each control absent or bypassed, impact from the last hop | any hop's control holds (then: that hop is the blocker) |
| `wildcard` | the rules of the class it maps to | the same |

## Anti-patterns

- Reporting grep hits, scanner output, or an advisory id as findings.
- Inventing an entrypoint ("an attacker who already has code execution could...").
- Grading severity in the hunter result; severity belongs to the verified record.
- Describing a sink by file name only; the symbol and call are part of the fingerprint.
- Stopping at the first candidate in a unit; the unit is covered only when every path is read.
- Treating "no test covers this" as a vulnerability by itself.
- Testing a discovered credential, token, or URL against any live system.

**Related**: `security-audit.md`, `security-audit-domains.md`, `malware-detection.md`,
`backend-security.md`, `backend-auth.md`, `ai-security.md`
