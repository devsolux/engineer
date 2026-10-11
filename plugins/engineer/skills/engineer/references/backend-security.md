# Application security: headers, CSP, and hardening

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Complements `backend-auth.md` (identity) and `backend-database.md` (RLS).
**AI tools / MCP / skills**: load **`ai-security.md`** (this module stays app headers + HTTP).
Delegate gstack `/cso` before shipping auth/payment/AI-tool surfaces.

Summary corpus: `research/security-research.md` · Deep: `research/deep-2026-07.md` § security · Gaps: `research/gap-audit.md`

## Contents
- [Threat model](#threat-model)
- [Security headers](#security-headers)
- [Content Security Policy](#content-security-policy)
- [Server Actions and API hardening](#server-actions-and-api-hardening)
- [Secrets and env](#secrets-and-env)
- [XSS and HTML injection](#xss-and-html-injection)
- [File uploads](#file-uploads)
- [Dependency security](#dependency-security)
- [Privacy basics](#privacy-basics)
- [Ship checklist](#ship-checklist)
- [Anti-patterns](#anti-patterns)
- [AI boundary](#ai-boundary)

## Threat model

| Layer | Protects against | Module |
|---|---|---|
| RLS | Data exfiltration via anon key | backend-database |
| Auth | Unauthorized mutations | backend-auth |
| Zod + validation | Injection, malformed input | typescript, backend-api |
| Headers + CSP | XSS, clickjacking, MIME sniff | **this module** |
| Rate limits | Abuse, brute force | backend-api, enforcement |
| CSP reporting | XSS residual, misconfig | this module (Report-Only → enforce) |

## Security headers

Next.js ships **no default security headers** - configure in `next.config.ts`:

```typescript
// next.config.ts
const securityHeaders = [
 { key: "X-DNS-Prefetch-Control", value: "on" },
 { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
 { key: "X-Content-Type-Options", value: "nosniff" },
 { key: "X-Frame-Options", value: "DENY" },
 { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
 { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

export default {
 async headers() {
 return [{ source: "/:path*", headers: securityHeaders }];
 },
};
```

Verify with [securityheaders.com](https://securityheaders.com) after deploy.

## Content Security Policy

Most effective XSS defense. **Nonce-based CSP** for App Router (per-request):

```typescript
// proxy.ts (Next 16) or middleware.ts (Next 15) - generate nonce, set CSP, pass x-nonce to layout
import { NextResponse, type NextRequest } from "next/server";

export function proxy(request: NextRequest) {
 const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
 const csp = [
 "default-src 'self'",
 `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
 `style-src 'self' 'nonce-${nonce}' 'unsafe-inline'`,
 "img-src 'self' blob: data: https:",
 "font-src 'self'",
 "connect-src 'self' https://*.supabase.co",
 "frame-ancestors 'none'",
 "object-src 'none'",
 "base-uri 'self'",
 "form-action 'self'",
 ].join("; ");

 const requestHeaders = new Headers(request.headers);
 requestHeaders.set("x-nonce", nonce);

 const response = NextResponse.next({ request: { headers: requestHeaders } });
 response.headers.set("Content-Security-Policy", csp);
 // Promote after Report-Only phase:
 // response.headers.set("Content-Security-Policy-Report-Only", csp + "; report-uri /api/csp-report");
 return response;
}
```

### CSP reporting pipeline (Report-Only → enforce)

1. **Report-Only** first: send `Content-Security-Policy-Report-Only`, `Reporting-Endpoints`, modern `report-to`, and compatibility `report-uri` as response headers.
2. **Ingest** both `application/reports+json` batches and legacy `csp-report` JSON. Use `templates/security/csp-reporting.ts`; connect its `allow` callback to the app's durable rate limiter and `record` to existing observability.
3. **Minimize before persistence**: retain document origin, blocked origin/marker, effective directive, disposition and status only. Never retain raw bodies, full URLs/query strings, samples, policies, source files, referrers, IPs, user agents, cookies, identities, or arbitrary attacker text.
4. **Bound abuse**: same-origin document admission, content-type allowlist, body/batch limits, rate limiting, aggregation and TTL. Treat reports as unauthenticated attacker-controlled telemetry, not proof of exploitation.
5. **Triage** by directive/origin/build and distinguish extensions, stale clients and first-party regressions. Alert on a sustained new first-party cluster, not individual reports.
6. **Promote** the exact observed policy to enforcement only after critical journeys and browser tests pass with no unexplained first-party violations. Keep reporting enabled after promotion.
7. **Rollback** the policy independently from application code through a reviewed configuration or feature flag; never relax to broad `unsafe-inline`/`unsafe-eval` as an incident shortcut.

Rules:
- Start with `Content-Security-Policy-Report-Only` in staging
- Nonce CSP requires dynamic rendering on protected routes
- Tighten `connect-src` for analytics/Stripe domains explicitly
- Never `unsafe-eval` in production
- `Report-Only` detects violations but does not mitigate them; it is a rollout phase, not the final security control
- CSP reports are lossy browser telemetry and cannot establish absence of XSS

## Server Actions and API hardening

See `backend-api.md` for full gates. Security-specific:

- Auth + authorization on **every** mutation
- Rate limit auth, billing, contact endpoints
- `allowedOrigins` in `next.config` behind reverse proxies
- Webhook signature verify on **raw body** (backend-webhooks)
- No stack traces in JSON responses
- CSRF: structural (POST + Origin) - not a substitute for auth

Keep Next.js **patched** - RSC protocol vulnerabilities disclosed 2025-2026.

## Secrets and env

| Var | Client OK? |
|---|---|
| `NEXT_PUBLIC_*` | Yes - treat as public |
| Supabase anon key | Yes (RLS protects) |
| Service role, Stripe secret, webhook secret | **Never client** |

- `.env.example` committed; `.env.local` gitignored
- gitleaks in CI (enforcement-rules.md)
- Rotate on leak; never commit secrets "temporarily"

## XSS and HTML injection

- **`dangerouslySetInnerHTML`** - DOMPurify sanitize server-side only
- User markdown → sanitize or render as plain text
- Never trust client for entitlements or role checks
- CSP as backstop when sanitization fails

## File uploads

Supabase Storage or S3:
- Validate MIME type + extension server-side
- Max size limits
- Storage RLS - user can only write own path
- Scan if accepting user uploads at scale (ClamAV / vendor)

## Dependency security

`npm audit` / Snyk / Dependabot find *known-CVE* packages. They do **nothing** against the
2025-2026 supply-chain attack class - malicious lifecycle scripts, compromised maintainers,
typosquats, and template poisoning ship a clean audit. Layer these controls; deeper dropper
taxonomy and detection tiers live in **`malware-detection.md`**, consume-side maintainer
posture in **`oss-maintainer.md`**.

- **Deny install scripts by default.** Lifecycle hooks (`preinstall`/`postinstall`/`prepare`)
  are the dominant execution primitive - Nx s1ngularity (2025-08) harvested tokens from a
  `postinstall`; Shai-Hulud 2.0 (2025-11) moved to a `preinstall`. Run `npm ci --ignore-scripts`
  (npm v12, 2026, disables auto scripts by default), pnpm `onlyBuiltDependencies` allowlist, or
  Bun `trustedDependencies`. Read a build script for shell-spawn/network/env-read before
  allowlisting it. Note the bypasses: native-addon rebuild (`binding.gyp`/node-gyp) and a
  dependency-shipped `.npmrc` still execute.
- **Frozen lockfile everywhere.** `npm ci` / `--frozen-lockfile` / `--immutable` with committed
  lockfiles, local and CI. This is subresource-integrity for the dependency graph - it refuses
  drift but does **not** catch a malicious-but-consistent version.
- **Name-resolution discipline.** Scope internal packages and reserve the bare names publicly
  (dependency confusion - Microsoft flagged 33 such npm packages 2026-05); pin one registry
  index; check name edit-distance / hallucinated names before installing a command copied from
  a blog or an LLM (typosquats install silently).
- **Release cooldown.** A 7-14 day minimum-release-age (pnpm `minimumReleaseAge`) is the single
  most effective control against the compromised-maintainer class (Sept-2025 npm phish wave hit
  chalk/debug/ansi-styles; CISA alert 2025-09-23).
- **Provenance where it exists.** Verify with `npm audit signatures`, `gh attestation verify`,
  or PyPI attestations (SLSA v1.2 approved 2025-11 adds a Source track; npm provenance GA via
  Sigstore; PyPI PEP 740). Provenance proves the *build path, not honest intent* - a compromised
  CI publishes valid provenance. Treat a sudden provenance loss as a slow-down signal; do **not**
  block on mere absence (most legit packages haven't adopted it), and note a git-cloned template
  has no registry provenance at all.
- **Assume ambient exposure.** Install/build code runs with full developer/CI credentials.
- **Reviewable build surfaces.** xz-utils (CVE-2024-3094, 2024) hid its payload in test fixtures
  and a build macro present only in the release tarball - never equate source review with
  artifact trust; treat binary fixtures and build machinery as code.

## Privacy basics

Not legal advice - engineering minimums:
- Privacy policy link on signup
- Cookie consent if non-essential tracking (EU)
- Data export/delete endpoints for GDPR requests (plan with legal)
- Minimize PII in logs and analytics

## Ship checklist

```
Security gate:
- [ ] HSTS + X-Frame-Options + nosniff configured
- [ ] CSP deployed (report-only → enforce)
- [ ] CSP report ingestion is bounded, privacy-minimized, rate-limited, retained briefly, and monitored after enforcement
- [ ] No secrets in NEXT_PUBLIC_ or client bundle
- [ ] Server Actions: auth + Zod + rate limit on sensitive
- [ ] Webhooks: signature + idempotency
- [ ] Deps: frozen lockfile + `--ignore-scripts` default; release cooldown; audit clean or documented exceptions
- [ ] gstack /cso on auth/payment paths
- [ ] If LLM/tools/MCP: ai-security.md checklist complete
- [ ] Next.js on a patched 15/16.x (Server Action origin/CSRF fixes)
- [ ] `serverActions.allowedOrigins` set if behind reverse proxy
```

## AI boundary

LLM features, agent tools, MCP, and skill installs are covered in **`ai-security.md`**.
Do not treat the model as an authorization layer; keep RLS + getUser() + Zod.

## Anti-patterns

- RLS as only security layer
- Enabling paid features without pay on `?success=true` URL
- CSP with `unsafe-eval`
- Service role in client bundle
- Skipping rate limits on login/signup
- Logging passwords or tokens
- Trusting client-side role checks
- Unrestricted shell/MCP tools without ai-security review
