# pgvector + RAG (Supabase / Postgres)

**Last verified**: 2026-07-14 · **Review cadence**: 3 months

Semantic search and retrieval-augmented generation on the default stack.
Load with `backend-database.md` (RLS), `ai-boundary.md` (where models live),
`ai-security.md` (prompt injection via retrieved text), `data-layer.md` (cache).

## Contents
- [When to use](#when-to-use)
- [Stack defaults](#stack-defaults)
- [Schema sketch](#schema-sketch)
- [Ingest pipeline](#ingest-pipeline)
- [Query pattern (RPC)](#query-pattern-rpc)
- [Performance](#performance)
- [Security](#security)
- [Caching](#caching)
- [Testing](#testing)
- [Anti-patterns](#anti-patterns)
- [Related](#related)

## When to use

| Use pgvector | Prefer something else |
|---|---|
| In-app search over user/org docs, tickets, knowledge base | Full-text only (`backend-fts.md` / tsvector) for keyword-heavy catalogs |
| RAG over product content you own | Bulk-load skills for static coding patterns |
| Tenant-scoped embeddings with RLS | Unscoped global corpus without isolation |

**Not for:** training models, replacing structured filters (status, dates), or dumping the whole monorepo into vectors by default.

## Stack defaults

| Piece | Default |
|---|---|
| Extension | `vector` (pgvector) on Supabase/Postgres |
| Embedding model | Provider via AI boundary (server-only); dimension fixed per table |
| Distance | cosine (`<=>`) or L2 (`<->`) - pick one and stick |
| Index | HNSW for most SaaS read paths; IVFFlat only if you know why |
| Tenancy | `org_id` / `user_id` columns + RLS (same as rest of app) |
| Chunking | app/worker code, not SQL |

## Schema sketch

```sql
-- migration (illustrative)
create extension if not exists vector;

create table public.document_chunks (
 id uuid primary key default gen_random_uuid(),
 org_id uuid not null references public.orgs (id) on delete cascade,
 source_id uuid not null, -- parent doc
 chunk_index int not null,
 content text not null,
 embedding vector(1536) not null, -- must match model dimension
 metadata jsonb not null default '{}',
 created_at timestamptz not null default now()
);

create index document_chunks_org_id_idx on public.document_chunks (org_id);
-- HNSW example (cosine). Adjust lists/ef later under load.
create index document_chunks_embedding_hnsw
 on public.document_chunks
 using hnsw (embedding vector_cosine_ops);

alter table public.document_chunks enable row level security;

create policy "members read chunks"
 on public.document_chunks for select
 using (public.is_org_member(org_id));

-- writes via service role worker or authenticated member with insert policy
create policy "members insert chunks"
 on public.document_chunks for insert
 with check (public.is_org_member(org_id));
```

Rules:
- **One embedding dimension per column** - never mix model sizes without a migration
- Index tenant filters (`org_id`) for pre-filter + vector search patterns
- RLS on every public table - embeddings are still user data
- Prefer membership helpers from `backend-multitenant.md`

## Ingest pipeline

```text
upload / sync source
 -> durable job (background-jobs / Python worker)
 -> extract text
 -> chunk (stable size + overlap)
 -> embed via AI boundary (timeouts, no client keys)
 -> upsert chunks + embedding
 -> revalidateTag / updateTag if UI lists sources
```

| Rule | Why |
|---|---|
| Job tier >= durable for bulk ingest | Request path will time out |
| Idempotent upsert on (source_id, chunk_index) | Retries safe |
| Store model id + dim in metadata | Future re-embed migrations |
| Never embed secrets / raw `.env` | ai-security |

## Query pattern (RPC)

Expose a **security invoker** or carefully audited **security definer** function that always filters by membership:

```sql
create or replace function public.match_document_chunks(
 query_embedding vector(1536),
 match_org uuid,
 match_count int default 8
)
returns table (
 id uuid,
 content text,
 metadata jsonb,
 similarity float
)
language sql
stable
as $$
 select
 c.id,
 c.content,
 c.metadata,
 1 - (c.embedding <=> query_embedding) as similarity
 from public.document_chunks c
 where c.org_id = match_org
 and public.is_org_member(match_org)
 order by c.embedding <=> query_embedding
 limit least(match_count, 32);
$$;
```

App flow:
1. Auth user; resolve `org_id` from membership (never trust body alone)
2. Embed query server-side
3. Call RPC with `match_org`
4. Pass chunks to model as **untrusted data** (prompt-injection resistant framing)
5. Cite sources in the UI when possible

## Performance

| Tip | Detail |
|---|---|
| Pre-filter | `where org_id = $org` before or with ANN (avoid full-table vector scan) |
| Cap `match_count` | Hard ceiling in SQL (e.g. 32) |
| Batch embed | Worker batches; respect provider rate limits |
| Re-embed jobs | Version embeddings; dual-write during model upgrades |
| Measure | p95 latency for embed + match under tenant load |

## Security

- Retrieved text is **untrusted** - can inject instructions into the model (`ai-security.md`)
- Service role only in workers, never browser
- Do not return other tenants' chunks even if similarity is high (RLS + org filter)
- Rate-limit search/RAG endpoints (cost amplification)

## Caching

- Do **not** put user-specific RAG answers in shared `use cache` without user/org keys
- Cache **public** knowledge base chunks more aggressively than private tenant data
- Invalidate source tags when docs change (`templates/lib/cache-tags.ts`)

## Testing

- pgTAP or SQL tests: member A cannot `select` member B chunks
- Integration: insert two orgs' embeddings; query as each user
- Mock embed API in unit CI (no live provider required for green)

## Anti-patterns

- Global vector table with no `org_id` / RLS
- Embedding from Client Components with public API keys
- `select *` huge chunks into the prompt without token budget
- IVFFlat with un-tuned lists as a silent default under high QPS
- Treating RAG as a substitute for structured filters (status = open)

## Related

- `backend-database.md` - RLS performance `(select auth.uid())`
- `backend-multitenant.md` - membership helpers
- `ai-boundary.md` / `python.md` - embed workers
- `ai-security.md` - injection via retrieval
- `background-jobs.md` - durable ingest
- `data-layer.md` - cache invalidation

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
