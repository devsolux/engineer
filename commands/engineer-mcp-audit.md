---
description: Audit an MCP server's identity, authorization, capabilities, tools, and captured calls.
---

# /engineer-mcp-audit

Load `references/mcp-security.md`, `references/ai-security.md`, and
`references/skill-supply-chain.md` for third-party server code or packages.

1. Inventory every project/user MCP registration, immutable server revision, process, endpoint,
   transport, environment, credential source, filesystem root, egress destination, and secret class.
2. Verify remote authorization discovery, PKCE/state/redirect, canonical resource indicator,
   audience, minimal scopes, token storage, and separate upstream credentials. Reject passthrough.
3. Capture a redacted ordered JSON-RPC transcript without tokens, cookies, or raw secrets. Compile it
   offline with `compile-mcp-transcript.py`; do not let the compiler connect to or invoke the server.
   Bind receipts to its manifest. Capture `tools/list`, hash the confined artifact, and derive every description
   and input/output schema digest from it. Require exact tool-set equality. Classify risk, scopes,
   destinations, timeout, rate limit, idempotency, confirmation, and validation requirements.
4. Review elicitation, resources, and prompts at their own trust boundaries. Roots, sampling, and
   logging are deprecated in the 2026-07-28 revision: review them only when the server still
   advertises them, and record that exposure as a deprecated-feature item with its migration path.
   Capture complete paginated resource/template and prompt catalogs, reviewed reads/renders, and
   completion policy. Resources remain application/user-selected data; prompts require explicit user
   selection and cannot grant authority. Revalidate list changes and subscriptions.
5. Capture benign and adversarial isolated calls with synthetic identities/data; never test
   destructive behavior against production.
6. Emit `mcp-session.json`, validate it, and keep install/enable/production promotion separately
   authorized.

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
python3 "$ENGINEER/scripts/compile-mcp-transcript.py" redacted-transcript.jsonl --output-dir mcp-evidence
python3 "$ENGINEER/scripts/compile-mcp-transcript.py" --check-manifest mcp-evidence/capture-manifest.json --evidence-root .
python3 "$ENGINEER/scripts/validate-mcp-session.py" mcp-session.json --evidence-root . --json
python3 "$ENGINEER/scripts/validate-mcp-content.py" mcp-content.json --evidence-root . --json
```
