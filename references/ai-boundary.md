# AI boundary (product ↔ model)

**Last verified**: 2026-07-14 · **Review cadence**: 3 months

How generative features sit in the stack. Load with `python.md` (service details),
`ai-security.md` (threats), `ai-evals.md` (measurement), `observability.md` (traces).

## Preferred shape

```text
Browser
 → Next Server Action / Route Handler
 · getUser() / session
 · Zod input
 · rate limit
 → AI boundary (server-only TS **or** Python FastAPI)
 · model gateway (timeouts, retries policy, redaction)
 · allowlisted tools only
 → Model provider / tools / optional vector store
```

| Layer | Owns |
|---|---|
| Next (TS) | UI, cookie auth, product mutations that need RLS UX |
| AI boundary service | Prompt assembly, model I/O, tool orchestration, streaming |
| Supabase | Durable product data + RLS (not the model key store) |
| Gateway (optional) | Multi-provider routing, spend caps, failover |

**Never:** model API keys in `NEXT_PUBLIC_*` or client bundles.

## When Python vs TS

| Prefer Python FastAPI (`python.md`) | Prefer server-only TS |
|---|---|
| Heavy LLM/RAG/agent libs, batch embeddings (`backend-pgvector.md`) | Thin completion + stream via Vercel AI SDK |
| Durable multi-step agent workers | Single-request generate/stream |
| Shared AI service used by multiple apps | App-local feature |

Greenfield product UI stays Next. Add `services/ai-api/` when AI is a real subsystem.

## Hard rules

1. **Timeouts** on every model and tool call (no `timeout=None` in prod).
2. **Auth before generate** - unauthenticated abuse is a cost + data risk.
3. **Zod / Pydantic** at the boundary; structured errors `{ code, message, request_id }`.
4. **Streaming:** SSE events `token | error | done`; cancel upstream on disconnect.
5. **Money paths:** durable jobs (not in-process `BackgroundTasks` alone).
6. **Logs/traces:** redact secrets and PII; never log full Authorization headers.
7. **Tools:** allowlist; see `ai-security.md`.
8. **CI:** unit tests mock the gateway; no live provider calls required for green.

## Minimal route sketch (FastAPI)

```python
# services/ai-api - illustrative; match repo layout
@router.post("/v1/complete")
async def complete(
 body: CompleteIn,
 user: Annotated[User, Depends(require_user)],
 http: Annotated[httpx.AsyncClient, Depends(get_http)],
 settings: Annotated[Settings, Depends(get_settings)],
) -> CompleteOut | EventSourceResponse:
 # assemble prompt server-side only
 # call gateway with explicit Timeout
 # stream or return structured JSON
 ...
```

## Scaffold checklist (new AI feature)

```
- [ ] Boundary chosen (TS server vs Python service)
- [ ] Keys only in server env / secret manager
- [ ] Input schema + auth + rate limit
- [ ] Timeout + cancel on disconnect
- [ ] Tool allowlist (if any) reviewed via ai-security.md
- [ ] Offline eval or fixture for the prompt path (ai-evals.md)
- [ ] Trace/request_id; redaction policy
- [ ] Activation/analytics if user-facing (growth-funnels)
```

## Anti-patterns

- Calling OpenAI/Anthropic from a Client Component
- One mega-prompt with no schema and no evals
- Unrestricted "run shell" tools on a product agent
- Storing customer chat logs forever without retention policy
- Dual ownership of the same tables via Alembic + Supabase migrations

## Related

- `python.md` - uv/FastAPI/SSE/jobs defaults
- `backend-pgvector.md` - tenant-scoped embeddings + RAG RPC
- `ai-security.md` - MCP/skills/injection
- `ai-evals.md` - harness matrix
- `ai-agents.md` - agent specs (coding agents, not product users)
- `workflows.md` - outer-loop + risk gates

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
