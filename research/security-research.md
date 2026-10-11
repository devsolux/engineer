# Application security research corpus (2026)

**Date**: 2026-07-13  
**Feeds**: `backend-security.md`, `backend-api.md`, `backend-auth.md`, `backend-webhooks.md`, `billing-stripe.md`, `compliance-privacy.md`  
**Deep pass**: [deep-2026-07.md](deep-2026-07.md) § security

## Executive summary

Next.js App Router apps ship **with zero default security headers**. Server Actions are **public POST endpoints**. Supabase anon keys are **public by design** — RLS is the data boundary. Production hardening is multi-layer, never single-gate.

1. **Headers + CSP nonces** — HSTS, frame deny, nosniff, Permissions-Policy; per-request nonce CSP
2. **Server Actions = public APIs** — auth + authorization + Zod + rate limit on every mutation
3. **RLS deny-by-default** — all `public` tables; `(select auth.uid())` performance pattern
4. **Webhooks** — raw body signature verify; idempotency on event ID; return 200 fast
5. **Secrets** — never `NEXT_PUBLIC_*` for service role / Stripe secret / webhook secrets
6. **Patch cadence** — RSC protocol / Next.js CVEs 2025–2026; dependabot + CI audit
7. **Compose** — gstack `/cso` for infrastructure + supply-chain; engineer for app-layer gates

Canonical: nextjs.org CSP + OpenTelemetry guides, OWASP ASVS / CSP Cheat Sheet, MakerKit Server Action security (2026), Stripe webhook best practices, Supabase RLS docs.

---

## 1. Threat model (SaaS stack)

| Layer | Asset | Threat | Control | Module |
|---|---|---|---|---|
| Edge / CDN | HTML, assets | MITM, cache poisoning | HSTS, HTTPS-only | backend-security |
| Browser | Session cookies | XSS, CSRF | CSP nonce, HttpOnly cookies, Next CSRF structure | backend-security, backend-auth |
| Server Actions | Mutations | Unauth calls, brute force | `getUser()`, Zod, rate limit | backend-api |
| PostgREST | Row data | Anon-key exfiltration | RLS + policy tests | backend-database |
| Storage | Objects | Path traversal, public leaks | Bucket policies + path conventions | backend-storage |
| Webhooks | Billing state | Spoofed events, replay | Signature + idempotency | backend-webhooks |
| Supply chain | Dependencies | Malicious package | lockfile, audit, pnpm ignore-scripts | enforcement |
| Logs / OTel | PII | Leak in traces | Scrub PII; no secrets in spans | observability, compliance-privacy |

**Binding rule**: frontend checks are UX. Security is server + RLS.

---

## 2. Security headers (no defaults)

Next.js does **not** set security headers by default (confirmed across 2026 audits). Configure in `next.config` headers() and/or middleware.

| Header | Recommended | Why |
|---|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Force HTTPS |
| `X-Content-Type-Options` | `nosniff` | Block MIME sniff |
| `X-Frame-Options` | `DENY` (or CSP `frame-ancestors`) | Clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit leak |
| `Permissions-Policy` | Disable camera/mic/geo by default | Capability lockdown |
| `Content-Security-Policy` | Nonce + strict-dynamic | XSS primary control |

Verify post-deploy: securityheaders.com, Mozilla Observatory.

---

## 3. CSP + nonces (App Router)

**Sources**: Next.js CSP guide (middleware/proxy nonce), OWASP CSP Cheat Sheet

### Pattern

1. Middleware generates per-request `nonce` (`crypto.randomUUID` → base64)
2. Set `Content-Security-Policy` on response
3. Pass `x-nonce` request header into layout / Script tags
4. Prefer `script-src 'self' 'nonce-…' 'strict-dynamic'` — avoid `'unsafe-eval'` in prod
5. Stage with `Content-Security-Policy-Report-Only` before enforce

### Hard truths

- Nonce CSP forces **dynamic** rendering on protected routes (trade-off vs pure static)
- Do **not** rewrite all `<script>` tags in middleware to inject nonces (attacker scripts would get them too) — only trusted render path
- Whitelist `connect-src` for Supabase, Stripe, analytics, Sentry explicitly
- Third-party widgets (Intercom, GTM) blow open CSP — isolate or avoid on high-trust surfaces

### Style note

`'unsafe-inline'` on `style-src` remains common with Tailwind/runtime styles; tighten when feasible. Script nonces matter more for XSS impact.

---

## 4. Server Actions as public endpoints

**Sources**: MakerKit Secure Server Actions (Jan 2026), Arcjet blog, Authgear Next.js security 2026, Next.js docs mutations

### Checklist (every action)

| Gate | Required | Notes |
|---|---|---|
| Auth (`getUser()`) | Yes (unless intentionally public) | Never middleware-only trust |
| Authorization | Yes | Resource ownership / org role |
| Zod `safeParse` | Yes | All input including FormData |
| Rate limit | Sensitive paths | Auth, billing, delete, contact, export |
| No secret in closures | Yes | Captured env/session bugs |
| Safe errors | Yes | No stack/SQL leak to client |
| `'use server'` file hygiene | Yes | Prefer dedicated action files |

### Rate limiting (2026 practice)

