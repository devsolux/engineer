# Verification ledger — 2026-11-05 MCP tool definitions

Verification of the MCP tool-definition rules in `scripts/validate-mcp-session.py`, the schema
handling of the secret scan in `scripts/compile-mcp-transcript.py`, and the matching text in
`references/mcp-security.md`, on top of the 1.3.0 tree (e978d2b). Research notes keep their own
dates and are not re-verified here. The previous ledger is
[verification-2026-10-26-rust.md](verification-2026-10-26-rust.md).

Method: the revision-specific rules were read from the primary sources below on 2026-11-05 and
written down as one test row each in `scripts/test-mcp-session.sh`. Behaviour was verified by
execution, not by documentation.

## Sources checked

All files are from `modelcontextprotocol/modelcontextprotocol`, branch `main`, on 2026-11-05.

| Source | Latest commit touching it | Checked |
|---|---|---|
| `schema/2026-07-28/schema.ts` (SHA-256 `742750af0bb8c716e7030c4977c992b55d1adc4407e9e66997db5846baedc2cd`) | 271ecc9 (2026-07-28) | `Tool`, `BaseMetadata`, `Icon`, `Icons`, `ToolAnnotations`; `execution` and `ToolExecution` absent |
| `schema/2025-11-25/schema.ts` (SHA-256 `e74b56e73b2e37bdb595f74ba22e428ad7f07aa3519355ba661d681298ed38ac`) | not recorded | `Tool`, `Icon`, `ToolExecution`; object root on `outputSchema` |
| `schema/2025-06-18/schema.ts` (SHA-256 `7d7f4cc6f3adb76e3fd5e1eee6bab8b1e183cfaf719da66d2aa5661737ca9539`) | not recorded | `Tool`, `BaseMetadata`; no `icons` or `execution` |
| `docs/specification/2026-07-28/server/tools.mdx` | 9850cae (2026-10-28) | Tool names, no-parameter schemas, annotations warning, `x-mcp-header`, output schema, security considerations |
| `docs/specification/2026-07-28/basic/transports/streamable-http.mdx` | 0cb6c6a (2026-07-28) | `x-mcp-header` constraints and static reachability |
| `docs/specification/2026-07-28/basic/index.mdx` | not recorded | JSON Schema usage, `$ref` resolution |

`tools.mdx` changed on `main` after the dated revision was published, so the text read here is that
later text. The schema files are the normative source for the Tool shape.

`search_notes`, named in the request behind this work, is not an MCP term: it appears in none of
the sources above. It is used here only as the name of a fixture tool.

## Findings

The validator's tool check was one fixed key set for every revision. Against the sources above it
refused or missed definitions in these ways, each now fixed and covered by a test:

| Finding | Spec rule | Before 1.3.1 |
|---|---|---|
| Fixed key set | `title`, `annotations`, `_meta` from 2025-06-18; `icons`, `execution` from 2025-11-25 | Any of them failed the tool |
| Required `description` and `outputSchema` | Only `name` and `inputSchema` are required | A tool without them failed |
| Required `properties` and `required` | Both optional; `{ "type": "object", "additionalProperties": false }` is the recommended no-parameter schema | The recommended schema failed |
| Tool names | Letters of either case, digits, `_`, `-`, `.`; up to 128 characters | Lower-case start and 64 characters only |
| `outputSchema` root | Any JSON Schema from 2026-07-28 | Object root only |
| Composition and references | Any 2020-12 keyword in `inputSchema` from 2026-07-28 | `oneOf`, `anyOf`, `$ref` roots failed |
| `execution` in 2026-07-28 | Removed from the core with Tasks | Not modelled per revision |
| `x-mcp-header` | Clients must drop a tool that breaks the rules | Not checked |
| `$ref` to a network URI | Must not be dereferenced; an unresolved reference should be rejected | Not checked |
| Malformed `required` entry | Not applicable | Crashed the validator with `TypeError` |
| Parameter names such as `page_token` and `max_tokens` | Ordinary parameter names | The compiler's secret scan rejected the whole transcript |

Local admission rules are stricter than the spec on purpose and are listed in
`references/mcp-security.md`: closed schemas, unknown keys refused, HTTPS or Base64 icons, the
recommended tool-name characters held as a rule, and the risk-versus-annotation gate.

Known limits, unchanged by this release: closure is judged at the schema root, through `items`,
`oneOf`, `anyOf`, and local `$ref`, not at every nested object, and `patternProperties` next to
`additionalProperties: false` is not inspected. The check for sensitive parameters marked with
`x-mcp-header` is not implemented; the spec makes that rule a server-side SHOULD NOT.

## Results

Run on macOS 27.2 (arm64) with Python 3.11.18 and Claude Code 2.1.282.

| Check | Result |
|---|---|
| Rule table in `test-mcp-session.sh` | 24 admitted and 60 refused definitions across the three revisions |
| End-to-end cases | Mutated transcripts recompiled and rebound through the real compiler and validator in `test-mcp-session.sh`; secret-scan boundaries in `test-mcp-transcript.sh` |
| Mutation check | 35 temporary mutants in scratch copies, each undoing one rule or restoring the 1.3.0 validator or compiler. 33 were caught at once. One survived and gained a test (`destructive_hint_ignored_when_read_only`), one was a broken mutant and was rerun as a valid one; both were then caught, so all 35 are caught |
| `make fixtures` | Illustrative skill-eval fixtures rebound after review: version 1.3.0 to 1.3.1, bundle a5f0ca49561e, grader-verified |
| `make lint`, `make check`, `make verify-build` | Passed |
| `make test JOBS=4` | 56 of 56 offline suites passed |
| `make host-validate` | `claude plugin validate --strict` passed for the marketplace and the plugin |
| `report-module-currency.py` | 120 modules, 119 current. Past due and not re-verified in this release: `references/output-quality.md` (verified 2026-08-27, due 2026-10-26) |

`references/mcp-security.md` keeps its 2026-10-22 verification date: only its tool-definition rules
were re-checked here, and its spec-pin line says so.

Not executed: any live MCP server or real SDK client, so no capture from a production tool list
backs these rules; a local install into a disposable host profile, which this repository requires
separate authorization for; Codex validation, because the Codex CLI is not installed on this
machine; and any live model run. CI results, the tag, and the release assets are recorded under
Publication once they exist.
