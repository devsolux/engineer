# Observability: logs, errors, traces

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

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
| **Errors** | What broke? | Sentry, BugSnag |
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
| Browser | Not `instrumentation.ts`; client init goes in `instrumentation-client.ts` (Next 15.3+) |

Template uses dynamic `import("@vercel/otel")` only on Node and skips Edge tracing (`@vercel/otel` is Edge-compatible; `NodeSDK` is not).

`@vercel/otel` 2.1.3 peers OTel JS 2.x / experimental 0.2xx. OTel JS 3.0 / 0.300 (2026-10-20; Node >=22.15; `sdk-trace-base`/`-node` replaced by `sdk-trace`) is outside that range: keep OTel peers on 2.x / 0.2xx until `@vercel/otel` widens it.

**Span / Sentry tag conventions:**

| Attribute | When |
|---|---|
| `app.user_id` | Authenticated request (hash if policy requires) |
| `app.org_id` | Multi-tenant path |
| `app.route` | Route **pattern**, not raw sensitive ids |
| `app.action` | Server Action name |
| `app.job_id` | Background job (`background-jobs.md`) |
| `app.trace_kind` | `request` \| `job` \| `webhook` |

Caveat: OTel semconv now owns an `app.*` namespace (Development: `app.build_id`, `app.screen.*`, ...) and its naming guide discourages custom keys under semconv namespaces. These six do not clash today; give new keys a reverse-domain prefix (`com.acme.*`). Next root spans already carry Stable `http.route`.

**Sentry ↔ trace:** set tag `trace_id` from the active OTel span so one ID follows browser → action → worker. In `@sentry/nextjs` v11 scope tags reach errors only; put span data in span attributes. If `@vercel/otel` owns the tracer provider, set `enableOpenTelemetrySetup: false` in the server `Sentry.init` (default `true`) and follow Sentry's OpenTelemetry custom-setup guide.

## Error tracking (Sentry)

```bash
npm install --save-dev --save-exact @sentry/wizard@8.0.1
npm exec --offline -- sentry-wizard -i nextjs
```

Wizard 8.x installs `@sentry/nextjs` ^11 (Next.js 14-16, Node >=20.19). It writes:
- `instrumentation-client.ts` (browser), `sentry.server.config.ts`, `sentry.edge.config.ts`
- `instrumentation.ts`: loads config by `NEXT_RUNTIME`, exports `onRequestError = Sentry.captureRequestError` (Next routes Server Component, Route Handler, Server Action and proxy errors there)
- `app/global-error.tsx` (React render errors); `withSentryConfig` from `@sentry/nextjs/config`
- Server Action spans still need `Sentry.withServerActionInstrumentation`

User context:

```typescript
Sentry.setUser({ id: user.id }); // no email in high-security apps
```

v11 replaced `sendDefaultPii` with `dataCollection`, whose defaults apply even when unset and mostly default to `true` (`userInfo`, `cookies`, `httpHeaders`, ...): set the keys to `false` explicitly in high-security apps.

Source maps uploaded in CI for readable stack traces.

## Next.js integration

```tsx
// app/global-error.tsx (Next 16.3+ `retry`; older: `reset`)
"use client";

export default function GlobalError({ error, retry }: { error: unknown; retry: () => void }) {
 useEffect(() => {
 Sentry.captureException(error);
 }, [error]);
 return (/* user-safe UI inside its own <html><body> */);
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
