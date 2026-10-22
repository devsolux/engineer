# Background jobs: queues, workers, and async work

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

Use when work must **outlive a single HTTP request**: email, webhooks fan-out,
exports, embeddings, retries, multi-step money paths. Complements `python.md`
(workers), `backend-webhooks.md` (ingress), `backend-api.md` (sync handlers).

Research: `research/deep-2026-07.md` § jobs/workers · Gaps: `research/gap-audit.md`

## Contents
- [When not Server Actions](#when-not-server-actions)
- [Decision tree](#decision-tree)
- [Patterns](#patterns)
- [Idempotency and retries](#idempotency-and-retries)
- [Observability](#observability)
- [Security](#security)
- [Anti-patterns](#anti-patterns)
- [Ship checklist](#ship-checklist)

## When not Server Actions

| Stay sync (Server Action / route) | Move to a job |
|---|---|
| < ~2s DB write + response | > 10s work, external APIs that flaky-retry |
| User must wait for result | Email, PDF, bulk export, crawl |
| Single-tenant small mutation | Stripe webhook side effects (fan-out) |
| Simple notification | Multi-step workflows with resume |

**Rule:** if money, email, or external write can fail mid-flight, use a **durable job** with retries + dead-letter visibility.

## Decision tree

```
Need async work?
├── Vercel-only TS app, light volume
│ └── Inngest, Trigger.dev, or Vercel Workflows (hosted, TypeScript-native)
├── Already on Supabase + Postgres, want fewer vendors
│ └── pg-boss / Graphile Worker (jobs table in Postgres); Supabase Queues (pgmq, public alpha)
├── Python AI / heavy CPU service
│ └── FastAPI + Taskiq/Celery/Temporal (see python.md; arq maintenance-only)
└── High throughput / multi-service
 └── SQS / Cloud Tasks / NATS + workers
```

| Tool | Pros | Cons |
|---|---|---|
| **Inngest** | DX, steps, retries, Vercel-friendly | Vendor |
| **Trigger.dev** | Apache-2.0, self-host option, good TS | Ops/hosting choices |
| **pg-boss** | Postgres-only, simple | Ops on you; poll load |
| **Taskiq / Celery** | Python ecosystem | Separate process model |

## Patterns

### Webhook → enqueue (binding shape)

```typescript
// app/api/webhooks/stripe/route.ts
export async function POST(req: Request) {
 const raw = await req.text(); // signature verify first
 const event = verifyStripe(raw, req.headers);
 await inngest.send({ id: event.id, name: "stripe/event", data: { id: event.id, type: event.type } }); // id: 24h dedupe
 return Response.json({ received: true }); // fast ACK
}
```

Never do long work inside the webhook handler before ACK.

### Job handler (idempotent)

```typescript
// jobs/stripe-event.ts (Inngest SDK v4: triggers live in the options object)
export const stripeEvent = inngest.createFunction(
 { id: "stripe-event", retries: 5, triggers: { event: "stripe/event" } },
 async ({ event, step }) => {
 await step.run("dedupe", async () => {
 // insert event.id into processed_events UNIQUE - skip if exists
 });
 await step.run("apply", async () => {
 // mutate billing state
 });
 }
);
```

### Server Action that enqueues

```typescript
"use server";
export async function requestExport(projectId: string) {
 const user = await requireUser();
 await rateLimit(user.id); // abuse surface - scanned by engineer-scan
 await inngest.send({ name: "export/requested", data: { projectId, userId: user.id } });
 return { ok: true };
}
```

## Idempotency and retries

| Concern | Practice |
|---|---|
| At-least-once delivery | Assume duplicates; unique keys on side effects |
| Partial failure | Step functions / multi-step with checkpoint |
| Poison messages | Max retries + dead-letter table/stream + alert |
| Ordering | Usually not guaranteed - design for out-of-order |

## Observability

- Log `jobId`, `eventId`, `userId` (if any), attempt number
- Metric: queue depth, fail rate, p95 duration
- Alert on dead-letter growth and retry storms
- Correlate with request ID when job was user-triggered (`observability.md`)

## Security

- Jobs run with **service role** carefully - least privilege per job type
- Never put secrets in job payloads; store IDs and load secrets from env
- Rate-limit **enqueue** paths (user-facing export/delete)
- AuthZ: verify the actor may act on the resource **before** enqueue and re-check in the worker if privileges can change

## Anti-patterns

- Long Stripe webhook handlers with nested API calls
- Fire-and-forget `fetch` to your own API without retries
- Unbounded retries without backoff
- Job payloads carrying PII unnecessarily
- Using Server Actions or `after()` as a free queue (route max duration, no retries/durability)

## Ship checklist

- [ ] Durability chosen (Inngest / Trigger / pg-boss / Python worker)
- [ ] Webhooks ACK fast; work enqueued
- [ ] Idempotency key on money and email paths
- [ ] Retries + dead-letter + alert
- [ ] Enqueue path rate-limited + auth'd
- [ ] Worker secrets not in payload
- [ ] Runbook: how to replay a failed job

## Related

- `backend-webhooks.md` - ingress verify
- `backend-api.md` - sync boundaries
- `python.md` - Python workers
- `billing-stripe.md` - payment side effects
- `observability.md` - traces and errors
- `enforcement.md` - scanners / CI
