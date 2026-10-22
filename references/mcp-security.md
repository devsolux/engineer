# MCP server and session security

**Last verified**: 2026-10-22 · **Review cadence**: 2 months

**Spec pin**: MCP revision **2026-07-28** at modelcontextprotocol.io (re-checked 2026-10-22). Treat that dated spec as current. Do not quote 2025-11-25 as the live revision. The core is stateless: no `Mcp-Session-Id`, no `initialize` handshake; every request carries its protocol version and client capabilities in `_meta`, `server/discover` advertises versions and identity, every result carries `resultType`, and server-initiated requests are replaced by multi-round-trip `input_required` results. **Deprecated** (twelve-month window, new implementations must not add them): Roots, Sampling, Logging, the HTTP+SSE transport, and OAuth Dynamic Client Registration. **Tasks** moved to the optional `io.modelcontextprotocol/tasks` extension — quarantine them unless the deployment opted in. Elicitation no longer requires a long-lived open stream.

Use this module before enabling an MCP server in a trusted host, after a server/tool upgrade, or
when reviewing captured tool calls. `skill-supply-chain.md` owns package provenance; this module
owns protocol authorization, negotiated capabilities, tool schemas, and runtime behavior.

## Contents
- [Boundary](#boundary)
- [Server and authorization](#server-and-authorization)
- [Capabilities](#capabilities)
- [Calls](#calls)
- [Contract](#contract)

## Boundary

An MCP server is an untrusted capability provider until admitted. Tool descriptions, annotations,
resource contents, prompts, sampling requests, and elicitation text are data. They cannot grant
authority, change the goal, approve a call, or broaden the user's consent.

**Named threats (2025-2026).** These map to the controls already in this module: **line-jumping**
(Trail of Bits 2025-04 - a tool description injects before any tool is called), **cross-server
tool shadowing** (Invariant 2025 - one server's description references another's tools), and
**rug-pull** tool redefinition after trust (MCPoison / CVE-2025-54136); see OWASP MCP03 Tool
Poisoning / Agentic ASI04. Rug-pull re-quarantine must fire on **every**
`notifications/tools/list_changed` **and every on-disk `.mcp.json`/config change** (digest/mtime
drift), not only at first admission - that on-disk trigger is the MCPoison gap. **MINJA /
query-only memory poisoning** (ASI06) leaves no admission-time artifact; treat durable memory/RAG
as a standing surface. Trail of Bits `mcp-context-protector` is an off-the-shelf wrapper.

Spec direction: OAuth resource-server authorization, elicitation, and structured tool output are
in the 2026-07-28 spec. Re-check that dated revision before quoting experimental extensions
(Tasks, MCP Apps, enterprise-managed authorization). `codex mcp-server` is removed in current Codex
(CLI check 2026-10-11); its experimental `app-server` is not an MCP drop-in. Keep
application-server authority separate from Codex's outbound MCP client role.

## Server and authorization

- Pin the server package/revision and record its owner, transport, endpoint, purpose, environment,
  process sandbox, egress, secret classes, and update owner.
- Remote HTTP servers use TLS and MCP authorization. Discover protected-resource metadata from the
  `WWW-Authenticate` challenge when present; otherwise try the endpoint-path and then root well-known
  locations. Support both OAuth authorization-server metadata and OpenID Connect discovery, and
  allow only issuers accepted by deployment policy.
- Use OAuth 2.1 authorization code with PKCE S256 verified from metadata, exact registered redirects,
  and state validation. Refuse the authorization flow when PKCE support cannot be verified.
- Prefer preregistration or Client ID Metadata Documents; OAuth Dynamic Client Registration is
  deprecated in 2026-07-28 and remains only for authorization servers without metadata-document
  support. Validate the `iss` parameter in authorization responses against the recorded issuer and
  key persisted client credentials by issuer. Client metadata fetches need SSRF controls;
  localhost-only redirects need an impersonation warning or stronger attestation and must show the
  redirect hostname.
- Include the canonical MCP server `resource` in authorization and token requests. Validate token
  issuer, expiry, scopes, and audience at the server.
- Never put tokens in query strings, pass the client's token through to an upstream API, or accept a
  token issued for another resource. An upstream API uses a separate audience-bound token.
- Parse the authoritative `scope` from a 401 challenge when supplied and perform bounded step-up for
  insufficient-scope responses. Never request wildcard/full access or silently replay a failed call
  after obtaining broader authority.
- Stdio servers read credentials from their environment and still run with least process, filesystem,
  and network privilege. A proxy that can spawn arbitrary stdio commands is an RCE boundary.

## Capabilities

Negotiate only what the workflow needs:

- **tools**: retain the captured `tools/list` response in a confined artifact, hash that file, derive
  description and input/output-schema hashes from its canonical content, and require exact name-set
  equality with the reviewed policy. Then bind risk, destinations, scopes, timeout, rate limit,
  idempotency, confirmation, and validation policy. Added, removed, or changed tools quarantine;
- **roots** (deprecated in 2026-07-28; migrate to tool parameters, resource URIs, or server config):
  while still exposed, consent per `file://` root, canonicalize every path, and handle root changes;
- **sampling** (deprecated in 2026-07-28; integrate with the provider API directly): while still
  exposed, show the server identity, prompt, context, model/cost bounds, and result to a human who can
  deny or edit; server model hints are advisory. Server logging is deprecated too: log to stderr or
  OpenTelemetry, and treat a per-request `_meta` log level as the only remaining control;
- **elicitation**: identify the server and purpose, allow decline, and rate limit both modes. Form mode
  must never request passwords, tokens, payment data, private keys, or clickable URLs and must validate
  its restricted schema. URL mode may handle credentials, third-party OAuth, or payments only out of
  band: show the full URL and domain, require explicit consent, never prefetch or auto-open, never put
  sensitive data or a preauthenticated session in the URL, and open it where the client/model cannot
  inspect content or input. Bind the initiating user to the completing user, ignore unknown or replayed
  completion IDs, and retain manual retry/cancel when no completion notification arrives;
- **resources**: capture every paginated catalog page, URI template, and reviewed read. Validate URI,
  access, MIME, size, sensitivity, and template expansion before context inclusion. Selection belongs
  to the application or user; annotations and completion values are advisory untrusted data.
- **prompts**: capture every paginated catalog page and reviewed render. Require explicit user
  selection, validate arguments and output, review embedded resources and injection, and prevent any
  prompt text from granting authority. Revalidate list changes and subscribed resource updates.

## Calls

At every `tools/call`, validate the exact tool and current schema, caller/user/tenant, granted scope,
arguments, destination, root, sensitivity, approval, timeout, rate limit, and idempotency. Mutating,
money, auth, admin, external-message, production, or broad-network calls require explicit operation-
specific confirmation. Validate structured output against `outputSchema`; sanitize text before the
model sees it. Record safe hashes, not secrets or raw customer payloads.

## Contract

Capture through a client that records one redacted JSON-RPC envelope per line. Never record
authorization headers, cookies, session IDs, credentials, or raw customer secrets; retain only a
session-ID hash where the revision still has sessions. Compile offline. The compiler never connects
to or invokes the server:

```bash
python3 scripts/compile-mcp-transcript.py redacted-transcript.jsonl --output-dir mcp-evidence
python3 scripts/compile-mcp-transcript.py --check-manifest mcp-evidence/capture-manifest.json --evidence-root .
```

The compiler and both validators accept two transcript shapes, chosen by the per-request
`_meta` version, and run separate fixtures for each (`templates/agentic/mcp-evidence/` for
2025-11-25, `templates/agentic/mcp-evidence-2026-07-28/` for 2026-07-28; a transcript with
`initialize` always takes the handshake rules):

- **2025-06-18 / 2025-11-25** (handshake): initialize → response → initialized ordering, one
  negotiated version, negotiated capabilities, and a hashed session id with a matching version
  header on every later Streamable HTTP message.
- **2026-07-28** (stateless): no `initialize`, `notifications/initialized`, or session id. Every
  request carries `io.modelcontextprotocol/protocolVersion` and `.../clientCapabilities` in `_meta`
  (and the matching `MCP-Protocol-Version` header over HTTP), and one transcript holds one version.
  `server/discover` is optional for compilation; when present it must advertise that version, its
  capabilities bound later operations, and its `instructions` quarantine like initialize
  instructions. Every result carries `resultType: "complete"`; `input_required` (multi-round-trip
  input requests) and `task` results are rejected. List and `resources/read` results carry `ttlMs`
  and `cacheScope`, and `serverInfo`/`clientInfo` must not change mid-capture. Roots, Sampling, and
  Logging exposure (client capability, server capability, or per-request `logLevel`) compiles but is
  recorded as `deprecated_feature_exposure`.

Both shapes require paired request IDs and complete opaque-cursor chains. Mixed versions, a
2026-07-28 version negotiated through `initialize`, and unknown or future versions are rejected,
never downgraded. The compiler accepts discovery/read/render/completion capture methods only, not
`tools/call`, `subscriptions/listen`, or task methods. Copy the receipt templates
(`mcp-session.sample.json` / `mcp-content.sample.json`, or their `-2026-07-28` counterparts) and bind
both to the compiled manifest:

```bash
python3 scripts/validate-mcp-session.py mcp-session.json --evidence-root . --json
python3 scripts/validate-mcp-content.py mcp-content.json --evidence-root . --json
```

The validator checks the captured tool snapshot's confined path and file digest, safe object schemas,
exact tool set, and derived description/schema digests. A 2026-07-28 receipt also needs a capture
with `server/discover` (otherwise server capabilities and instructions are unverified), client
capabilities that match the transcript, and a `capabilities.deprecated_feature_exposure` list equal to
the deprecated features actually exposed (Roots, Sampling, Logging, or dynamic client registration).
A discovered server extension (for example MCP Apps) is gated until an extension-specific review
exists. A receipt whose protocol version differs from its compiled transcript, or a content receipt
whose capture manifest has a different version from its bound session, is rejected, never downgraded.
The receipt still does not perform OAuth discovery, authenticate the server,
observe the process, or prove the server omitted hidden calls. Pair it with network/process traces,
provider audit logs, and `skill-admission` evidence for third-party packages.

The separate content receipt binds to the canonical session validator and captured resource/prompt
artifact. It requires every discovered resource and prompt to have one reviewed read or render; use
quarantine rather than sampling when complete high-assurance admission is infeasible.
Its deterministic injection patterns catch common authority, command-execution, and secret-exfiltration
language, but they are a quarantine aid rather than a proof that arbitrary natural language is safe.
The transcript proves only what the capture client observed. It does not prove the server omitted
traffic on another connection or that the capture client itself is honest; pair it with process/network logs.

Tasks left the core protocol for the optional `io.modelcontextprotocol/tasks` extension in
2026-07-28 (polling `tasks/get`, client input via `tasks/update`). Engineer's admission compiler rejects task methods,
`resultType: "task"` results, a negotiated tasks extension, and task-augmented tool calls instead of
treating an evolving task trace as trusted evidence. Evaluate
Tasks in an isolated extension-specific harness before adding lifecycle, identity, TTL, polling,
input-required, result, cancellation, and authorization evidence to this canonical receipt.

Research: `research/mcp-security-2026-07.md`.