| Tool | Fit |
|---|---|
| **@upstash/ratelimit** + Redis | Default for Vercel/serverless; sliding window |
| **Arcjet** | Shield + bot + rate limit combined |
| In-memory Map | Dev only — not multi-instance safe |

Order: **auth → rate limit → validate → mutate**.  
Key by `user.id` when authenticated; IP (`x-forwarded-for` / platform IP) when anonymous.

engineer encodes Upstash pattern in `backend-api.md`. **Gap**: no dedicated rate-limit module/template; scanners don't enforce presence of limiter calls.

---

## 5. Auth surface

- Middleware: cookie `getAll`/`setAll` for session refresh (Supabase SSR)
- Decisions: `getUser()` on server mutations — not `getSession()` alone
- Never service role in client bundle
- Auth responses: respect no-store / session cache headers — CDN session bleed risk
- CSRF: Next structural protection (POST + Origin/Host) is **not** auth

---

## 6. RLS multi-tenant (security view)

**Sources**: MakerKit RLS 2026, Supabase multi-tenant patterns, pgvector RAG-with-permissions

| Pattern | Isolation | When |
|---|---|---|
| User-scoped `user_id` | Personal data | B2C, single-player |
| Org + memberships | Team SaaS | Default multi-tenant |
| Schema-per-tenant | Strong isolation | Enterprise / compliance heavy |

Production team pattern:

```
organizations → memberships(user_id, org_id, role) → resources(org_id)
```

- SECURITY DEFINER helpers in private schema for membership checks (avoid recursive RLS)
- Index `org_id`, `user_id`, FK columns used in policies
- Wrap: `(select auth.uid())` not bare `auth.uid()`
- pgTAP for every table + role matrix

**Vector/RAG**: embeddings tables need same RLS as documents (`owner_id` / org); similarity search without RLS is a data leak. See Supabase “RAG with permissions”.

engineer documents patterns in `backend-database.md` but **lacks a dedicated multi-tenant module** (memberships, invites, role hierarchy, transfer ownership).

---

## 7. Webhooks & Stripe

| Rule | Why |
|---|---|
| Verify signature on **raw body** | Parsed JSON invalidates HMAC |
| Idempotency on `event.id` | Stripe may deliver duplicates |
| Do not assume event order | Parallel/out-of-order delivery |
| Unlock only via webhook | Never `success_url` query trust |
| Return 200 quickly | Enqueue heavy work |
| Idempotency keys on Stripe **writes** | Safe retries on Checkout Session create |

---

## 8. File uploads

- Metadata in Postgres + object in Storage
- Path: `{ownerId}/…` never user-controlled bucket names
- MIME + size validate server-side
- Signed URLs for private buckets; short TTL for exports
- Virus/malware scanning is product-tier (not in skill default)

---

## 9. Dependencies & supply chain

- pnpm with lifecycle scripts blocked by default (keep it)
- CI: `pnpm audit` / OSV; gitleaks on PRs
- Pin major versions of auth/billing SDKs
- Review new deps: maintainer, downloads, install scripts
- Next.js patch within days of security advisories (RSC protocol history)

Compose with gstack `cso` for secrets archaeology + skill supply chain.

---

## 10. Privacy / GDPR engineering

Engineering-owned (see `compliance-privacy.md`):

- Export API (machine-readable)
- Delete/anonymize account (transactional; no partial delete)
- Consent storage for marketing cookies / analytics
- Log/PII scrubbing in OTel and Sentry

Legal owns policy text. Engineering owns the pipes.

---

## 11. Observability as security control

- Request ID across browser → Action → DB
- Alert on webhook failure rate, auth error spikes, 429 storms
- Sentry user id without email in high-security apps
- OTel: Next.js built-in spans via `instrumentation.ts` + `@vercel/otel` (see deep corpus)

---

## 12. Ship checklist (security)

- [ ] Security headers live + verified
- [ ] CSP Report-Only → enforce path decided
- [ ] All public tables RLS + pgTAP
- [ ] Every mutation: getUser + Zod + rate limit (sensitive)
- [ ] Webhooks: raw body, signature, idempotency
- [ ] No secrets in `NEXT_PUBLIC_*`
- [ ] Stripe unlock only from webhook + DB entitlements
- [ ] gitleaks + audit in CI
- [ ] `/cso` on auth/payment surfaces
- [ ] `engineer-scan --strict` green

---

## 13. What the skill encodes vs misses

| Encoded | Thin / missing |
|---|---|
| Headers, CSP sketch | Full CSP report-uri / reporting pipeline |
| Action five gates | Automated rate-limit presence lint |
| RLS patterns + pgTAP | Multi-tenant invites/roles module |
| Webhook flow | Background job after webhook (queue module) |
| Dependency mention | SBOM / provenance policy |
| Privacy export/delete | Cookie consent CMP integration detail |
| Sentry sketch | Full OTel collector runbook |

---

## Sources (2026)

- nextjs.org — CSP, OpenTelemetry, Server Actions security notes  
- OWASP — CSP Cheat Sheet, ASVS  
- MakerKit — Secure Server Actions (2026), RLS best practices  
- Arcjet — Server Action security  
- Authgear — Next.js security 2026  
- Stripe — idempotent requests, webhook best practices  
- Supabase — RLS, RAG with permissions  
- Upstash — rate limiting on serverless  

**Anti-slop**: prefer vendor docs + MakerKit/Stripe over generic listicles when encoding rules.
