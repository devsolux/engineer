# Observability: logs, errors, traces

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

See `coding-principles.md` § observability.
Research: `research/deep-2026-07.md` § observability (OTel) · Gaps: `research/gap-audit.md`.

## Contents
- [Three pillars](#three-pillars)
- [Structured logging](#structured-logging)
- [Error tracking (Sentry)](#error-tracking-sentry)
- [Next.js integration](#nextjs-integration)
- [Alerts](#alerts)
- [Rust services](#rust-services)
- [Privacy in logs](#privacy-in-logs)
- [Anti-patterns](#anti-patterns)

## Three pillars

| Pillar | Question | Tools |
|---|---|---|
| **Logs** | What happened? | Axiom, Datadog, Vercel logs |
| **Errors** | What broke? | Sentry, Bugsnag |
| **Traces** | Where was it slow? | OpenTelemetry, Vercel OTel |

**60-second rule**: follow one request ID from browser → Server Action → DB.

## Structured logging

```typescript
// lib/logger.ts
interface LogEvent {
 level: "info" | "warn" | "error";
 message: string;
 userId?: string;
 action?: string;
 traceId?: string;
 durationMs?: number;
 error?: string;
}

export function log(event: LogEvent) {
 console.log(JSON.stringify({ ...event, ts: new Date().toISOString() }));
}
```

Use in Server Actions:

```typescript
log({ level: "info", action: "createProject", userId: user.id, traceId });
```

Never `console.log` random strings in production paths.

## OpenTelemetry (Next.js template)

Copy **`templates/lib/instrumentation.ts`** to the app root (or `src/instrumentation.ts`):

```bash
pnpm add @vercel/otel
cp "$ENGINEER/templates/lib/instrumentation.ts" ./instrumentation.ts
# export OTEL_SERVICE_NAME=my-app
```

`register()` runs **once** when a Next server instance starts (not every request). Restart `next dev` after changing the file.

**Runtime split (required):**

| Runtime | Do |
|---|---|
| `NEXT_RUNTIME === "nodejs"` | Load `@vercel/otel` / Node SDK |
| `edge` | Return early or load edge-safe only - never NodeSDK |
| Browser | No instrumentation.ts |

Template uses dynamic `import("@vercel/otel")` only on Node so Edge analysis does not pull Node-only packages.

**Span / Sentry tag conventions:**

| Attribute | When |
|---|---|
| `app.user_id` | Authenticated request (hash if policy requires) |
| `app.org_id` | Multi-tenant path |
| `app.route` | Route **pattern**, not raw sensitive ids |
| `app.action` | Server Action name |
| `app.job_id` | Background job (`background-jobs.md`) |
| `app.trace_kind` | `request` \| `job` \| `webhook` |

**Sentry ↔ trace:** set tag `trace_id` from the active OTel span so one ID follows browser → action → worker.

## Error tracking (Sentry)

```bash
npm install --save-dev --save-exact @sentry/wizard@6.13.0
npm exec --offline -- sentry-wizard -i nextjs
```

Wraps:
- Server Components / Actions
- Client error boundaries
- Edge middleware

User context:

```typescript
Sentry.setUser({ id: user.id }); // no email in high-security apps
```

Source maps uploaded in CI for readable stack traces.

## Next.js integration

```tsx
// app/global-error.tsx
"use client";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
 useEffect(() => {
 Sentry.captureException(error);
 }, [error]);
 return (/* user-safe UI */);
}
```

Route Handlers: catch, log with context, return safe JSON - Sentry in catch block.

## Alerts

| Signal | Threshold | Action |
|---|---|---|
| Error rate | >0.1% of requests | Page on-call |
| p95 latency | 2× baseline | Investigate |
| Failed webhooks | Stripe dashboard | Fix handler |
| Auth failure spike | 5× normal | Possible attack |

Start with Sentry alerts + Stripe webhook failure emails - expand later.

## Rust services

```rust
tracing::info!(user_id = %user_id, latency_ms = elapsed, "request completed");
```

Export OTLP to same backend as Next.js for unified traces.

Health endpoints: `/health/live`, `/health/ready` - monitor in deploy platform.

## Privacy in logs

- No passwords, tokens, full credit card numbers
- Hash or truncate PII when possible
- GDPR: log retention policy documented

## Anti-patterns

- String-only logs (unsearchable)
- Logging full request bodies with secrets
- No error tracking in production
- Ignoring Sentry noise instead of fixing root cause
- Client-only error reporting (misses server failures)
