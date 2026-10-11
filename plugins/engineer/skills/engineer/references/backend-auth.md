# Backend auth: Supabase SSR, sessions, and gates

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Cookie-based SSR auth for Next.js + Supabase. RLS is the data layer gate - auth
is the application layer gate. Both must align.

## Contents
- [Client layout](#client-layout)
- [Root request interceptor (mandatory)](#root-request-interceptor-mandatory)
- [getClaims vs getUser](#getclaims-vs-getuser)
- [Auth flows](#auth-flows)
- [Profile sync](#profile-sync)
- [Server Action auth gate (every mutation)](#server-action-auth-gate-every-mutation)
- [Server Actions are public endpoints](#server-actions-are-public-endpoints)
- [@supabase/server (advanced)](#supabaseserver-advanced)
- [Anti-patterns](#anti-patterns)
- [Non-default auth adapters (Clerk / Auth.js)](#non-default-auth-adapters-clerk-authjs)

## Client layout

```
lib/supabase/
 client.ts # createBrowserClient - client components only
 server.ts # createServerClient - RSC, Server Actions, Route Handlers
 proxy.ts  # updateSession helper (Next 16 template). Older apps: middleware.ts helper.
```

Env vars:
- `NEXT_PUBLIC_SUPABASE_URL` - client + server
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - client + server (RLS-scoped)
- `SUPABASE_SERVICE_ROLE_KEY` - **server only**; bypasses RLS; admin jobs only

## Root request interceptor (mandatory)

Session refresh must run on the Next request boundary so cookies refresh correctly.

| Next version | Root file | Export |
|---|---|---|
| 16+ (greenfield) | `proxy.ts` | `proxy` |
| 13-15 (detected) | `middleware.ts` | `middleware` |

**Detect first** (`project-detect.md`): Next 16+ uses `proxy.ts`. If the app still has only `middleware.ts`, keep it until a deliberate `middleware-to-proxy` migration. Do not delete a working interceptor without verifying cookies still persist under `next start` (dev-mode-only success is a known 2026 `@supabase/ssr` + Next 16 failure mode).

**Must implement `getAll` AND `setAll`** on cookies. Missing `setAll` causes random logouts and failed token refresh.

When auth cookies are set, Supabase SSR passes cache-control headers that must reach the response - do not strip them at CDN/proxy:

```
Cache-Control: private, no-cache, no-store, must-revalidate, max-age=0
```

```typescript
// lib/supabase/proxy.ts - shared helper (older apps: middleware.ts)
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
 let response = NextResponse.next({ request });

 const supabase = createServerClient(
 process.env.NEXT_PUBLIC_SUPABASE_URL!,
 process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
 {
 cookies: {
 getAll() {
 return request.cookies.getAll();
 },
 setAll(cookiesToSet, headers) {
 cookiesToSet.forEach(({ name, value, options }) =>
 response.cookies.set(name, value, options),
 );
 Object.entries(headers).forEach(([key, value]) =>
 response.headers.set(key, value),
 );
 },
 },
 },
 );

 // Refresh session - do not remove
 await supabase.auth.getUser();

 return response;
}
```

```typescript
// proxy.ts (Next 16+) — Next 15 keeps middleware.ts + export function middleware
import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/proxy";

export async function proxy(request: NextRequest) {
  return updateSession(request);
}
```

Create a **new client per request** - never share across requests.

## getClaims vs getUser

| Context | Method | Why |
|---|---|---|
| Request-boundary route gate | `getClaims()` | JWT verified locally; no DB round-trip |
| Server Components | `getUser()` | Validated against Supabase Auth server |
| Server Actions | `getUser()` | Same - auth decisions on mutations |
| Route Handlers | `getUser()` or Bearer verify | Depends on client type |

Rules:
- **Never** use `getSession()` alone for server auth decisions - session can be stale/forged
- **Never** trust client-side session for protected mutations
- After sign-out: clear cookies server-side + redirect

### Enforcement

| Rule | Tool |
|---|---|
| Root interceptor + setAll | Code review + integration test (`middleware.ts` or `proxy.ts`) |
| getUser not getSession | `engineer-scan --backend` |
| No localStorage JWT | `engineer-scan --strict` |
| allowedOrigins config | Deploy checklist (`backend-api.md`) |

See `enforcement.md`.

## Auth flows

| Flow | Pattern |
|---|---|
| Email/password | Server Action → `signInWithPassword` → redirect |
| OAuth | `signInWithOAuth` → `/auth/callback` route → exchange code → cookies |
| Magic link | `signInWithOtp` + email template |
| Password reset | Rate-limited action → Supabase reset email |
| Protected routes | Middleware refresh + RLS as second layer |

OAuth callback route (Server):

```typescript
// app/auth/callback/route.ts
import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
 const { searchParams, origin } = new URL(request.url);
 const code = searchParams.get("code");
 if (code) {
 const supabase = await createClient();
 await supabase.auth.exchangeCodeForSession(code);
 }
 return NextResponse.redirect(`${origin}/dashboard`);
}
```

## Profile sync

Store app profile in `public.profiles` synced from `auth.users`:

```sql
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
 insert into public.profiles (id, email)
 values (new.id, new.email);
 return new;
end;
$$;

create trigger on_auth_user_created
 after insert on auth.users
 for each row execute function public.handle_new_user();
```

## Server Action auth gate (every mutation)

Order: **rate limit (if sensitive) → auth → authorize → validate → mutate**

```typescript
"use server";

export async function updateProfile(input: unknown): Promise<Result<ProfileDto>> {
 const parsed = profileSchema.safeParse(input);
 if (!parsed.success) return { ok: false, error: "Invalid input" };

 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) return { ok: false, error: "Unauthorized", code: "AUTH" };

 // RLS enforces row access; explicit check for cross-user ops
 const { error } = await supabase
 .from("profiles")
 .update(parsed.data)
 .eq("id", user.id);

 if (error) return { ok: false, error: error.message };
 return { ok: true, data: /* map to DTO */ };
}
```

## Server Actions are public endpoints

Next.js Server Actions:
- Accept POST only
- Compare Origin vs Host (CSRF structural defense)
- **Do NOT** authenticate callers automatically

Every action needs: Zod validation + auth + authorization. Treat as public API.

Configure for production behind proxies:

```typescript
// next.config.ts
const nextConfig = {
 experimental: {
 serverActions: {
 bodySizeLimit: "2mb",
 allowedOrigins: ["https://yourdomain.com"], // preview domains too
 },
 },
};
```

Rate-limit sensitive actions (login, signup, checkout, delete) - see
`backend-api.md`.

## @supabase/server (advanced)

Composable with `@supabase/ssr`:
- `@supabase/ssr` - cookie lifecycle
- `@supabase/server` - JWT verify, RLS-scoped context, admin client helpers

Default engineer stack: `@supabase/ssr`. Mention `@supabase/server` for advanced
multi-runtime setups.

## Anti-patterns

- JWT in `localStorage` (use cookie SSR flow)
- `getSession()` as sole server check
- Middleware without `setAll`
- Service role in client or `NEXT_PUBLIC_*`
- Skipping auth because "RLS handles it" (actions still callable)
- Caching responses that set auth cookies at CDN
- Shared Supabase client across requests

## Non-default auth adapters (Clerk / Auth.js)

**Default remains Supabase SSR.** Use this only when the product already chose another provider.

| Provider | Keep from engineer | Change |
|---|---|---|
| Supabase (default) | Full module | - |
| Clerk | RLS patterns still apply if using Supabase DB | Session via Clerk; map `userId` into RLS claims or app tables |
| Auth.js / NextAuth | Zod + rate limit + re-auth gates | Session strategy; never service-role in client |

Rules if not Supabase Auth:
- Still **get session server-side** on every mutation (no client-only trust)
- Still **RLS or equivalent** on data plane
- Still re-auth for delete-account / billing
- Document claim shape (`sub`, org ids) next to policies
- Do not fork half the module - pick one source of identity

Compose: `compliance-privacy.md` (export/delete), `backend-api.md` (CSRF/origins), `backend-multitenant.md` (membership).


---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
