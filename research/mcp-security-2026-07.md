# MCP authorization and runtime security research

**Date:** 2026-07-16
**Feeds:** `references/mcp-security.md`, `scripts/compile-mcp-transcript.py`, `scripts/validate-mcp-session.py`, `scripts/validate-mcp-content.py`

## Encoded findings

- HTTP MCP authorization treats the server as an OAuth resource server. Clients discover protected-
  resource metadata through the 401 challenge or ordered well-known fallbacks, support OAuth and OIDC
  authorization-server discovery, use authorization code with verified PKCE S256, exact redirects and
  state, and include the canonical MCP resource in authorization and token requests.
- Client registration is an explicit trust choice. Client ID Metadata Documents introduce metadata-
  fetch SSRF and localhost redirect impersonation risks; preregistration and dynamic registration have
  different deployment costs. Scope challenges are authoritative for the failed request and step-up
  authority cannot silently authorize replay.
- Servers validate token audience and scopes. Tokens do not travel in query strings and an inbound
  MCP token is never passed through to an upstream API.
- Minimal initial scopes and incremental elevation reduce confused-deputy and token-theft impact.
- Tool input schemas, structured output schemas, access controls, rate limits, timeouts, user-visible
  sensitive-operation confirmation, result validation, and audit logs are protocol security duties.
- Roots are consented `file://` boundaries, not advisory labels; canonical path validation remains
  necessary after root changes.
- Sampling can create nested agent behavior and should preserve human review of request and result.
- Elicitation is mode-specific in 2025-11-25. Form mode cannot request secrets or carry clickable
  URLs. URL mode may move credential, OAuth, or payment entry out of band only with explicit consent,
  full URL disclosure, no prefetch/auto-open, no sensitive or preauthenticated URL, client/model
  content isolation, verified same-user binding, completion-ID validation, and manual recovery.
- A tool-policy receipt must not self-assert schema hashes. Persist the observed `tools/list` result,
  confine and hash the artifact, derive description/input/output digests from canonical content, and
  reject tool insertion, removal, malformed closed schemas, or drift from the reviewed policy.
- Resources are application-driven and uniquely URI-addressed; servers validate URIs and permissions.
  Capture complete paginated lists, templates, reads, list changes, and subscriptions. Treat content
  and annotations as data, enforce MIME/size/sensitivity policy, and re-review changed content.
- Prompts are user-controlled protocol features. Require explicit user selection, complete paginated
  discovery, validated arguments and outputs, and injection review of text and embedded resources.
  Completion suggestions are also untrusted input and cannot expand authority.
- Initialization is the first protocol interaction; operation follows the matching initialize result
  and client `initialized` notification. HTTP operation requests carry the negotiated protocol version
  and session identity. List cursors are opaque, session-local, and followed until absent.
- Derive review artifacts from a redacted ordered JSON-RPC transcript. Reject action methods, secret-
  bearing fields, lifecycle/capability/header drift, incomplete request pairs, and unfinished cursor
  chains. Recompile the manifest before trusting semantic output hashes.
- Tasks entered the 2025-11-25 specification as experimental durable state machines. The canonical
  compiler keeps rejecting task methods and task-augmented calls until a separate harness can prove
  task ownership, unpredictable IDs, authorization, TTL, polling, input-required binding, exact
  terminal results, cancellation, and cleanup without relying on optional notifications.

## Primary sources

- MCP 2025-11-25, [Key Changes](https://modelcontextprotocol.io/specification/2025-11-25/changelog)
- MCP, [Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- MCP, [Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- MCP, [Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- MCP, [Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)
- MCP, [Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- MCP, [Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- MCP, [Prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts)
- MCP, [Completion](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/completion)
- MCP, [Pagination](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination)
- MCP, [Roots](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- MCP, [Sampling](https://modelcontextprotocol.io/specification/2025-11-25/client/sampling)
- MCP, [Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- MCP, [Tasks (experimental)](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
- IETF, [RFC 8707: Resource Indicators for OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8707)
- IETF, [RFC 9728: OAuth 2.0 Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728)
- IETF, [RFC 9700: Best Current Practice for OAuth 2.0 Security](https://www.rfc-editor.org/rfc/rfc9700)

## Limits

The shipped receipt validates recorded configuration, a local captured tool snapshot, and calls. A live assessment must independently
retrieve metadata, inspect tokens without retaining their values, observe network/process behavior,
and compare server/provider audit logs with the receipt.
The content validator's bounded pattern scan only detects common instruction, command, and secret-
exfiltration language. Independent review, least authority, and runtime isolation remain necessary.
