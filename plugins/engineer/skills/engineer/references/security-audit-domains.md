# Security audit domain companions

**Last verified**: 2026-10-22 · **Review cadence**: 2 months

Loaded per coverage unit by the `domain` the ledger assigns: `web_auth`, `client_side`,
`ai_agent`, `supply_chain`, `cloud_infra`, `protocols_messaging`, `availability`,
`data_isolation`, or `null` when a unit fits none. Each companion turns the eight classes of
`security-attack-classes.md` into the questions that matter on that surface and names the
Engineer module that owns depth; read that module when a candidate needs mechanism detail, not
before. `security-audit.md` owns the verb contract and verdicts; nothing here relaxes a
validation rule, the sandbox policy, or the independence rules.

## Contents
- [Shared rules](#shared-rules)
- [web_auth: HTTP, sessions, identity](#web_auth-http-sessions-identity)
- [client_side: browser code and messaging](#client_side-browser-code-and-messaging)
- [ai_agent: LLM, agent, and MCP surfaces](#ai_agent-llm-agent-and-mcp-surfaces)
- [supply_chain: CI, release, plugins](#supply_chain-ci-release-plugins)
- [cloud_infra: IAM, containers, config](#cloud_infra-iam-containers-config)
- [protocols_messaging: RPC, queues, webhooks](#protocols_messaging-rpc-queues-webhooks)
- [availability: resource exhaustion](#availability-resource-exhaustion)
- [data_isolation: tenancy and lifecycle](#data_isolation-tenancy-and-lifecycle)
- [Anti-patterns](#anti-patterns)

## Shared rules

- Each companion lists **use when**, the **core discipline**, the **classes** as they appear on
  that surface, **universal moves** (do them for every unit in the domain before any class
  question), **validation rules**, the usual **confirmed vs needs-validation** split with its
  blocker kinds, and the **depth** module.
- Label every statement in a hunter result observed (file and symbol), inferred, assumed, or
  unknown. A domain companion never supplies facts about the target; it supplies questions.
- Everything the companion says about live systems is read from code and config in the tree.
  No companion authorizes a request to a deployed host, a cloud API, a provider console, or a
  model endpoint; those facts are blockers with owner-observed steps.

## web_auth: HTTP, sessions, identity

- **Use when**: `http` or `webhook` surfaces reached by browsers or API clients; sessions,
  tokens, OAuth, OIDC, SAML, MFA, passkeys, recovery, API keys, mTLS, framing, caching.
- **Core discipline**: every request is anonymous until a server-side check binds it to a
  principal. Find the route where that binding is missing, late, or client-controlled. Cookie
  attributes, cache keys, and frame control are part of the control, not polish.
- **Classes**: `access_control` (route without the interceptor; resource ids without an owner
  predicate; role read from a client claim instead of the record; recovery or refresh minting
  broader authority; API keys without tenant scope); `crypto_secrets` (JWT algorithm and key
  selection, refresh rotation without reuse detection, session fixation, reset-token entropy and
  lifetime, passkey challenge binding to origin and relying party); `injection` (header and
  CRLF, host header in reset links, log lines); `feature_abuse` (enumeration on login, reset,
  invite; authenticated responses cached by a shared cache or CDN); `business_logic` (OAuth
  state, PKCE, redirect allowlist; SAML assertion audience and replay; MFA step order; recovery
  versus lockout interplay); `chained_trust` (forwarded headers trusted behind a proxy; mTLS
  terminated at the edge with a plaintext internal hop).
- **Universal moves**: enumerate every route with its auth gate; trace session issue →
  validate → revoke; map every token's issuer, audience, scope, lifetime, and rotation; read
  each identity callback end to end; check cookie flags, the CSRF model, CORS with credentials,
  cache headers on authenticated responses, and frame control.
- **Validation rules**: show server-side absence of the control. A client-only check is
  confirmed when the server lacks the equivalent. A missing CSRF token on a JSON-only API with a
  custom request header and `SameSite=Strict` is a hardening note. An open redirect is confirmed
  alone only at low impact; higher impact needs the shown chain to a token or session.
- **Confirmed vs needs validation**: identity-provider settings, edge and CDN behavior, and
  production cookie domains are `configuration` or `deployment` blockers; everything in code is
  confirmed or rejected.
- **Depth**: `backend-auth.md` (interceptor, claims versus user lookup, Server Actions as public
  endpoints), `backend-security.md` (headers, CSP, cookies, CSRF).

## client_side: browser code and messaging

- **Use when**: `ui` surfaces: SPA and SSR components, DOM sinks, cross-window messaging,
  service workers, web storage, iframes, extensions, third-party scripts.
- **Core discipline**: the browser is the attacker's machine; a control that runs only there
  protects nothing server-side. Hunt the DOM sinks, the message handlers, and every crossing of
  an origin boundary.
- **Classes**: `injection` (DOM XSS through raw-HTML sinks, framework escape hatches, URL
  attributes with script schemes, markdown and rich-text renderers, SVG served inline);
  `access_control` (message handlers without an origin check; service worker fetch handlers
  serving cached private responses to any client; tokens in web storage reachable by any script);
  `feature_abuse` (cross-site leaks through timing, frame counting, error events, cache probing;
  referrer and prefetch leaks); `business_logic` (UI redress on state-changing pages without frame
  control; drag-and-drop and cursor tricks); `chained_trust` (a CSP that admits inline or wide
  script sources turning text injection into script; third-party scripts with full origin
  authority); `resource_handling` (client-side URL parsing that disagrees with the server's; open
  redirects in route parameters).
- **Universal moves**: list every DOM sink and every source feeding it; list message handlers
  and their origin checks; read the CSP as code; list what service workers cache and for whom;
  enumerate storage keys and the scripts that can read them.
- **Validation rules**: DOM XSS is confirmed with source → sink and the framework's escaping
  shown absent or bypassed in the version in use. A text injection that the CSP would stop is a
  hardening note unless the bypass is shown. A cross-site leak needs the oracle and the protected
  fact named. UI redress is confirmed only on a state-changing action with no frame control and
  no second factor.
- **Confirmed vs needs validation**: CSP or headers delivered by the edge and third-party script
  content are `deployment` or `third_party_dependency` blockers.
- **Depth**: `frontend.md`, `browser-agent-security.md` (source-to-sink rules for agent-driven
  browsers), `backend-security.md` (CSP sections).

## ai_agent: LLM, agent, and MCP surfaces

- **Use when**: the target calls a model, runs an agent loop, exposes or consumes tools, MCP
  servers, skills, retrieval, or durable memory.
- **Core discipline**: prompt injection alone is not a finding. The model is an untrusted
  component; a finding exists when a code-level boundary fails: the tool layer executes what
  content asked for without authorization, an approval is not bound to the action executed, a
  destination is not allowlisted in code, memory accepts writes from content. Guardrail prompts
  and classifiers are not boundaries; cite the code that would have to hold.
- **Classes**: `access_control` (tool authority derived from content; confused deputy, where the
  agent spends the user's session on content-chosen targets; approval binding, where arguments
  change after approval; over-scoped agent credentials); `injection` (tool arguments built from
  model output into shells, queries, or URLs; tool descriptions carrying imperatives);
  `resource_handling` (fetch tools reaching internal hosts; file tools without root confinement);
  `feature_abuse` (exfiltration through URL parameters, image loads, tool arguments, logs; the
  private-data, untrusted-content, external-sink trifecta present at once); `business_logic`
  (who can write durable memory and whether a write from content is gated; cross-session
  persistence; loops without budgets); `chained_trust` (agent-to-agent messages treated as
  delegations; a sub-agent inheriting more than its parent; transport messages as approval).
  Skill, plugin, and server admission belong to `supply_chain`.
- **Universal moves**: map every path from untrusted content (web, files, tool results,
  messages, memory) to every side-effecting tool; find the code that authorizes each tool call
  and which inputs it uses; check approval → execution binding; check memory write gates; check
  egress allowlists in the tool layer, not in prompts.
- **Validation rules**: `confirmed` needs the content → tool → effect path with the missing code
  control named, shown in the sandbox with a replayed model response and no live model call. A
  candidate that rests on model behavior ("the model would follow this") without a code-level gap
  is rejected or a hardening note. A destination allowlist enforced in the tool layer refutes an
  exfiltration candidate.
- **Confirmed vs needs validation**: hosted-platform permission settings, provider-side policy,
  and deployed tool allowlists are `configuration` or `third_party_dependency` blockers.
- **Depth**: `ai-security.md`, `mcp-security.md`, `agent-memory.md`; `agent-red-teaming.md` for
  authorized live testing after the audit (this verb reads code; red-team runs attacks).

## supply_chain: CI, release, plugins

- **Use when**: build, CI, release, signing, update channels, plugin and skill loading,
  dependency install, container image build, scaffolds and templates.
- **Core discipline**: the question is who can get code executed in a trusted context: a
  contributor, a dependency maintainer, a registry, a mutable tag, a template author. Read the
  always-read surfaces in `malware-detection.md` in full.
- **Classes**: `access_control` (workflows that run on attacker-authored events with secrets or
  write tokens in scope: `pull_request_target`, `workflow_run`, comment triggers that check out
  fork code; broad default token permissions; environments without protection rules);
  `chained_trust` (actions, images, and base images pinned by mutable tag; lockfile not enforced;
  lifecycle scripts; floating package runners; update channels without signature verification;
  plugin loaders running code from a user-controlled path); `crypto_secrets` (release signing
  keys in CI environment variables; unverified checksums; a signature checked but the identity
  not pinned); `injection` (expression interpolation of titles, branches, or bodies into
  workflow steps; shell steps interpolating event data; build scripts interpolating environment);
  `resource_handling` (artifact downloads extracted without path checks; cache poisoning across
  branches); `wildcard` (obfuscated or hidden-unicode content in config, hooks, agent config).
- **Universal moves**: list every trigger × secret × checkout combination; diff declared against
  resolved dependencies; check pinning by digest; read lifecycle scripts, hooks, and editor or
  agent config; run `check-oss-leaks.sh` and `scan-doc-supply-chain.py` over the tree.
- **Validation rules**: a CI finding is confirmed when the trigger, the attacker-controlled
  input, the secret or permission in scope, and the step that uses the input are all shown in
  the workflow file. A mutable pin alone is a hardening note unless the pinned content is shown
  attacker-controllable. A dropper shape is confirmed only with encoder, sink, and delivery read
  in context, never from a regex hit.
- **Confirmed vs needs validation**: repository settings not visible in code (branch protection,
  required reviewers, environment secrets, default token permissions) are `configuration`
  blockers with an owner-observed step.
- **Depth**: `skill-supply-chain.md`, `malware-detection.md`, `oss-maintainer.md`,
  `git-signing-deploy.md`, `enforcement.md`.

## cloud_infra: IAM, containers, config

- **Use when**: IaC, IAM policies, ingress and network config, container and orchestration
  manifests, serverless config, config and secret lifecycle, object storage, event wiring, edge
  rules.
- **Core discipline**: the code is the deployment. Hunt wildcard principals and actions, public
  exposure of private things, and secrets whose lifecycle is "forever in an environment
  variable". Never confirm by calling a provider; read IaC, manifests, and config in the tree.
- **Classes**: `access_control` (IAM wildcards; role trust policies open to any account; public
  or cross-account buckets, queues, topics; one service account shared across workloads; the
  instance metadata endpoint reachable from a workload that handles untrusted input);
  `crypto_secrets` (secrets in IaC state, environment, images, or logs; no rotation path; open
  key-management policies); `resource_handling` (containers as root or privileged, host mounts,
  the container runtime socket, writable root filesystems, added capabilities); `feature_abuse`
  (event wiring where one tenant's event triggers another's processing; edge rules that bypass
  application auth for a path); `chained_trust` (no network policy, so one compromised workload
  reaches everything; ingress trusting forwarded headers); `business_logic` (config defaults
  mid-migration: two environments, one still on the old policy).
- **Universal moves**: enumerate principals and their policies from IaC; enumerate every public
  endpoint from ingress, load balancer, and DNS config; enumerate every secret source and its
  consumers; read each container security context; diff environments for drift.
- **Validation rules**: `confirmed` needs the policy or manifest text, the principal or workload
  it exposes, and the result. "The policy allows X" without a reachable principal is a hardening
  note. A metadata-credential chain needs the application-side SSRF confirmed first.
- **Confirmed vs needs validation**: anything that depends on live account state (what is
  deployed, console-made changes, provider defaults) is a `deployment` blocker; IaC drift is a
  hardening note.
- **Depth**: `infra-security.md`, `cloud-aws.md`, `cloud-gcp.md`, `cloud-vercel.md`,
  `cloud-platforms-iac.md`.

## protocols_messaging: RPC, queues, webhooks

- **Use when**: `rpc`, `message`, `webhook`, and `job` surfaces: gRPC, JSON-RPC, GraphQL, queues,
  pub/sub, inbound and outbound webhooks, scheduled jobs, idempotency, replay.
- **Core discipline**: a message is input from whoever can put it on the channel. Authenticate
  the producer, bind the message to one intended effect, and make the effect idempotent. Find
  where the consumer trusts the channel instead of the message.
- **Classes**: `access_control` (webhook handlers without signature verification, or with it
  after side effects; signatures without a timestamp or replay window; consumers acting on a
  tenant id from the payload; GraphQL resolvers with field-level gaps; batching and aliases
  bypassing per-operation limits); `business_logic` (idempotency keys missing or scoped globally
  instead of per principal on money, notification, or provisioning handlers; at-least-once
  delivery applied twice; reordering; retries re-running side effects); `injection` (RPC
  arguments into shells or queries; schema-less payloads); `chained_trust` (internal RPC without
  authentication because "the network is private"; identity claims forwarded in headers);
  `resource_handling` (payload size, recursive schemas, batch depth); `feature_abuse` (outbound
  webhooks to user-supplied URLs acting with the server identity; introspection exposing hidden
  fields).
- **Universal moves**: for each inbound channel: who can produce, how the producer is
  authenticated, where the check sits relative to effects, replay protection, idempotency; for
  each outbound: destination control, secret handling, retry semantics; read the schema for
  authorization gaps per field and method.
- **Validation rules**: webhook forgery is confirmed with the handler path, the missing or
  post-effect verification, and the effect. Replay is confirmed with the absent window and a
  side effect that is not idempotent. GraphQL authorization is confirmed per resolver path.
- **Confirmed vs needs validation**: producer identity enforced by the broker or gateway rather
  than code is a `configuration` blocker; presence of signing secrets in production is
  `deployment`.
- **Depth**: `backend-webhooks.md`, `background-jobs.md`, `backend-api.md`.

## availability: resource exhaustion

- **Use when**: any surface where one principal can consume shared capacity: parsers, uploads,
  regular expressions, pagination, fan-out, retries, queues, model calls, metered spend.
- **Core discipline**: never validate by stressing shared services. Confirm from code (an
  unbounded loop, a missing limit, an amplification factor) or in the sandbox against a local
  instance under the run's CPU, memory, and wall limits.
- **Classes**: `resource_handling` (unbounded body, file, or archive size; decompression bombs;
  recursive parsing; regular expressions with catastrophic backtracking on input; pagination
  without a maximum; list parameters without a cap); `business_logic` (retry amplification;
  fan-out without caps; unbounded concurrency per principal; no rate limit on expensive or paid
  operations such as email, SMS, or model calls); `access_control` (rate limits keyed on
  client-controlled values; limits bypassable through an alternate route); `chained_trust` (a
  cheap request that enqueues an expensive internal job).
- **Universal moves**: list every limit (size, count, depth, time, concurrency, spend) and find
  the surface that lacks one; compute amplification (bytes in against work out); check what a
  single principal can queue.
- **Validation rules**: `confirmed` needs the code path, the missing or bypassable limit, and a
  computed or sandbox-measured amplification. "Could be slow" without a factor is a hardening
  note.
- **Confirmed vs needs validation**: limits enforced by an edge, gateway, or autoscaler not
  visible in code are `deployment` blockers; provider cost ceilings are `configuration`.
- **Depth**: `backend-api.md` (limits), `observability.md`, `agent-red-teaming.md`
  (denial-of-wallet class).

## data_isolation: tenancy and lifecycle

- **Use when**: multi-tenant data, derived copies (search indexes, caches, analytics, backups,
  logs), export and restore, deletion and revocation, retention.
- **Core discipline**: isolation holds only if every copy and every path enforces it. Follow a
  tenant's row into every derived store and every egress; follow a deletion or revocation until
  nothing is left or you can name what remains.
- **Classes**: `access_control` (a tenant predicate missing in one query, index, cache key, or
  report; RLS off on a table or bypassed by a service role; cross-tenant ids accepted in joins);
  `feature_abuse` (exports with other tenants' rows; a search index returning cross-tenant hits;
  shared caches keyed without the tenant; analytics events carrying another tenant's data);
  `business_logic` (restore overwriting newer data or reviving revoked access; deletion that
  misses derived copies, backups, queues, or logs; revocation not propagated to long-lived
  sessions, tokens, or shares; retention timers from client time); `crypto_secrets` (one key for
  every tenant where per-tenant keys were promised); `chained_trust` (background jobs running
  with a global identity across tenants).
- **Universal moves**: enumerate tenant tables and the predicate on every read and write path;
  enumerate derived stores and their keying; trace export, restore, delete, and revoke end to
  end; list every path that uses a service-role or bypass connection.
- **Validation rules**: a cross-tenant read is confirmed with the query or index lookup, the
  missing predicate, and the resulting row. A deletion gap is confirmed by naming the store where
  data persists after the delete path completes. A revocation gap is confirmed with the token or
  session lifetime and the missing check.
- **Confirmed vs needs validation**: backup retention, provider-side deletion, and replica lag
  are `deployment` or `data` blockers with owner-observed steps.
- **Depth**: `backend-multitenant.md`, `backend-database.md`, `audit-log.md`,
  `compliance-privacy.md`.

## Anti-patterns

- Loading every companion for every unit; the ledger assigns one domain per unit.
- Promoting prompt injection to a finding without a failing code-level boundary.
- Confirming cloud exposure by calling the provider, or availability by generating load.
- Treating a provider or dashboard setting you cannot see as present or absent; it is a blocker.
- Pasting a depth module into the hunter prompt wholesale; load it for a candidate.

**Related**: `security-audit.md`, `security-attack-classes.md`, `backend-auth.md`,
`backend-security.md`, `ai-security.md`, `mcp-security.md`, `skill-supply-chain.md`,
`infra-security.md`, `backend-multitenant.md`
