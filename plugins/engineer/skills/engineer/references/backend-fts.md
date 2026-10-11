# Postgres full-text search (FTS)

**Last verified**: 2026-07-14 · **Review cadence**: 3 months

Keyword search with `tsvector` / `tsquery` on Supabase/Postgres.
Load with `backend-database.md` (RLS), `backend-multitenant.md` (org scope),
`backend-pgvector.md` (when hybrid semantic + keyword), `data-layer.md` (cache).

## When to use FTS vs pgvector

| Need | Prefer |
|---|---|
| Exact tokens, product names, emails, codes | **FTS** (or `ILIKE` only for tiny tables) |
| Synonyms / natural language questions | **pgvector** RAG |
| Both keyword and meaning | Hybrid: FTS filter/rank + vector re-rank (or RRF) |

Do not stand up Elasticsearch for early SaaS if Postgres FTS + RLS covers the product.

## Core rules

1. **Persist** `tsvector` (generated column or trigger) - do not `to_tsvector(...)` on every query for large tables.
2. **GIN index** on the vector column.
3. **Weight** title > body (`setweight` A/B/C/D).
4. **Rank** with `ts_rank` or `ts_rank_cd`; always `LIMIT`.
5. **Tenant filter** in the same query as FTS (`org_id` + RLS).
6. **Sanitize** user input into `tsquery` (`plainto_tsquery` / `websearch_to_tsquery`).

## Schema sketch

```sql
alter table public.articles
 add column if not exists search_vector tsvector
 generated always as (
 setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
 setweight(to_tsvector('english', coalesce(summary, '')), 'B') ||
 setweight(to_tsvector('english', coalesce(body, '')), 'C')
 ) stored;

create index articles_search_vector_gin
 on public.articles
 using gin (search_vector);

-- RLS already on articles; search does not bypass it
```

If the table is huge and writes are hot, a trigger-maintained column is fine; generated columns keep the mental model simple.

## Query sketch

```sql
-- websearch_to_tsquery handles quotes/OR-ish user strings better than raw to_tsquery
select
 a.id,
 a.title,
 ts_rank_cd(a.search_vector, q) as rank
from public.articles a,
 websearch_to_tsquery('english', $query) q
where a.org_id = $org_id
 and a.search_vector @@ q
order by rank desc
limit 20;
```

App rules:
- Resolve `org_id` from membership (never trust alone from client)
- Cap page size (20-50)
- Optional: highlight with `ts_headline` carefully (CPU cost)

## Languages and config

- Pick a text search config (`english`, `simple`) and stick to it per column
- `simple` for product codes / usernames (no stemming)
- Multi-language products: separate columns or `regconfig` strategy - document the choice

## Performance

| Tip | Detail |
|---|---|
| Stored vector + GIN | Avoid compute-at-query on large tables |
| Pre-filter | `org_id` / `status` before or with FTS |
| Limit early | Top-N only |
| Rank cost | `ts_rank_cd` for multi-word proximity; measure p95 |
| Hybrid | FTS for candidates, vector for re-rank if needed |

## Security

- FTS results still go through **RLS**
- Do not expose rows from other orgs via a SECURITY DEFINER search RPC without membership checks
- Rate-limit search endpoints (abuse + cost)
- Avoid reflecting raw query strings unescaped into HTML headlines

## Caching

- Shared public search: possible with `use cache` + query hash tags
- Private tenant search: pass `orgId` into cache keys or skip shared cache
- Invalidate content tags on article write (`cache-tags.ts` `content` / `ragSource`)

## Testing

- Seed two orgs with distinct titles; user A query must not return B rows
- Assert rank order for a fixture query
- Migration includes GIN index

## Anti-patterns

- `ILIKE '%q%'` on large tables as the long-term search plan
- Computing `to_tsvector` on every request over multi-column expressions
- Unbounded result sets without `LIMIT`
- Elasticsearch for a 10k-row catalog "because search"
- Skipping RLS because "it's just search"

## Related

- `backend-pgvector.md` - semantic search
- `backend-database.md` - RLS performance
- `backend-multitenant.md` - org scope
- `backend-api.md` - rate limit search actions
- `data-layer.md` - cache invalidation

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
