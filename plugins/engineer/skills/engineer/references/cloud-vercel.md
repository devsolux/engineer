# Cloud: Vercel runtime, identity, security, limits, cost

**Last verified**: 2026-08-29 · **Review cadence**: 3 months

**Related**: `deploy-ops.md` (deploy ritual, env tiers, rollback, smoke; this module extends its Vercel section),
`frontend-performance.md` (CWV, images), `backend-security.md` (headers, CSP, secrets split), `observability.md`
(Sentry, alerting), `cloud-platforms-iac.md` (AWS/GCP/IaC counterpart, pending).

## Contents
- [Scope and boundary](#scope-and-boundary)
- [Defaults](#defaults)
- [Decision gates](#decision-gates)
- [Deploy model](#deploy-model)
- [Runtime](#runtime)
- [Identity](#identity)
- [Domains, security, observability](#domains-security-observability)
- [Limits and pricing](#limits-and-pricing)
- [Cost guardrails](#cost-guardrails)
- [CI gates](#ci-gates)
- [Failure modes and anti-patterns](#failure-modes-and-anti-patterns)
- [Agent codegen policy](#agent-codegen-policy)
- [Scan signals](#scan-signals)
- [Ship checklist](#ship-checklist)
- [Conflicts with deploy-ops.md](#conflicts-with-deploy-opsmd)
- [Sources](#sources)

## Scope and boundary

Owns: Vercel Functions and Fluid compute, runtime versions, regions, ISR/cache, cron, Queues/Workflows, OIDC federation
out of Vercel, environments and Sensitive env vars, Deployment Protection, monorepo layout, domains/DNS, Firewall/WAF/bot
management, Drains/OTel/Speed Insights, plan tiers, limits, pricing units, Spend Management. Does not own: release ritual
and migrations, CSP construction, Sentry, AWS/GCP side (see Related), Supabase RLS/branching (`backend-supabase.md`).

## Defaults

- Keep Fluid compute on (default for new projects since 2025-04-23). Never disable it.
- Node.js runtime for every Route Handler and Server Action; pin `engines.node: "24.x"` (Node 20 deprecated 2026-10-01).
  Python only for thin glue; pin `requires-python`.
- Function region next to the Supabase region; `maxDuration` and `memory` sized per function (defaults 300 s, 2 GB), never the ceiling.
- Every credential-shaped Production/Preview env var is **Sensitive**; team policy "Enforce Sensitive Environment Variables" on.
- Standard Protection with Vercel Authentication on every non-Hobby project; one Protection Bypass secret per automation
  consumer (CI, Playwright, uptime monitor).
- OIDC federation (Team issuer mode) for any AWS/GCP call. No long-lived cloud keys, ever.
- Pro before any commercial use or real traffic; Spend Management with auto-pause on day one.
- Firewall on from day one; Bot Protection in challenge mode on auth/checkout routes.
- Security headers with a nonce CSP; `@vercel/otel` plus a Log Drain and a Trace Drain to an external sink (Pro+).
  Sentry stays the system of record for exceptions.

## Decision gates

**Stay on Vercel** for SSR, request/response APIs, edge routing, ISR, crons that finish in minutes, and LLM streaming
under the duration cap. **Move the workload off Vercel** (Fly/Railway for simplicity, AWS Fargate/Lambda or GCP Cloud Run
for scale; see `cloud-platforms-iac.md`) when it runs longer than 800 s (Pro GA cap) or must survive deploys (batch, ETL,
ML inference, media processing; Vercel Workflows is the on-platform alternative, see Runtime); when it needs a persistent
process (WebSocket server, stateful queue consumer, GPU worker); or when it is a high-throughput queue consumer or serves
heavy egress.
**Python services never run on Vercel Functions unless** the service is a thin request/response handler
(FastAPI/Flask/Django) with no worker loop, no `while True`, no multi-minute job, and no deploy lifecycle separate from
the frontend. Everything else goes to Fly/Railway/Cloud Run/Fargate; Vercel keeps the webhook.
**Plan tier**: the cliffs under Cost guardrails. **Edge runtime**: legacy code only (see Runtime). **Supabase Edge
Functions** only when code must sit next to Postgres/Auth with its own deploy lifecycle.

## Deploy model

- **Git integration**: native GitHub/GitLab/Bitbucket integration so PR comments, branch URLs, and the fork-PR gate work.
  `vercel deploy --prebuilt` from CI only when a pre-deploy step must block the deploy.
- **Environments**: Production, Preview, Development, plus Custom Environments (Pro 1, Enterprise 12). A `staging` Custom
  Environment or a long-lived preview branch with branch-scoped Preview vars (CLI 22.0.0+) gives a stable pre-prod URL.
- **Sensitive env vars**: write-only and encrypted after creation; Production and Preview only, never Development. Values
  of 32+ characters are redacted in build logs (`VERCEL_AUTOMATION_BYPASS_SECRET` and `VERCEL_OIDC_TOKEN` always). Local
  dev gets separate low-privilege values; `.env*.local` gitignored.
- **Deployment Protection**: Standard Protection (everything except the live production domain) is on all plans; All
  Deployments, Password Protection, Passport, and Trusted IPs are priced per the table. Automation uses
  `x-vercel-protection-bypass` with a per-consumer secret, never disabled protection. Once protected, `VERCEL_URL`-based
  server-to-server fetches return 401; use relative paths.
- **Rollback**: Instant Rollback re-aliases domains, no rebuild; it does not revert env vars or database state, and it turns
  off auto-assignment of production domains until `vercel promote` or Undo Rollback. Alert if `main` receives commits while rolled back.
- **Monorepos**: one Vercel Project per deployable app with its own Root Directory. Vercel skips builds for unaffected
  workspace packages when package names are unique and internal deps are declared; otherwise
  `ignoreCommand: "npx turbo-ignore"`. Related Projects: max 3, same repo, not for CLI deploys.

## Runtime

**Fluid compute** bills Active CPU (only while code executes; I/O wait is free), Provisioned Memory (whole instance
lifetime, including I/O wait), and Invocations. A slow LLM stream bills memory the whole time; the 1,024 file descriptors
per instance are shared across concurrent requests. `waitUntil()` from `@vercel/functions` for post-response work.
Streaming: AI SDK `streamText`/`toTextStreamResponse`; Edge must begin responding within 25 s, Node streams to `maxDuration`.
**Node vs Edge**: **Next.js 16.3 removed `runtime = 'edge'` for routes and pages**; they always run on Node.
`middleware.ts` is renamed `proxy.ts` and runs on Node (the edge path still works but is deprecated). Custom OTel spans
are unsupported on Edge. Proxy/middleware is routing only, never the authorization boundary.
**Versions** (as-of 2026-08-29, /docs/functions/runtimes, /changelog): Node 24.x default, 22.x and 20.x selectable, Node
20 deprecated 2026-10-01; Python 3.12 default, 3.13/3.14; Next.js 16 GA 2025-10-21. **Regions**: default `iad1`;
Enterprise adds `functionFailoverRegions`. Multi-region only for real data locality (EU residency); prices differ (Sao
Paulo about 1.7x iad1).

**ISR and cache**: stale-serve on revalidation failure can mask a broken origin for days; alert on it. On-demand
revalidation is scoped to the calling deployment and domain only. Next.js 16: `cacheComponents: true` plus `'use cache'`
replace `experimental.ppr`/`dynamicIO`; `revalidateTag(tag, cacheLifeProfile)` is the two-argument form (single-argument
deprecated); `updateTag()`/`refresh()` are the new APIs. **Cron**: a cron invokes a normal Function under the same
duration cap. Verify a `CRON_SECRET` header server-side; the `vercel-cron/1.0` user agent is spoofable.
**Queues and Workflows**: Vercel Workflows (`'use workflow'` / `'use step'`, Python SDK too) is the durable-execution path
for pause/resume across minutes to months. It is built on Vercel Queues, in public beta (uncertain, no GA date located
as-of 2026-08-29); multi-region workflows need `workflow` 5.0.0-beta.33+. Treat both as beta-to-early-GA; check status
before betting a money path on it. Pricing has its own dimensions (Events, Data Written, Data Retained); keep PII out of
step state.

## Identity

- Vercel is an OIDC identity provider (OIDC Federation is GA). Builds get `VERCEL_OIDC_TOKEN`; functions get the
  `x-vercel-oidc-token` header, reused up to 90 min with a 2 h TTL. Use **Team issuer mode**
  (`https://oidc.vercel.com/team_example`), not Global.
- AWS: register the issuer as an IAM OIDC provider; trust policy matches `aud` (`https://vercel.com/team_example`) and
  `sub` (`owner:team_example:project:my-app:environment:production`); exchange via `@vercel/oidc-aws-credentials-provider`.
  GCP: Workload Identity Federation pool/provider.
- One role per environment; no `project:*` or `environment:*` wildcards, so a compromised preview cannot assume the
  production role. Re-validate after a project rename.
- Pin `AWS_REGION` as an explicit env var; Vercel's auto-set value shifts under multi-region routing or failover.
- Vercel platform tokens (CLI, REST, Terraform) are not OIDC-exchangeable: scope to project/team, store as CI secrets,
  rotate. Owner/Billing roles stay with 1 to 2 named people; automation never carries them. Drain/OTel sinks: signed or
  short-lived auth; verify `x-vercel-signature`, not source IPs.

## Domains, security, observability

**DNS**: Vercel nameservers when Vercel is the only consumer of the zone; wildcard domains require nameservers (ACME
challenge). External DNS: A/ALIAS for apex, CNAME for `www`, values read from the project's Domains tab (never hardcode
an IP), add both apex and `www`, redirect one to the other. Re-add MX records or mail breaks. No AAAA (IPv6). Lower TTL
to 60 s 24 h before cutover. Audit for dangling CNAMEs (subdomain takeover).

**Firewall/WAF**: DDoS mitigation, IP blocking, and custom rules are free on every plan; blocked traffic does not count
toward requests or transfer. Rate limiting is priced (table did not render this pass, uncertain). Attack Mode is a manual
incident toggle, not a standing posture. **No Cloudflare proxy mode or any reverse proxy in front of Vercel** when Bot
Protection matters; it masks the fingerprints. Bot Protection and AI Bots managed rulesets are GA: challenge on login,
signup, checkout; decide log or deny for AI crawlers (default is allow).
**Headers**: HSTS, `X-Content-Type-Options`, `X-Frame-Options` or `frame-ancestors`, `Referrer-Policy`,
`Permissions-Policy`, nonce-based CSP via `headers()` or `vercel.json`. Never `script-src 'unsafe-inline'` as a permanent
hydration fix. No HSTS `preload` until every subdomain serves HTTPS. Verify with securityheaders.com. CSP construction
lives in `backend-security.md`.
**Drains** (logs, OTel traces, Speed Insights, Web Analytics, Connect events, Audit Logs): Pro/Enterprise only; Hobby
cannot export. In-dashboard log retention is 1 h / 1 day / 3 days (Hobby/Pro/Ent, /docs/plans), so Drains are the only
durable log store. The Configurable Log Drain REST endpoint is deprecated. **OTel and RUM**: `instrumentation.ts` with
`registerOTel({ serviceName: 'my-app' })` from `@vercel/otel`; a hand-rolled OTel SDK loses Session Tracing and Trace
Drains. Speed Insights is field Core Web Vitals (P75 to P99 by route) and captures no exceptions; Web Analytics is
pageviews/events. Sentry stays for errors.

## Limits and pricing

Every value as-of 2026-08-29. Pricing units have shifted repeatedly (bandwidth to Fast Data Transfer, GB-hours to Active
CPU plus Provisioned Memory, per-unit invocations); re-verify before quoting or embedding in cost code. Sources are paths
under vercel.com.

| Item | Value | Source |
|---|---|---|
| Plan base | Hobby $0; Pro $20/seat/month (Viewers free); Enterprise custom | /pricing |
| Hobby commercial use | Forbidden (fair use); overage pauses up to 30 days, no pay-to-unlock | /docs/limits/fair-use-guidelines |
| Function duration | Hobby 300 s max; Pro/Ent 300 s default, 800 s GA max, 1800 s beta | /docs/functions/limitations |
| Function memory | Hobby 2 GB / 1 vCPU; Pro/Ent 2 GB default, 4 GB / 2 vCPU max | /docs/functions/limitations |
| Body size | 4.5 MB request/response, hard (413 `FUNCTION_PAYLOAD_TOO_LARGE`) | /docs/functions/limitations |
| Bundle size | 250 MB Node/Bun, 500 MB Python, uncompressed; Large Functions beta 5 GB | /docs/functions/limitations |
| Concurrency | Up to 30,000 Hobby/Pro; 100,000+ Enterprise (uncertain Pro ceiling) | /docs/functions/limitations |
| Regions | Hobby 1; Pro up to 5; Enterprise all | /docs/functions/configuring-functions/region |
| Compute (Fluid) | Active CPU: Hobby 4 CPU-h/month, Pro $0.128/CPU-h iad1 ($0.128 to $0.221 by region). Provisioned Memory: Hobby 360 GB-h/month, Pro $0.0106/GB-h iad1 ($0.0106 to $0.0183). Invocations: Hobby 1M/month, Pro $0.60 per 1M | /docs/functions/usage-and-pricing |
| Fast Data Transfer / Edge Requests | Hobby 100 GB / 1M; Pro 1 TB then about $0.15/GB, 10M then about $2 per 1M (both uncertain) | /pricing |
| ISR / images (Pro) | About $0.40 per 1M ISR reads, $4 per 1M writes, $0.05 per 1K transforms [uncertain] | /pricing |
| ISR cache | Persists 31 days; purge about 300 ms; stale-serve with 30 s retry on failure | /docs/incremental-static-regeneration |
| Cron | 100/project all plans; Hobby daily (plus or minus 59 min), Pro/Ent per minute | /docs/cron-jobs/usage-and-pricing |
| Env vars | 1000 per environment per project; 64 KB total per deployment; 5 KB per var on Edge | /docs/environment-variables |
| Custom Environments | Hobby none; Pro 1; Enterprise 12 | /docs/deployments/environments |
| Builds | 45 min per deployment all plans; concurrent 1 Hobby, up to 500 Pro | /docs/limits |
| Deploys/day, projects/repo, hooks, proxy timeout | 100 / 6,000 per day; 25 / 150 per repo; hooks 5 (10 Ent); 120 s | /docs/limits, /docs/plans/hobby |
| Instant Rollback | Hobby previous only; Pro/Ent any prior production deployment | /docs/instant-rollback |
| Advanced Deployment Protection | Enterprise included; Pro $150/month add-on, 30-day minimum; Trusted IPs Enterprise only | /docs/deployment-protection |
| SSO | Pro add-on about $300/month (uncertain); Enterprise included | /pricing |
| WAF rules / IP blocks / managed rulesets | Rules 3/40/1000; project IP blocks 3/100/1000 (Hobby/Pro/Ent); OWASP rulesets and account-level IP blocking Enterprise only; 4 KB inspected per request included on Pro | /docs/vercel-firewall/vercel-waf |
| Drains | Pro/Ent; $0.50/GB uncompressed JSON; Audit Log Drains Enterprise | /docs/drains |
| Speed Insights | Hobby 1 project, 10k events/month, 7-day window; Pro $10/project/month plus $0.65 per 10k events, 30-day window; Ent 90 days | /docs/speed-insights/limits-and-pricing |
| Spend Management | Alerts at 50/75/100%, SMS at 100%; checks every few minutes, not instant | /docs/spend-management |

## Cost guardrails

**Cliffs**. Hobby to Pro: commercial use, a second seat, 300 s duration, Spend Management, Drains, RBAC, Custom
Environments, rollback beyond the previous deployment, per-minute cron. Pro to Enterprise: Trusted IPs, managed WAF
rulesets, account-level IP blocking, Audit Log Drains, SSO without the add-on, >12 custom environments, SLA, isolated
builds, or Pro overage regularly reaching low four figures a month.
**Spend Management** (Pro/Enterprise, Owner or Billing role): budget below the real pain threshold (enforcement lags
several minutes), "pause production deployments" on, 50/75/100% web/email alerts plus SMS at 100%, and a webhook whose
`x-vercel-signature` is verified before acting. Raising the cap does not resume paused projects; each is resumed by hand.
Notify-only is not a guardrail. Same pattern as the AWS Budgets / GCP budget auto-disable in `cloud-platforms-iac.md`.
**First three bill surprises** (as-of 2026-08-29; mechanics from official docs, practitioner threads not re-verified this
pass): (1) Image Optimization transforms from unbounded `deviceSizes`/`imageSizes` times user-uploaded images: bound the
arrays, `minimumCacheTTL` 30 days, everything through `next/image`. (2) ISR read amplification from low `revalidate`
windows plus crawler traffic (every cache miss during regeneration counts): raise windows, batch on-demand revalidation.
(3) Fast Data Transfer from large bundles, video, PDFs served from Vercel: move media to object storage plus a CDN.
Runners-up: Provisioned Memory on LLM streaming routes, Drains without sampling, Speed Insights on every project,
Password Protection assumed included on Pro. Right-size `memory` (billed by allocation); reconcile Usage against the cap
monthly, since Vercel does not throttle Pro at 100% unless auto-pause is on.

## CI gates

- Fail on any static AWS/GCP credential (`AWS_SECRET_ACCESS_KEY`, service-account JSON) in code or env definitions;
  require a role ARN or Workload Identity resource instead.
- Fail if a `vercel.json` function lacks explicit `maxDuration`, or sets 800/1800 without a justification comment or
  linked issue. Fail on `runtime: 'edge'` in new routes or pages.
- Warn on cron routes without secret verification and on single-argument `revalidateTag`.
- Verify `engines.node` (24.x) and `requires-python` pins; fail if a required env var is missing.
- E2E against the Preview URL with `x-vercel-protection-bypass` from CI secrets before merge.
- Bundle-size budget on PRs; weekly cleanup of stale previews; diff WAF rule changes in PR/Terraform plan; validate Drain
  endpoints via the delivery-validation API; OTel traces visible in a preview.
- Pre-cutover gate: Pro plan confirmed, Spend Management with auto-pause enabled.

## Failure modes and anti-patterns

- Rollback after a destructive migration (code reverts, schema does not; forward-fix); rollback without `vercel promote`
  (pushes to `main` silently stop reaching production).
- Preview carrying production Stripe/Supabase keys behind an unauthenticated preview URL; a Protection Bypass secret
  committed or in a webhook URL (bypasses every method until rotated **and redeployed**).
- OIDC trust policy with wildcard `sub`; `AWS_REGION` left to Vercel's auto value (calls land in an empty region after
  failover); function region far from Supabase.
- 504 `FUNCTION_INVOCATION_TIMEOUT` from a job that belonged in Workflows or off-platform; 413 from base64 uploads over
  4.5 MB (use signed upload URLs); `too many open files` under Fluid concurrency; env payload over 64 KB failing opaquely.
- One Vercel Project building several monorepo apps from one build script; Cloudflare orange-cloud in front of Vercel
  with Bot Protection on (constant re-challenges); a Python worker with a polling loop as a Function.
- CSP `unsafe-inline` as the permanent hydration fix; HSTS preload before all subdomains were HTTPS; hardcoded
  `76.76.21.21` in IaC; wildcard domain via CNAME (cert never issues); Drain endpoint trusting source IPs only; PII
  logged into a third-party sink; Owner/Billing role granted to everyone.

## Agent codegen policy

- MUST default new routes and Server Actions to Node; MUST NOT emit `runtime = 'edge'` unless asked.
- MUST use `@vercel/oidc-aws-credentials-provider` or GCP WIF for any cloud SDK client in a function; MUST NOT read
  static cloud keys from env; SHOULD default to Team issuer mode and per-environment `sub` conditions.
- MUST pin `engines.node` and Python version; MUST set explicit, justified `maxDuration` (60 s or less by default) and
  `memory`; MUST flag work that needs Workflows or off-platform compute.
- MUST scope new env vars per environment and ask before creating a non-Sensitive var named like
  `KEY|SECRET|TOKEN|PASSWORD|SERVICE_ROLE`; MUST use placeholders only (`my-app.vercel.app`, `prj_example`,
  `team_example`, `example.com`, `arn:aws:iam::123456789012:role/example-role`).
- MUST NOT hardcode a Protection Bypass secret, Drain secret, or Vercel per-unit price; MUST NOT suggest disabling
  Deployment Protection to fix tests.
- MUST add secret verification to any generated cron endpoint; MUST use two-argument `revalidateTag`; MUST generate
  nonce-based CSP and the baseline headers, never `'unsafe-inline'` without a flag.
- MUST use `registerOTel()` from `@vercel/otel`; MUST scaffold one Vercel Project per monorepo app; MUST bound
  `images.deviceSizes`/`imageSizes` and set `minimumCacheTTL`.
- MUST NOT scaffold a reverse proxy in front of Vercel without a bot-signal warning; SHOULD include "enable Spend
  Management with auto-pause" in any go-live checklist.

## Scan signals

Flag:
- `prj_`, `team_`, or `dpl_` identifiers, real team slugs, or a real `*.vercel.app` preview hostname in committed docs,
  config, or IaC (placeholders only; treat as leak candidates).
- `VERCEL_TOKEN`, `VERCEL_AUTOMATION_BYPASS_SECRET`, `x-vercel-protection-bypass=` literals, `CRON_SECRET`, or Drain
  secrets as values in the repo, `vercel.json`, or a committed `.env*` file; `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
  or a PEM/service-account JSON block anywhere.
- `runtime: 'edge'` or `export const runtime = 'edge'` in new code; `experimental.ppr` or `dynamicIO` flags;
  single-argument `revalidateTag(`; `maxDuration` at 800/1800, project-wide, or absent; `while True`/long polling loops
  in a Python directory deployed to Vercel; cron routes with no secret check.
- CSP `unsafe-inline` for `script-src`; no header config in a production Next.js app; hardcoded `76.76.21.21`; a reverse
  proxy in front of a Vercel domain; identical credential values across Production and Preview; one `buildCommand`
  building several apps; hardcoded Vercel unit prices.
Positive: `@vercel/oidc-aws-credentials-provider` plus `AWS_ROLE_ARN` and pinned `AWS_REGION`; runtime version pins;
explicit per-function `maxDuration`/`memory`; `'use workflow'`/`'use step'` for durable logic; `@vercel/otel` in
`instrumentation.ts`; `turbo-ignore`; bounded `images.deviceSizes`.

## Ship checklist

```
Vercel gate (on top of deploy-ops.md smoke):
- [ ] Pro plan (never Hobby for commercial or real traffic); Owner/Billing limited to 1-2 people
- [ ] Spend Management: budget, auto-pause, 50/75/100% alerts, signed webhook
- [ ] Fluid compute on; no runtime: 'edge' in new code; Node 24.x and Python pins present
- [ ] Every function: explicit maxDuration and memory; region co-located with Supabase
- [ ] No static AWS/GCP keys in env; OIDC role per environment; AWS_REGION pinned
- [ ] All credential-shaped Production/Preview vars Sensitive; team enforcement policy on
- [ ] Standard Protection on; one bypass secret per automation consumer, none in repo
- [ ] Cron endpoints verify a secret; durable logic on Workflows or off-platform, not cron polling
- [ ] Long-running / worker / heavy-egress workloads confirmed NOT on Vercel Functions
- [ ] Next.js 16 caching: cacheComponents, two-argument revalidateTag, bundle under limits
- [ ] Domains: apex + www, redirect, DNS values from Domains tab, MX re-added; firewall rules on
      auth/checkout, Bot Protection challenge, AI Bots decided, no reverse proxy
- [ ] Headers: HSTS, nosniff, frame-ancestors, Referrer-Policy, nonce CSP; securityheaders.com pass
- [ ] Log Drain + Trace Drain to external sink; @vercel/otel wired; Sentry still on
- [ ] Rollback runbook: migration-state check first; vercel promote after; monorepo one project per app
```

## Conflicts with deploy-ops.md

- No contradictions found. Node 24 LTS default is confirmed by Vercel's runtime docs (as-of 2026-08-29); its "Node 20 is
  end-of-life" phrasing is stronger than Vercel's "deprecated on 2026-10-01". Treat 20.x as unusable for new work either way.
- `deploy-ops.md` says "Protect preview URLs if sensitive: Vercel authentication or IP allowlist". The IP allowlist (Trusted
  IPs) is Enterprise only; Pro teams get Vercel Authentication and the paid Password Protection add-on. A nuance, not a contradiction.
- Its forward-fix rollback guidance is corroborated by Vercel's docs and extended with the auto-assignment side effect.
  "Enable Speed Insights for CWV" still holds; this module adds that it is per-project priced on Pro and never replaces Sentry.

## Sources

Official Vercel docs read 2026-08-29 (vercel.com): /docs/fluid-compute, /docs/functions (limitations, runtimes,
usage-and-pricing, region, streaming), /docs/incremental-static-regeneration, /docs/cron-jobs, /docs/workflows, /docs/oidc,
/docs/deployments/environments, /docs/environment-variables, /docs/deployment-protection, /docs/instant-rollback,
/docs/monorepos, /docs/git, /docs/limits, /docs/domains, /docs/vercel-firewall, /docs/bot-management, /docs/headers,
/docs/drains, /docs/tracing/instrumentation, /docs/speed-insights, /docs/plans, /docs/spend-management, /docs/pricing,
/pricing, /changelog; nextjs.org/blog/next-16. Research corpus: `research/cloud/results/vercel-*.json` (four items), load on demand only.
