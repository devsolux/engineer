# Rust: services, APIs, and infra

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `api-data-flows.md` | TS ↔ Rust data paths |
| `python.md` | Prefer Python for AI/workers; Rust after measured need |
| `system-architecture.md` | When to split services |
| `observability.md` | Tracing, health checks |
| `enforcement-rules.md` | clippy, no-unwrap CI; `templates/rust/` lint config |
| `rust-idioms.md` / `rust-systems.md` | The Rust itself: ownership, API design, errors; async, unsafe, crates, docs, tests |
| `rust-review.md` / `rust-port.md` | Reviewing existing Rust; porting other languages to Rust |

Default stack: **Axum 0.8+ / Tokio / SQLx / Tower**. Match existing project
crates before applying defaults.

## Contents
- [When to use Rust](#when-to-use-rust)
- [Project layout](#project-layout)
- [Axum handler patterns](#axum-handler-patterns)
- [Error handling](#error-handling)
- [State and database](#state-and-database)
- [Middleware and observability](#middleware-and-observability)
- [Production checklist](#production-checklist)
- [TS ↔ Rust boundary](#ts--rust-boundary)
- [Anti-patterns](#anti-patterns)

## When to use Rust

| Use Rust | Stay in TypeScript |
|---|---|
| High-throughput/low-latency APIs | CRUD BFF, Server Actions |
| Streaming (gRPC, WebSocket fanout) | Marketing pages, dashboards |
| Infra proxies, gateways, workers | Supabase-backed app logic |
| Correctness-critical parsers | Form validation, UI state |
| Long-running background jobs | Webhooks simple enough for Next |

Don't rewrite working TS in Rust without measured latency/cost/correctness need.

## Project layout

```
crates/
 api/ # Axum router, handlers
 domain/ # business logic, no HTTP deps
 db/ # SQLx queries, migrations
 proto/ # gRPC/contract types (if used)
services/
 gateway/
 src/
 main.rs
 routes/
 middleware/
 error.rs
 state.rs
```

Rules:
- **Handlers thin** - extract, validate, call domain, map response
- **Domain pure** - testable without HTTP mocks
- **No `unwrap()`/`expect()` in handlers** - use `?` + AppError

## Axum handler patterns

```rust
use axum::{extract::State, Json};
use std::sync::Arc;

pub async fn create_item(
 State(state): State<Arc<AppState>>,
 auth: AuthUser, // custom extractor
 Json(payload): Json<CreateItemRequest>,
) -> Result<Json<ItemResponse>, AppError> {
 payload.validate()?; // or validator crate
 let item = domain::create_item(&state.db, auth.user_id, payload).await?;
 Ok(Json(item.into()))
}
```

Extractors for typed inputs - compile-time request contract:
- `Json<T>`, `Query<T>`, `Path<T>` with serde + validation
- Custom `FromRequestParts` for auth (JWT/API key)

Nested routers for scale:

```rust
let api = Router::new()
 .nest("/v1/items", items_router())
 .nest("/v1/users", users_router());
```

## Error handling

Unified `AppError` → HTTP response:

```rust
pub enum AppError {
 Validation(String),
 Unauthorized,
 NotFound,
 Conflict(String),
 Internal(anyhow::Error),
}

impl IntoResponse for AppError {
 fn into_response(self) -> Response {
 let (status, msg) = match self {
 AppError::Validation(m) => (StatusCode::BAD_REQUEST, m),
 AppError::Unauthorized => (StatusCode::UNAUTHORIZED, "Unauthorized".into()),
 AppError::NotFound => (StatusCode::NOT_FOUND, "Not found".into()),
 AppError::Conflict(m) => (StatusCode::CONFLICT, m),
 AppError::Internal(e) => {
 tracing::error!(error = %e, "internal error");
 (StatusCode::INTERNAL_SERVER_ERROR, "Internal error".into())
 }
 };
 (status, Json(json!({ "error": msg }))).into_response()
 }
}
```

Never return internal error details to clients in production.

## State and database

```rust
pub struct AppState {
 pub db: PgPool,
 pub config: Arc<Config>,
}
```

SQLx rules:
- Migrations in `migrations/` - run at startup or deploy step
- Parameterized queries always - no string concat SQL (SQLx 0.9 `query*()` take
 `impl SqlSafeStr`: a `&'static str`, or an `AssertSqlSafe(..)` to review)
- Explicit pool limits: `max_connections`, acquire timeout
- `query_as!` / `query!` macros for compile-time checked SQL when feasible

Timeouts on all external I/O (DB, HTTP clients, Redis).

## Middleware and observability

Standard `tower-http` layers via `tower::ServiceBuilder` (runs top to bottom, so
outermost first; chained `Router::layer` calls run bottom to top):

```rust
Router::new()
 .route(/* ... */)
 .layer(ServiceBuilder::new()
   .layer(TraceLayer::new_for_http()) // method, uri, latency, status (ids: SetRequestIdLayer)
   .layer(CompressionLayer::new())
   .layer(CorsLayer::new() /* configured */)
   .layer(TimeoutLayer::with_status_code(StatusCode::REQUEST_TIMEOUT, Duration::from_secs(30))))
```

- **`tracing` + `tracing-subscriber`** - JSON logs in production
- **`RUST_LOG`** for filter control
- Graceful shutdown: `axum::serve(...).with_graceful_shutdown(signal)`
- Health: `/health/live` (process up), `/health/ready` (DB reachable)
- Prometheus metrics on `/metrics` when project uses them

## Production checklist

```
Rust ship gate:
- [ ] No unwrap/expect in handler path
- [ ] All I/O has timeouts
- [ ] Graceful shutdown wired
- [ ] Structured logging (tracing)
- [ ] CORS locked to real domains
- [ ] Rate limit on auth/sensitive routes
- [ ] Errors don't leak internals
- [ ] DB pool sized for instance
- [ ] Migrations versioned and applied
- [ ] Non-root Docker user (if containerized)
```

## TS ↔ Rust boundary

Preferred patterns:

| Pattern | When |
|---|---|
| REST + OpenAPI | Public APIs, BFF calling Rust service |
| gRPC + protobuf | Internal high-perf service mesh |
| Message queue | Async jobs, decoupled pipelines |
| Shared Postgres | Both read/write with clear ownership per table |

Rules:
- **One owner per table** - either TS/Supabase or Rust, not both writing blindly
- Contract-first: OpenAPI/proto is source of truth; codegen TS types
- Auth: pass JWT or service token; validate in Rust extractor
- Version endpoints (`/v1/`) - breaking changes get new version

## Anti-patterns

- `unwrap()` in request path
- Business logic in `main.rs`
- Global mutable state without `Arc`
- Missing request timeouts
- Leaking SQL errors to HTTP response
- Duplicating Supabase RLS logic in Rust without documented reason
- Hand-syncing Rust structs and TS interfaces

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
