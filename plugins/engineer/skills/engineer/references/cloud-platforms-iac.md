# Cloud platforms and IaC: Cloudflare, Fly, Railway, Render, Netlify, Terraform/OpenTofu

**Last verified**: 2026-08-29 · **Review cadence**: 3 months

**Related**: `deploy-ops.md` (release tiers, migrations, rollback), `infra-security.md` (token policy,
node/container hardening), `cloud-aws.md`, `cloud-gcp.md`, `cloud-vercel.md`, `python.md`, `observability.md`.

Opinionated greenfield defaults for a TS/Next + Python + Supabase stack; unverified numbers are `[uncertain]`.

## Contents
- [Scope and boundary](#scope-and-boundary)
- [Platform selection matrix](#platform-selection-matrix)
- [Cloudflare](#cloudflare)
- [Fly / Railway / Render / Netlify](#fly--railway--render--netlify)
- [Identity reality](#identity-reality)
- [Infrastructure as code](#infrastructure-as-code)
- [Cross-provider glue](#cross-provider-glue)
- [Limits and pricing](#limits-and-pricing)
- [Cost guardrails](#cost-guardrails)
- [CI gates](#ci-gates)
- [Failure modes and anti-patterns](#failure-modes-and-anti-patterns)
- [Agent codegen policy](#agent-codegen-policy)
- [Scan signals](#scan-signals)
- [Ship checklist](#ship-checklist)
- [Sources](#sources)

## Scope and boundary

Owns the edge/PaaS tier (Cloudflare, Fly.io, Railway, Render, Netlify, a Hetzner VPS baseline), whether
to adopt IaC at all, and cross-provider glue (secrets, telemetry, FinOps). Siblings own the rest; link, do
not repeat: Vercel (`cloud-vercel.md`, `deploy-ops.md`); AWS IAM/OIDC and GCP WIF (`cloud-aws.md`,
`cloud-gcp.md`); rotation, SSH/VPS/container hardening, backups (`infra-security.md`); Supabase service-role
and RLS (`backend-database.md`, `backend-auth.md`). Kubernetes, Helm, GitOps, and Ansible-class tooling stay
out of scope until the stack runs them. Supabase Postgres is the system of record; D1, KV, Fly and Render
Postgres are satellites or documented exceptions.

## Platform selection matrix

| Workload class | Default | Why |
|---|---|---|
| Next.js frontend | Vercel (Netlify as comparator) | Most mature Next hosting; Cloudflare's vinext is beta as of 2026-08-29 |
| Latency-sensitive edge HTTP / middleware | Cloudflare Workers | V8 isolates, near-zero cold start, global by default |
| Stateless Python API (FastAPI-class) | Fly.io Machines | Per-second billing, scale-to-zero, Dockerfile control; Render is the low-ops second |
| Background worker / queue consumer | Fly Machines or Railway service (no public port) | Second process in the same app; Fly idle-wait beats Render always-on |
| Scheduled cron | Render Cron Job; on Fly, GitHub Actions `schedule:` + flyctl | Fly has no native cron primitive |
| WebSocket / long-lived connections | Fly Machines, `min_machines_running >= 1` | Long-lived VMs; never Netlify Functions |
| Object storage with real egress | Cloudflare R2 | Zero egress, S3 API; Supabase Storage only for RLS-coupled objects |
| Postgres outside Supabase | Fly Managed Postgres, or self-hosted on Hetzner | Fly's unmanaged Postgres is explicitly unsupported |
| GPU / ML inference | Fly GPU Machines `[uncertain]` or a dedicated GPU provider | Railway/Render/Netlify have no GPU; this set is insufficient for production ML |
| High-bandwidth media; persistent disk, non-HTTP protocols, > 5 min runs | Hetzner VPS (hardened per `infra-security.md`), + object storage + CDN for media | PaaS per-GB bandwidth is not CDN pricing; the only class where a VPS beats a zero-ops platform |

Classify first, generate config second (PaaS research item, 2026-08-29). Gate to leave PaaS: when one
service's projected compute + bandwidth exceeds roughly 3-5x a mid-tier Hetzner VPS, evaluate a VPS and
accept the ops cost (Hetzner price `[uncertain]`, see Limits).

## Cloudflare

- **Workers**: V8 isolates, HTTP-shaped work only (limits in the table below); CPU-heavy jobs go to
  a Queue consumer or a service host. Raise CPU past the 30 s default via `limits.cpu_ms`.
- **Pages**: docs say "Start new projects with Workers"; new frontends use Workers + `[assets]`.
- **R2**: S3-compatible, zero egress; point existing S3 SDKs at the R2 endpoint, check parity before
  porting lifecycle or replication rules. Private by default; public access is a decision.
- **D1** (serverless SQLite): edge-local, read-mostly, per-tenant shardable; never a second primary next
  to Supabase without a sync boundary. **KV** (eventually consistent): config, flags, caches; never sessions.
- **Durable Objects**: single-threaded, strongly consistent actor per key on the SQLite backend
  (`new_sqlite_classes`): rate limiters, WebSocket rooms, per-tenant locks; no cross-object transactions.
- **Queues**: set `max_batch_size` and `max_batch_timeout`; add a dead-letter queue or the 100-retry /
  14-day ceiling drops messages silently. **Access**: admin surfaces on a Cloudflare-proxied domain only; keep app authz on.
- **Wrangler** (4.127.1, npm 2026-08-29): `name = "my-app-worker"`, `account_id = "<account-id>"`,
  pinned `compatibility_date`, explicit `compatibility_flags`, `[observability] enabled = true`,
  placeholder binding ids; `wrangler secret put <NAME> --env production`; `[vars]` non-secret only.
- **Next.js on Workers**: vinext is the recommended adapter and is beta; `@opennextjs/cloudflare`
  (1.20.4, npm 2026-08-29) is the stable fallback; run the compatibility checker in CI. Versus Vercel:
  wins on edge latency, R2 economics, DO/Queues, Access; loses on Next.js maturity (ISR, image
  optimization, server actions), adapter risk, CI identity. Decide explicitly.

## Fly / Railway / Render / Netlify

| | Fly.io | Railway | Render | Netlify |
|---|---|---|---|---|
| Deploy | `flyctl deploy` from a Dockerfile; `fly.toml` | GitHub App auto-deploy or `railway up`; Nixpacks or Dockerfile | Git auto-deploy or Deploy Hook URL; `render.yaml` Blueprint | Git integration or `netlify-cli`; `netlify.toml` |
| CI credential | `FLY_API_TOKEN`: app-scoped, `flyctl tokens create deploy -x <TTL> -a my-app` | `RAILWAY_TOKEN`: project token | `RENDER_DEPLOY_HOOK_URL`: bearer-style URL, one service | Site or personal API token |
| Runtime secrets | `flyctl secrets set` (encrypted, injected at boot); never `[env]` | `railway variables set`; sealed variables hide values but cannot be read back | `sync: false` env vars set in dashboard; never inline in `render.yaml` | Site env vars |
| Scaling | `auto_stop_machines`, `auto_start_machines`, `min_machines_running = 0` | Replicas per service; usage-billed | Per-instance plans, always-on; free tier suspends after 15 min idle, ~1 min cold start | Functions only, execution-time bounded |
| Postgres | Managed Postgres (supported); unmanaged Fly Postgres "not able to provide support or guidance" | Managed add-on, fine small/medium | Managed; free DB 1 GB, expires 30 days, no backups | None |
| Pricing unit | Per-second Machine + volume GB + egress GB | RAM GB-month, vCPU-month, egress GB, plan credit | Instance-hour by plan tier | Credits per GB-hour of function compute |
| Never | `min_machines_running = 0` for WebSockets; sleep-loop cron | Treat the included credit as a budget | Customer-facing traffic on free tier | Long-running Python, workers, WebSockets |

Common rules (vendor docs, 2026-08-29): web and worker are separate services, never one process with a
background loop. Pin the runtime (Dockerfile base, `nixpacks.toml`, Render runtime var). Front public endpoints
on usage-billed platforms with a CDN/WAF, or scale-to-zero plus per-GB egress becomes a denial-of-wallet
surface. Dashboard access equals env-var read/write: audit membership like IAM. Fly low-traffic APIs:
`auto_stop_machines = "suspend"`, `auto_start_machines = true`, `min_machines_running = 0`.

## Identity reality

**None of Cloudflare, Fly.io, Railway, Render, or Netlify offer GitHub Actions OIDC federation as of
2026-08-29.** Verified by absence in each vendor's CI/CD, GitHub Actions, and token-creation docs (Cloudflare
high confidence, PaaS medium-high); evidence of absence in documentation, not a vendor statement, so re-check
at every review. Vercel's status is `cloud-vercel.md`'s call. Every deploy job for these providers carries a
static credential that stays valid until revoked; the accepted ceiling (`infra-security.md` § Cloud IAM):

1. A **machine/deploy token** scoped to one app/project/zone/service and one environment; staging and
   production get separate, independently revocable tokens.
2. Held as a **GitHub Environment secret** (`environment: production` on the job), never repo-wide, so
   required-reviewer rules gate every job that can read it (the substitute for the missing OIDC step-up);
   never exposed to `pull_request_target` or fork workflows; passed only as `${{ secrets.NAME }}` to a
   SHA-pinned action or CLI step.
3. Expiry where supported (Fly `-x <TTL>`, Cloudflare token TTL); 90-day rotation, immediate on
   suspected leak or personnel change; owner, issue date, scope in the `infra-security.md` inventory.
4. **Personal tokens never.** A scoped, rotated machine token where OIDC does not exist is the
   documented fallback, not a violation; a Global API Key or account-wide token in CI is.

## Infrastructure as code

**Default for this stack: no dedicated IaC tool.** Committed `vercel.json`, `supabase/config.toml` +
migrations, `wrangler.toml`, `fly.toml`, and `render.yaml` are reviewable, versioned config. Adopt IaC
when any one is true: AWS/GCP resources beyond a single bucket; multiple environments that must stay
in parity; a compliance need for reviewable infra diffs; three or more engineers touching infra.
Re-evaluate on those triggers, not on calendar time.

| Tool | Pick when | Notes (as of 2026-08-29) |
|---|---|---|
| OpenTofu | Default engine once IaC is needed | MPL-2.0, Linux Foundation; drop-in CLI/provider compatible; 1.12.0 stable per opentofu.org, point release `[uncertain]` |
| Terraform | Existing HCP Terraform contract, Sentinel, vendor mandate | BUSL-1.1 since 2023-08; IBM acquisition effect on licence `[uncertain]` |
| SST v3 (Ion) | TS-native team going AWS (or Cloudflare) serverless | Pulumi engine, typed resource linking, live lambda dev; non-AWS coverage `[uncertain]` |
| Pulumi | General-purpose-language IaC across providers beyond SST's components | State in Pulumi Cloud or self-managed (S3/GCS) |
| AWS CDK v2 | AWS-only, wants CloudFormation drift detection and StackSets | CloudFormation lock-in; v1 is EOL |

Non-negotiables once adopted:

- **Remote state with locking** once more than one person or machine runs plan/apply (S3 + DynamoDB,
  S3-native locking on OpenTofu/Terraform 1.10+, HCP Terraform, Pulumi Cloud); local state is a sandbox
  only. **State carries plaintext secrets**: encrypt at rest, restrict the backend to the CI role plus a
  break-glass group, log access. Never commit `.tfstate`, `.tfstate.backup`, `.pulumi/`, `cdk.out/`.
- **Plan on PR, apply on merge**: `fmt -check`, `validate`, static analysis (tflint, checkov, trivy config),
  `plan` as a PR comment; apply from the merged plan artifact behind a GitHub Environment with a named
  reviewer; split read/write roles; scheduled drift plan that alerts on non-empty diffs; never mix
  click-ops and IaC on one resource. **Destroy/replace on stateful resources** needs explicit human
  confirmation, never a green plan.
- **OIDC from the first CI apply** for AWS/GCP/Azure: `permissions: id-token: write` on the job, not the
  workflow root; trust policy `sub` scoped to `repo:example-org/my-app:ref:refs/heads/main`, never `repo:org/*:*`.
- Pin providers, modules (`.terraform.lock.hcl`, `Pulumi.lock`), and Actions (SHAs). Do not wrap
  Cloudflare, Fly, Railway, Render, Vercel, or Supabase in community Terraform providers; native
  config gives the same review with less state. Atlantis / Spacelift / env0 past roughly 3-4 infra
  engineers.

## Cross-provider glue

**Secrets**: provider-native stores until 3+ providers each hold secrets and rotation falls behind, or an
audit needs one access log; then Doppler or Infisical; Vault only for dynamic/leased secrets. Never paste one
plaintext value into two stores. Keep one registry: secret, issuer, location, owner, last rotated. "Committed
then force-pushed away" is leaked; rotate.

**Telemetry**: services emit OTLP to one OpenTelemetry Collector (`localhost:4317` gRPC, `4318` HTTP);
only the Collector holds backend credentials and fans out to one primary backend, with a redaction
processor (drop `Authorization`, known PII) before any exporter. Cloudflare: Workers Logs, `wrangler tail`,
Logpush, Tail Workers (OTel export `[uncertain]`); Fly/Railway/Render/Netlify: dashboards and log drains,
no first-party OTel ingestion confirmed `[uncertain]`; Hetzner: nothing. Correlate with Sentry per `observability.md`.

**FinOps**: monthly review, one budget alert per provider (50/90/100 percent ladder, anomaly detection
where offered), one shared sheet; dedicated tooling or FOCUS exports only past 3+ billed providers or
spend where a spreadsheet misses anomalies (commonly cited $10k-50k/month `[uncertain]`). Egress traps:
AWS NAT Gateway per-GB processing plus transfer; GCP inter-region and internet egress; CDN overage
after a spike; Fly/Railway/Netlify per-GB bandwidth for CDN-shaped traffic; route large objects to R2
when egress is the cost driver. Free tiers reset and count per provider.

**Exit and lock-in**: R2's S3 API, OTLP, Dockerfiles, and Postgres are portable seams; D1, KV, DOs,
Netlify Functions, and CloudFormation are sticky. A second hyperscaler only for a capability gap (GPU,
data residency), never as a hedge.

## Limits and pricing

As-of 2026-08-29; `[uncertain]` = not readable from a primary page. CF = developers.cloudflare.com.

| Item | Value | Source |
|---|---|---|
| Workers | Free: 10 ms CPU/invocation; 100k req/day; 50 subrequests/req; 3 MB compressed script. Paid: $5/mo min; 10M req included then $0.30/M; 30M CPU-ms included then $0.02/M; CPU 30 s default, 5 min max; 10 MB script; 128 MB memory | CF /workers/platform/limits, /pricing |
| R2 | $0.015/GB-mo Standard, $0.01 Infrequent Access, 10 GB-mo free; Class A $4.50/M (IA $9.00), Class B $0.36/M (IA $0.90), free 1M A + 10M B/mo; egress $0 (Workers, S3 API, r2.dev) | CF /r2/pricing |
| D1 | 500 MB/db free, 10 GB/db paid; 10 dbs free, 50,000 paid; 2 MB row; 50 queries/invocation free, 1,000 paid; $0.001/M rows read, $1.00/M rows written `[uncertain]` (inferred from the DO SQLite billing note) | CF /d1/platform/limits |
| KV | 512 B key, 25 MiB value, 1 write/s/key; free 100k reads + 1k writes/day, 1 GB; paid unlimited | CF /kv/platform/limits |
| Durable Objects | 10 GB/object SQLite (5 GB account total free); ~1,000 req/s/object; free 100k req/day + 13,000 GB-s/day; paid 1M req + 400k GB-s/mo included, then $0.15/M req, $12.50/M GB-s; SQLite storage at D1 rates from 2026-01 | CF /durable-objects/platform/limits, /workers/platform/pricing |
| Queues | 128 KB message; 5,000 msg/s/queue; 25 GB backlog; 14-day retention paid, 24 h free; free 10k ops/day; paid 1M ops/mo then $0.40/M, metered per 64 KB | CF /queues/platform/limits, /workers/platform/pricing |
| Fly | shared-cpu-1x 256 MB ~$0.00000078/s (~$2.02/mo); performance-1x 2 GB ~$0.00001242/s (~$32.19/mo); Amsterdam, varies by region. Volumes $0.15/GB-mo; egress $0.02-0.12/GB by region group; FKS $75/mo base plus compute; no free allowance found `[uncertain]` | fly.io/docs/about/pricing |
| Railway | Free $0 + $1 credit; Hobby $5 + $5; Pro $20 + $20; post-paid card required, mid-cycle charges. RAM $10/GB-mo, CPU $20/vCPU-mo, egress $0.05/GB, volumes $0.15/GB-mo | docs.railway.com/reference/pricing |
| Render | Free web service suspends after 15 min idle, ~1 min cold start; free Postgres 1 GB, expires 30 days, 14-day grace, no backups. Paid Starter 0.5 CPU/512 MB up to Pro Ultra 8 CPU/32 GB (12 CPU/96 GB top); $/mo `[uncertain]` | render.com/docs/free, /docs/compute-plans |
| Netlify Functions | Billed in GB-hours, 10 credits per GB-hour; 1024 MB default, 4096 MB Pro/Enterprise; timeouts `[uncertain]` | docs.netlify.com/build/functions/usage-and-billing |
| Other | Hetzner entry VPS historically about EUR 4-5/mo shared vCPU with multi-TB included traffic `[uncertain]`. GitHub OIDC free with Actions; exchanged AWS STS session defaults to about 1 h `[uncertain]`. OpenTofu: over 3,900 providers and 23,600 modules. HCP Terraform / Pulumi Cloud: small-team free tiers exist, seat/resource limits `[uncertain]` | hetzner.com/cloud; docs.github.com OIDC hardening; opentofu.org; vendor sites |

## Cost guardrails

- Budget alerts share a channel with deploy success/failure; spending limits set before production.
- Workers: watch CPU-ms against the 30M/month included budget; "no request cap on paid" is not "no cost
  ceiling". Bound queue consumers; small messages multiply per-64 KB ops. R2 Class A costs roughly 12x
  Class B; use Infrequent Access for archives. DO duration billing under sustained WebSockets adds up.
- Fly is cheap only if machines stop; `min_machines_running >= 1` across many machines restores
  always-on cost, and a sleep-loop cron bills 24/7. Railway accrues past the credit with no hard cap.
- Any unauthenticated public endpoint on a usage-billed platform is a cost-based DoS surface: rate
  limit or front it with a CDN/WAF; serve media from object storage + CDN with signed URLs.
- IaC: Infracost on infra PRs; owner/environment tags; TTL-destroy preview environments. Check
  free-tier boundaries (100k Workers req/day, 100k KV reads/day, 10 D1 databases, Render 30-day
  Postgres) before assuming a side project stays free.

## CI gates

- Deploy jobs fail closed when the provider token or account id secret is missing; no interactive
  login fallback. `id-token: write` only on jobs that federate, never at root.
- Dry-run on PRs (`wrangler deploy --dry-run`, `flyctl deploy --build-only`, config schema checks);
  real deploy only from the merge-to-main job under a protected Environment after green tests, then a
  health smoke with retries (`deploy-ops.md`). Next.js-on-Workers runs the adapter compatibility checker.
- Config lint for real-looking ids, tokens, or connection strings in platform config files;
  gitleaks-class scan on every PR touching workflows or IaC.
- Production D1/R2/KV creation and Postgres migrations go through a reviewed step (`alembic upgrade --sql`
  dry run, or plan/apply). IaC adds destroy/replace grep on plan JSON and an apply timeout with a `force-unlock` runbook.
- Scheduled: token-age check that opens an issue past the rotation window; `otelcol validate --config`
  before a collector rollout; weekly cost diff against the prior baseline that fails loudly.

## Failure modes and anti-patterns

Failure modes not already implied by a rule above: KV write-then-read from another edge returns stale data
in prod only; one Durable Object key absorbs all traffic and overloads near 1,000 req/s; the D1 50-query cap
or Workers CPU limit truncates a batch that worked in dev; an unpinned `compatibility_date` changes behaviour
after a Wrangler upgrade; a Render free service used as a demo looks like an outage; a laptop apply bypasses
review; a bucket rename plans as a replace. Anti-patterns (each inverts a rule above): a single-region Fly
Machine called "edge"; video from PaaS compute; Terraform for a solo Vercel + Supabase app; `apply
-auto-approve` in a real environment; Vault on day one; five vendor SDKs instead of one Collector; assuming
"OIDC everywhere" and never documenting it.

## Agent codegen policy

- MUST NOT hardcode account ids, zone ids, database ids, bucket names, tokens, deploy hook URLs, or
  connection strings in platform config, IaC source, or workflow files; use placeholders (`<account-id>`,
  `my-app`) and `${{ secrets.NAME }}`. MUST NOT echo, print, or debug-log a secret.
- MUST route runtime secrets through `wrangler secret put`, `flyctl secrets set`, Railway sealed
  variables, or Render `sync: false`; MUST NOT write them under `[vars]`/`[env]`.
- MUST NOT claim Cloudflare, Fly, Railway, Render, or Netlify supports GitHub OIDC; for "OIDC like AWS"
  say it is unavailable and generate scoped token + GitHub Environment + rotation with the caveat in a
  comment. MUST use OIDC for AWS/GCP/Azure.
- MUST pin Actions to commit SHAs, set an explicit `compatibility_date`, generate parameterized D1
  queries only, and never commit `.tfstate`, Pulumi state, or `cdk.out/`. MUST configure locked remote
  state first, show `plan` before proposing `apply`, never auto-apply to a shared environment, and flag
  destroy/replace on stateful resources.
- SHOULD propose dashboards + committed config first and OpenTofu only when the adoption gates are met;
  default Cloudflare frontends to Workers + `[assets]` and DOs to SQLite; flag vinext's beta status; default
  Fly to scale-to-zero and say when to raise `min_machines_running`; recommend Fly Managed Postgres or
  Supabase, never unmanaged Fly Postgres; refuse a Netlify Function for long-running, stateful, or WebSocket
  work; point OTel snippets at the local Collector, not a vendor SDK with an API key; include at least one
  sub-100 percent threshold in any budget alert.

## Scan signals

| Signal (feeds engineer-scan / check-oss-leaks) | Meaning (hosts and ids are reconnaissance; tokens and state are hard failures) |
|---|---|
| Hostnames `*.workers.dev`, `*.pages.dev`, `*.fly.dev`, `*.up.railway.app`, `*.onrender.com`, `*.netlify.app`, `*.r2.cloudflarestorage.com`, `*.r2.dev` | Live platform surface; verify placeholder or intentionally public |
| 32-hex strings beside `account_id`, `zone_id`, `database_id`, `id =` in `wrangler.toml`/`.jsonc` | Real Cloudflare id in a template; replace with `<account-id>` |
| Token prefixes `fo1_` (Fly), `nfp_` (Netlify personal), `dop_v1_` (Doppler); literal values for `CLOUDFLARE_API_TOKEN`, `FLY_API_TOKEN`, `RAILWAY_TOKEN`, `RENDER_DEPLOY_HOOK_URL`, `NETLIFY_AUTH_TOKEN`; `api.render.com/deploy/srv-...?key=` | Committed credential; rotate, treat as leaked |
| Local auth or state dirs (kube config, docker config, the gcloud config folder, fly/wrangler/netlify/railway state files); `.tfstate`, `.tfstate.backup`, `.pulumi/`, `cdk.out/` in tree or history | Local auth or plaintext-secret state staged into the repo; purge history, migrate to remote state |
| `aws-access-key-id` / `aws-secret-access-key` or service-account JSON in a workflow; `id-token: write` at workflow root; trust policy `sub` wildcarded (`repo:org/*:*`) | Static cloud key where OIDC exists, or over-broad federation |
| Terraform provider block for Vercel, Fly, Railway, Render, Cloudflare Pages beside the native config file; `wrangler.toml` missing `compatibility_date`; `functions/` + `_worker.js` (legacy Pages); DO classes without `new_sqlite_classes` | Duplicate management, drift, or legacy patterns |
| Key-shaped values under `[vars]`/`[env]`; credential env vars in `render.yaml` without `sync: false` | Secret in plaintext config |
| `worker.py`/Celery entrypoint with no worker service; cron script with no `render.yaml` cron or Actions `schedule:` | Workload with no host defined |
| Several vendor observability SDKs and no Collector config; OTel config exporting raw headers | Credential sprawl; telemetry leak path |
| Static-token deploy job with no `environment:` key | Missing the compensating review gate |

## Ship checklist

```
Platform gate:
- [ ] Workload classified against the matrix; platform and reason recorded
- [ ] Postgres decision explicit (Supabase default); backup/HA owner named for any exception
- [ ] CI token: scoped machine token per environment, TTL where supported, in a GitHub Environment with required reviewers, inventoried; personal tokens absent
- [ ] AWS/GCP/Azure jobs use OIDC with a repo+branch-scoped sub; no static cloud keys
- [ ] No ids, tokens, or connection strings in wrangler/fly/render/railway/netlify config
- [ ] Runtime secrets via wrangler secret / flyctl secrets / sealed / sync: false only
- [ ] Actions and deploy CLIs pinned; dry-run on PR; deploy only from protected main job
- [ ] Cloudflare: Workers + [assets], pinned compatibility_date, observability on, DO SQLite, D1 parameterized, R2 private, Access paired with app authz
- [ ] Fly: auto_stop / min_machines_running matches workload; Managed Postgres if any
- [ ] Free tiers staging/demo only; spending limits and 50/90/100 alerts set per provider
- [ ] Media via object storage + CDN; public endpoints behind CDN/WAF; cron has a real trigger
- [ ] One OTel Collector with redaction; services emit OTLP; Sentry correlation wired
- [ ] IaC (if adopted): OpenTofu default, remote locked state, plan-on-PR, Environment-gated apply, drift schedule, lockfiles committed, no state in git history
- [ ] Secret registry current; 90-day rotation calendar; combined free-tier usage reviewed
```

## Sources

- Fetched 2026-08-29; WebSearch was unavailable that session, so only primary vendor docs. Cloudflare: developers.cloudflare.com/{workers,r2,d1,kv,durable-objects,queues}/platform limits and pricing,
  /pages, /workers/ci-cd (+ external-cicd/github-actions), /workers/wrangler, /cloudflare-one,
  /fundamentals/api/get-started/create-token, /workers/frameworks/framework-guides/nextjs
- Fly.io: fly.io/docs/about/pricing, /docs/postgres, /docs/reference/secrets,
  /docs/app-guides/continuous-deployment-with-github-actions. Railway: docs.railway.com/reference/pricing,
  /guides/variables. Render: render.com/pricing, /docs/{free,web-services,compute-plans,environment-variables,
  deploy-hooks}. Netlify: docs.netlify.com/functions/overview, /build/functions/usage-and-billing. Hetzner: hetzner.com/cloud
- IaC: opentofu.org, developer.hashicorp.com/terraform/language/state, sst.dev/docs, docs.github.com (configuring
  OIDC in AWS and GCP; about security hardening with OIDC). Glue: opentelemetry.io/docs/collector and
  /docs/specs/otel/protocol/exporter, finops.org/framework and /introduction/what-is-finops,
  developer.hashicorp.com/vault/docs/what-is-vault, infisical.com/docs
- Local: `research/cloud/results/{cloudflare-workers-pages-storage, paas-selection-fly-railway-render-netlify,
  iac-and-provisioning, multicloud-secrets-observability-cost}.json`; `research/cloud/outline.yaml`
