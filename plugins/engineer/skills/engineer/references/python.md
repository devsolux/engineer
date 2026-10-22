# Python: services, workers, and AI boundary

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `typescript.md` | Product boundary, Zod, OpenAPI consumers |
| `rust.md` | Measured hot paths after profiling |
| `ai-boundary.md` | Product ↔ model shape, scaffold checklist |
| `ai-security.md` | Tools/MCP/secrets for AI paths |
| `ai-evals.md` | How to measure prompts/agents |
| `backend-api.md` | Next Server Actions / Route Handlers (contrast) |
| `backend-auth.md` | Cookie SSR vs Python Bearer verify |
| `backend-database.md` / `backend-supabase.md` | RLS + migration ownership |
| `api-data-flows.md` | Cross-service OpenAPI flows |
| `enforcement.md` | CI + scan PY-* |
| `project-detect.md` | Detect uv / FastAPI / `services/**` |

Default stack: **CPython 3.14 / uv / ruff / basedpyright / FastAPI / Pydantic v2 / SQLAlchemy 2 async / uvicorn**.
Pins: § [Default stack snapshot](#default-stack-snapshot). **Match the existing service before applying defaults.**

## Contents
- [When to use Python](#when-to-use-python)
- [Default stack snapshot](#default-stack-snapshot)
- [Project layout](#project-layout)
- [Tooling (uv, ruff, types, CI)](#tooling-uv-ruff-types-ci)
- [Typing and Pydantic](#typing-and-pydantic)
- [Settings and secrets](#settings-and-secrets)
- [Async model](#async-model)
- [FastAPI services](#fastapi-services)
- [Middleware and security headers](#middleware-and-security-headers)
- [Auth and SSRF](#auth-and-ssrf)
- [HTTP clients and streaming](#http-clients-and-streaming)
- [Data layer (SQLAlchemy)](#data-layer-sqlalchemy)
- [Supabase boundary](#supabase-boundary)
- [Migrations](#migrations)
- [Background jobs](#background-jobs)
- [Idempotency and retries](#idempotency-and-retries)
- [Observability](#observability)
- [Testing and contracts](#testing-and-contracts)
- [Agent codegen rules](#agent-codegen-rules)
- [Anti-patterns](#anti-patterns)
- [TS and Rust boundaries](#ts-and-rust-boundaries)
- [Production checklist](#production-checklist)

## When to use Python

| Use Python | Stay in TypeScript | Prefer Rust |
|---|---|---|
| LLM / RAG / agents / MCP tools | UI, RSC, client islands | Hot path failing SLA **after** optimize |
| Embeddings, batch ML, PyData transforms | Cookie session + Supabase product CRUD | Stream fanout, proxy/gateway |
| OpenAPI microservices next to Next | BFF aggregation for UI | CPU-bound parsers (measured) |
| Durable multi-step agent workflows | Simple webhooks on Vercel | - |
| Ops CLIs for Python-owned services | Form validation, dashboards | - |

Greenfield product surface stays **Next + Supabase**. Add Python when the problem is AI/data/Python-first libs - not because “backends should be Python.”

## Default stack snapshot

**as_of 2026-10-22** · re-verify by **2027-01-22**

| Component | Pin / policy |
|---|---|
| CPython | **3.14** (`.python-version` + `requires-python = ">=3.14"`); **3.13** (security-only) only for max-compat |
| Free-threading | Opt-in only (3.14t / measured); default **GIL + asyncio** |
| Package manager | **uv** 0.13.x · commit `uv.lock` · CI `uv sync --locked` |
| Format + lint | **ruff** 0.17.x only (no Black/isort/flake8) |
| Typecheck | **basedpyright** 1.40.x CI · **ty** optional editor (beta) |
| API | **FastAPI** 0.159.x · **uvicorn** 0.54.x |
| Validation | **Pydantic** 2.14.x · **pydantic-settings** 2.16.x |
| HTTP | **httpx** 0.28.x (no release since 2024-12; Pydantic's `httpx2` fork exists - evaluate) |
| DB | **SQLAlchemy** 2.1.x (`[asyncio]` extra) · **asyncpg** 0.32.x · Alembic only if Python owns DB |
| Auth JWT | **PyJWT** 2.15.x (+ cryptography) - not python-jose |
| Jobs | **Taskiq** (greenfield async) · Celery if already present · **Temporal** for durable sagas |
| Obs | **structlog** · OTel (FastAPI built-in) + httpx/SQLAlchemy · Sentry |
| Supply chain | `uv audit` + `UV_MALWARE_CHECK=1` (both preview) · prefer `exclude-newer` cooldown |
| Optional | Granian after measure · msgspec after profile · LiteLLM proxy · supabase-py for Auth/Storage |

**Avoid for greenfield:** Poetry, pip-tools as sole lock, Black/isort, mypy-only, python-jose, arq new systems, SA 1.4 `Query`, Pydantic v1, notebooks as product.

## Project layout

```
apps/web/ # Next (TS) - UI + BFF
services/
 ai-api/ # FastAPI package (uv)
 src/ai_api/
 __init__.py
 main.py # app + lifespan
 api/ # routers
 domain/
 db/
 settings.py
 tests/
 pyproject.toml
packages/py-shared/ # optional shared libs
crates/ # Rust hot paths
supabase/migrations/ # schema + RLS source of truth (when using Supabase)
```

Rules:
- **src layout** + `py.typed` for packages
- Never nest Python under `apps/web`
- uv **workspace** when packages share resolution; path editables when graphs conflict

## Tooling (uv, ruff, types, CI)

```toml
# pyproject.toml (excerpt)
[project]
requires-python = ">=3.14"
dependencies = [
 "fastapi>=0.159",
 "uvicorn[standard]>=0.54",
 "pydantic>=2.14",
 "pydantic-settings>=2.16",
 "httpx>=0.28",
]

[dependency-groups]
dev = ["pytest>=9", "pytest-asyncio>=1.4", "basedpyright>=1.40", "ruff>=0.17", "httpx"]

[tool.ruff]
target-version = "py314"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.basedpyright]
typeCheckingMode = "recommended"
```

CI order (blocking):

1. `uv sync --locked` (or `--frozen`)
2. `ruff format --check` && `ruff check`
3. `basedpyright`
4. `pytest -m "not integration"` (fast)
5. `uv audit` + `UV_MALWARE_CHECK=1`
6. Integration (testcontainers) on PR / main

Local hooks: **prek** preferred over classic pre-commit (ruff + `uv lock --check`); typecheck/audit stay in CI.

## Typing and Pydantic

- Prefer `list[str]`, `X | None`, PEP 695 type params; **Protocol** for ports; **TypedDict** for wire-ish shapes
- **Pydantic at trust boundaries** - `model_validate` / `model_dump`; `ConfigDict(extra="forbid")` on public APIs
- Ban V1 APIs: `parse_obj`, `.dict()`, `from_orm`
- Domain types vs DTO split - same idea as `typescript.md`
- Static types **do not** replace runtime validation

## Settings and secrets

```python
from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
 model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
 database_url: SecretStr
 jwt_audience: str
 cors_origins: list[str] = []

@lru_cache
def get_settings() -> Settings:
 return Settings()
```

- 12-factor: fail-fast missing env in prod
- `.env` local only; prod = platform secrets / `secrets_dir`
- Never log `SecretStr` values

## Async model

- **anyio** task groups + cancel scopes for structured concurrency
- No fire-and-forget `create_task` on request paths without tracking
- Lifespan-owned resources (`httpx.AsyncClient`, engine); always dispose
- No `requests` / `time.sleep` / sync DB in `async def`
- Reraise cancellation after shielded cleanup

## FastAPI services

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends

@asynccontextmanager
async def lifespan(app: FastAPI):
 app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0))
 yield
 await app.state.http.aclose()

app = FastAPI(lifespan=lifespan)
api = APIRouter(prefix="/v1")

@api.get("/health/live")
async def live():
 return {"status": "ok"}
```

- Handlers **thin**: extract → validate → domain → map response
- `Annotated[..., Depends()]` for deps; routers by domain
- Ban `@app.on_event` - use **lifespan** only
- OpenAPI is the **source of truth** for TS clients

## Middleware and security headers

Order (Starlette: **last** `add_middleware` is **outermost**):

1. CORS (explicit origins - never `*` + credentials)
2. TrustedHost
3. Request ID / correlation
4. Security headers
5. GZip (exclude SSE)

Auth is **Depends**, not middleware that swallows 401 semantics.

## Auth and SSRF

- Next owns **cookie SSR**; Python verifies **Bearer JWT** (PyJWT: always `algorithms=[...]`, check `exp`/`sub`/`aud`/`iss`)
- 401 unauthenticated vs 403 forbidden - do not conflate
- Outbound URL fetches: **https + host allowlist**; block private/metadata; recheck redirects
- `service_role` keys: server-only, never browser

## HTTP clients and streaming

- Shared `httpx.AsyncClient` on lifespan - never per-request client in hot paths
- Explicit `Timeout(connect=…, read=…, write=…, pool=…)`; never `timeout=None` in prod
- Retries only on **idempotent** methods with budgeted backoff
- LLM tokens: **SSE** (`fastapi.sse.EventSourceResponse` 0.135+ / sse-starlette); events `token | error | done`; cancel upstream on disconnect; disable proxy buffering

## Data layer (SQLAlchemy)

- SQLAlchemy **2.1** (`sqlalchemy[asyncio]`; 2.0 is maintenance) + asyncpg: `async_sessionmaker`, request-scoped session, `select()` only
- `expire_on_commit=False`; explicit `selectinload` / `joinedload`; prefer `lazy="raise"`
- **Pool budget:** `workers × (pool_size + max_overflow) < DB/pooler limit`
- Supabase transaction pooler (`:6543`): **NullPool** + unique prepared-statement names / disable statement cache
- Stationary single instance: prefer direct `:5432` when possible

## Supabase boundary

| Concern | Owner |
|---|---|
| Auth/Storage/Realtime helpers | supabase-py async client OK |
| Multi-table transactions / heavy SQL | SQLAlchemy + asyncpg |
| Schema + RLS | **`supabase/migrations/`** (or single Alembic owner - never both) |
| User-scoped data | user JWT + RLS; never trust client alone with service_role |

## Migrations

- **One writer** for schema: Supabase migrations **or** Alembic for Python-private DB - not both on the same tables
- Expand/contract for renames; migrate → deploy code; prod prefers forward-fix
- Autogenerate = draft only; RLS with every `CREATE TABLE public.*`

## Background jobs

| Tier | Tool | When |
|---|---|---|
| 0 | FastAPI `BackgroundTasks` | Best-effort, seconds, **may die with process** |
| 1 | **Taskiq** (+ Redis/broker) | Greenfield durable async jobs |
| 2 | Celery | Existing Celery ops only |
| 3 | **Temporal** | Multi-step sagas, long waits, durable agents |

- Never use Tier 0 for payments / webhook finalization
- Separate worker processes for Tier ≥1
- JSON/Pydantic payloads - **no pickle**
- arq is **maintenance-only** - do not start new systems on it

## Idempotency and retries

- Assume **at-least-once**; handlers must be idempotent
- HTTP: `Idempotency-Key` + request hash store
- Webhooks: verify signature → dedupe `event_id` → apply
- Retry only transient errors; max attempts + jitter; poison → **DLQ + alert**
- Reuse provider idempotency keys across retries

## Observability

- **structlog** JSON + contextvars (`request_id`, user id when safe)
- OTel: FastAPI built-in (0.142+; exporter auto-setup opt-in) + httpx + SQLAlchemy/asyncpg
- Split **`/health/live`** (process) vs **`/health/ready`** (deps)
- No secrets/PII in logs; Sentry for exceptions

## Testing and contracts

- pytest 9 + `asyncio_mode=auto`
- httpx `ASGITransport` for unit API tests
- **testcontainers** Postgres for integration - not SQLite-as-Postgres
- Markers: `unit` / `integration`
- **Schemathesis** (or equivalent) against OpenAPI ASGI for contract drift
- CI must stay green without network to third-party LLM APIs (mock gateway)

## Agent codegen rules

### Must generate
- `uv` project + committed `uv.lock` + `.python-version`
- `lifespan` for clients/engines; thin routers; Pydantic request/response models
- PyJWT with explicit `algorithms=` and claim checks
- Explicit httpx timeouts; structured errors `{code, message, request_id}`
- Job tier chosen deliberately; OpenAPI export path for TS

### Must not generate
- Poetry/Black/flake8/mypy-only greenfield stacks
- `python-jose`, `verify_signature=False`, hardcoded secrets
- `@app.on_event`, `session.query`, Pydantic v1 APIs
- `requests` in async routes; CORS `*` + credentials
- `BackgroundTasks` for money-critical work
- Dual Alembic + Supabase migrations on the same tables
- Production `uvicorn --reload`; root Docker user without reason

### Scan IDs (for enforcement)

| ID | Signal |
|---|---|
| PY-LOCK | missing `uv.lock` / no frozen sync |
| PY-RUFF-ONLY | Black/isort/flake8 as primary |
| PY-JWT | jose / missing `algorithms` |
| PY-LIFESPAN | `on_event` or import-time engines |
| PY-ASYNC-BLOCK | `requests`/`time.sleep` in async |
| PY-SA14 | `session.query` |
| PY-CORS | `allow_origins=["*"]` + credentials |
| PY-JOB-TIER0 | BackgroundTasks for payment/webhook |
| PY-SECRET-LOG | logging secrets / raw tokens |
| PY-AUDIT | CI without `uv audit` |

## Anti-patterns

| ID | Severity | Pattern | Remediation |
|---|---|---|---|
| AP-PKG-POETRY | blocker | Poetry/pip freeze as sole truth | uv + lock |
| AP-FMT-BLACK | major | Black+isort+flake8 | ruff only |
| AP-AUTH-JOSE | blocker | python-jose / no algorithms | PyJWT + algorithms |
| AP-FA-ON-EVENT | major | `@app.on_event` | lifespan |
| AP-ASYNC-REQUESTS | blocker | sync HTTP in async route | httpx AsyncClient |
| AP-SA-QUERY | major | `session.query` | 2.0 `select()` |
| AP-CORS-STAR | blocker | `*` origins + credentials | explicit origins |
| AP-JOB-BG-PAY | blocker | BackgroundTasks for payments | Taskiq/Temporal |
| AP-MIG-DUAL | blocker | Alembic + Supabase dual-write schema | one owner |
| AP-NOTEBOOK-PROD | blocker | Notebook/Streamlit as product API | FastAPI service |
| AP-PICKLE | blocker | pickle job payloads | JSON/Pydantic |
| AP-RELOAD-PROD | major | `--reload` in prod | multi-worker/ASGI only |

## TS and Rust boundaries

```
Browser → Next (session, UI, CRUD, RLS) → Postgres
 └→ Python AI/service (Bearer) → models / tools
 └→ Rust hot service (JWT) → Postgres/Redis [measured only]
```

- **Contract-first:** FastAPI OpenAPI → `contracts/openapi-*.json` → `openapi-typescript` / `@hey-api/openapi-ts`
- Never hand-sync DTOs across languages
- One table writer; document ownership
- Profile before Rust (`py-spy` / scalene); fix I/O and queries first

## Production checklist

- [ ] `requires-python` + `.python-version` pinned (3.14 preferred)
- [ ] `uv.lock` committed; deploy `uv sync --locked --no-dev`
- [ ] ruff format/check + basedpyright + pytest green
- [ ] `uv audit` (+ malware check) in CI
- [ ] Lifespan resources; no `on_event`
- [ ] JWT verify with algorithms + aud/iss; secrets not in repo/logs
- [ ] CORS explicit; TrustedHost; request IDs
- [ ] httpx timeouts; no open SSRF fetches
- [ ] Pool sizing vs Postgres/pooler documented
- [ ] Migration owner singular; RLS on user tables
- [ ] Job tier ≥1 for durable work; DLQ for poison
- [ ] live/ready probes; non-root container; no `--reload`
- [ ] OpenAPI published for TS consumers
- [ ] `engineer-scan` Python signals clean when enforcement enabled

---

Research: `research/python/` (outline, fields, 44 results) - **load on demand only**. Never session bulk-load.

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
