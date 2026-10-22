# Feature flags: rollout and kill switches

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

Controlled rollout without redeploy. Observability on flag evals:
`observability.md`. Deploy process: `deploy-ops.md`.
Entitlements (paid plan): `billing-stripe.md` - **do not** use flags as the only paywall.

## Contents
- [Maturity ladder](#maturity-ladder)
- [Flag types](#flag-types)
- [Env-based flags (MVP)](#env-based-flags-mvp)
- [Database flags (per org / user)](#database-flags-per-org--user)
- [Percentage rollout](#percentage-rollout)
- [Kill switch](#kill-switch)
- [Vercel Flags / Global Config](#vercel-flags--global-config)
- [Flag lifecycle](#flag-lifecycle)
- [Flags vs entitlements](#flags-vs-entitlements)
- [Testing](#testing)
- [Anti-patterns](#anti-patterns)
- [Composition](#composition)

## Maturity ladder

| Stage | Approach | When |
|---|---|---|
| MVP | Env var `FEATURE_X=true` | Single tenant, no % rollout |
| Early product | DB flags table + admin UI | Per-org or per-user toggles |
| Scale | Vercel Flags, LaunchDarkly, PostHog, Statsig | % rollout, targeting, audit, kill switch |

Start env-based; graduate when non-engineers need toggles, % rollout, or instant kill.

## Flag types

| Type | Purpose | Lifetime |
|---|---|---|
| Release | Ship dark; turn on gradually | Days-weeks; delete after 100% |
| Experiment | A/B with metrics | Until decision; then remove |
| Ops / kill switch | Disable risky path instantly | Until incident over; prefer permanent config for forever-ops |
| Permission / beta | Allowlist orgs | Until GA |

**Short-lived by default.** Flags older than ~1-2 release cycles without an owner are debt.

## Env-based flags (MVP)

```typescript
// lib/flags.ts
export const flags = {
 newDashboard: process.env.NEXT_PUBLIC_FEATURE_NEW_DASHBOARD === "true",
 billingV2: process.env.FEATURE_BILLING_V2 === "true",
} as const;
```

Rules:
- **`NEXT_PUBLIC_*`** only for client-safe flags (UI visibility)
- Server-only flags without prefix (security-sensitive features)
- Default `false` - opt-in per environment in Vercel project settings
- Document each flag in PR; remove within 2 sprints after full rollout

```typescript
// Server Component
import { flags } from "@/lib/flags";

export async function DashboardPage() {
 if (flags.newDashboard) return <NewDashboard />;
 return <LegacyDashboard />;
}
```

## Database flags (per org / user)

```sql
create table public.feature_flags (
 key text not null,
 scope text not null check (scope in ('global', 'org', 'user')),
 scope_id uuid, -- null only for global
 enabled boolean not null default false,
 check ((scope = 'global') = (scope_id is null)),
 unique nulls not distinct (key, scope, scope_id) -- PG15+; a primary key forces scope_id not null
);

alter table public.feature_flags enable row level security;
-- read: authenticated users read global + their org/user rows
-- write: service role or admin role only
```

Server evaluation:

```typescript
export async function isEnabled(key: string, ctx: { orgId?: string; userId: string }) {
 const supabase = await createClient();
 const scopes = ["scope.eq.global", `and(scope.eq.user,scope_id.eq.${ctx.userId})`]; // ids from server auth only
 if (ctx.orgId) scopes.push(`and(scope.eq.org,scope_id.eq.${ctx.orgId})`);
 const { data } = await supabase
 .from("feature_flags")
 .select("enabled")
 .eq("key", key)
 .or(scopes.join(","))
 .order("scope", { ascending: false }) // most specific wins: user > org > global
 .limit(1)
 .maybeSingle();
 return data?.enabled ?? false;
}
```

Dedupe per request with React `cache()`. Cross-request: `'use cache'` + `cacheLife` (Next.js 16
Cache Components; replaces `unstable_cache`) cannot read cookies - cache only cookie-free reads
(e.g. global rows) and keep the TTL under the kill-switch SLA.

## Percentage rollout

Deterministic bucket by user id (stable across sessions):

```typescript
function bucket(userId: string, key: string): number {
 const hash = crypto.createHash("sha256").update(`${key}:${userId}`).digest();
 return hash.readUInt32BE(0) % 100; // not hash[0] % 100: one byte puts 58.6% in a "50%" rollout
}

export function isInRollout(userId: string, key: string, percent: number): boolean {
 return bucket(userId, key) < percent;
}
```

Rollout ladder (typical):
1. Staff / internal orgs (0-1%)
2. Beta allowlist
3. 5% → 25% → 50% → 100% with error/latency watch between steps

Log flag evaluations in dev; sample in prod for debugging stuck rollouts.
Pair with canary/observability when the flag gates a deploy risk.

## Kill switch

An ops flag default **on** (feature live) that can flip **off** without redeploy.

| Requirement | Detail |
|---|---|
| Fast read path | Global Config / DB / flag SaaS - not a slow third-party on every request without cache |
| Server enforce | Kill switch checked server-side for mutations, not only UI hide |
| Owner + runbook | Who flips it; link from incident doc |
| Default safe | Prefer fail-closed for money/AI spend paths when config missing |

```typescript
// Server Action
if (!(await isEnabled("ai_export_v2", ctx))) {
 throw new Error("Feature temporarily unavailable");
}
```

Do not wait for a full Vercel redeploy to stop a bleeding feature.

## Vercel Flags / Global Config

For Next.js on Vercel:
- Define flags in the Vercel Flags dashboard (provider, GA 2026-04) or in `flags.ts` with the
  Flags SDK (`flags` package, `flag()` from `flags/next`; `@vercel/flags` is the deprecated name)
- Evaluate in Proxy (`proxy.ts`; Next.js 16 renamed `middleware`) for route gating and
  `precompute`, or in RSC for UI
- Overrides via Flags Explorer (Vercel Toolbar, needs `FLAGS_SECRET`) in preview deployments
- Global Config (Edge Config until 2026-07; `@vercel/global-config`) for low-latency kill switches

Use when non-engineers need instant kill without redeploy.

## Flag lifecycle

```
1. Define flag (default off in prod) + owner + removal date
2. Ship code behind flag (both paths tested)
3. Enable internal -> beta orgs -> % rollout
4. Monitor errors/latency (observability.md)
5. Remove flag + dead code branch (same PR series as 100% on)
```

**Anti-pattern**: flags living > 1-2 months after full rollout - combinatorial test debt.

## Flags vs entitlements

| Concern | Use |
|---|---|
| Paid plan includes feature X | Stripe entitlements / plan table (`billing-stripe.md`) |
| Gradual rollout of a free feature | Feature flag |
| Emergency disable | Kill switch flag |
| Seat counts | `billing-seats.md` |

Never hide a paid capability only in the client while the API still works.

## Testing

- Unit: both branches of `if (flag)` have tests or explicit skip with ticket
- E2E: run critical path with flag on AND off in CI matrix (high-value flags only)
- pgTAP: if flags in DB, test RLS on `feature_flags` table

## Anti-patterns

| Don't | Do |
|---|---|
| Flag without default-off in prod | Explicit env per environment |
| Client-only gate for paid features | Server enforce + RLS / entitlements |
| 20 stale flags | Delete after rollout |
| Random % without stable user hash | Deterministic bucket |
| Flag check in hot loop uncached | Cache DB flags per request |
| Security behind public env flag | Server-only evaluation |
| Kill switch only hides a button | Block Server Actions too |
| Using flags as the billing system | Stripe entitlements |

## Composition

| Module | When |
|---|---|
| `deploy-ops.md` | Env tiers, preview overrides |
| `observability.md` | Alert on flag-gated error spikes |
| `billing-stripe.md` | Entitlements vs feature flags |
| `billing-metered.md` | Usage limits are not flags |
| `backend-database.md` | Flags table RLS |
| `backend-admin.md` | Who can toggle staff flags |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
