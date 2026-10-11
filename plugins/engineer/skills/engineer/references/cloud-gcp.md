# Cloud GCP: identity, Cloud Run, data, network, cost

**Last verified**: 2026-08-29 · **Review cadence**: 3 months

**Related**: `deploy-ops.md` (release tiers, rollback), `infra-security.md` (tokens, network,
containers), `backend-security.md` (app-layer secrets split), `python.md` (service packaging),
`cloud-platforms-iac.md` (Terraform/OpenTofu conventions, multi-cloud glue).

## Contents
- [Scope and boundary](#scope-and-boundary)
- [Defaults](#defaults)
- [Decision gates](#decision-gates)
- [Identity](#identity)
- [Compute](#compute)
- [Data](#data)
- [Network and edge](#network-and-edge)
- [Limits and pricing](#limits-and-pricing)
- [Cost guardrails](#cost-guardrails)
- [Observability](#observability)
- [CI gates](#ci-gates)
- [Failure modes and anti-patterns](#failure-modes-and-anti-patterns)
- [Agent codegen policy](#agent-codegen-policy)
- [Scan signals](#scan-signals)
- [Ship checklist](#ship-checklist)
- [Sources](#sources)

## Scope and boundary
Owns the GCP layer for the default stack (TS/Next on Vercel, Python services, Supabase Postgres):
IAM and WIF, Cloud Run, GCS, Cloud SQL, AlloyDB, Firestore, Pub/Sub, Secret Manager, Tasks/Scheduler,
VPC and edge, budgets. Not owned: release ritual and rollback (`deploy-ops.md`); token scoping, SSH,
containers, backups (`infra-security.md`); Supabase RLS, Auth, Storage (`backend-database.md`,
`backend-auth.md`); Vercel OIDC federation (`cloud-vercel.md`); GKE, BigQuery, Vertex AI; Cloud Run
Worker Pools and Instances (preview as of 2026-08-29). GCP is opt-in: Supabase stays the primary
relational store and Vercel the public HTTP edge; GCP enters for Cloud Run-hosted Python services,
GCP residency or integration, or a gate below.

## Defaults
- Hierarchy: one org, folders per environment, one project per environment per product line
  (`my-project-prod`); a flat MVP project needs a migration plan.
- Identity: zero SA JSON keys; CI uses WIF via `google-github-actions/auth`, local dev uses
  `gcloud auth application-default login` or short-lived impersonation; org policies
  `iam.disableServiceAccountKeyCreation` and `iam.disableServiceAccountKeyUpload` enforced at the org
  node; one least-privilege SA per deploy target per environment; never `roles/owner` or `roles/editor`
  on a CI-facing principal.
- Compute: Dockerfile containers on Cloud Run services, batch/ETL as jobs, single-purpose event
  handlers as functions; `--no-allow-unauthenticated`, explicit `--min-instances` and
  `--max-instances`, starting concurrency 40 with a load-test note, a runtime SA per service,
  secrets only as Secret Manager references (`--set-secrets`, `secret_key_ref`).
- Data: Supabase Postgres and Storage first. GCS only when the workload lives in GCP: regional,
  uniform bucket-level access (UBLA), public access prevention (PAP) enforced, lifecycle rule.
  Cloud SQL over AlloyDB: Postgres 16 or 17, private IP, `ssl_mode = ENCRYPTED_ONLY`, backups plus
  PITR. Pub/Sub push with dead-letter topics; Cloud Tasks for one deferred call; Scheduler for cron.
- Network and cost: Vercel serves public HTTP; Direct VPC egress to private resources (Google's
  recommended default as of 2026-08-29), connector only as a documented fallback; Cloud Armor
  default-deny plus rate limit on any GCP LB; one region for Cloud Run, DB, NAT, and connectors;
  Billing Budget per project (50/90/100 percent, Pub/Sub action) before any always-on network
  resource goes live.

## Decision gates

| Question | Pick |
|---|---|
| Standard CRUD, RLS tied to Supabase Auth, no GCP residency need | Supabase Postgres (default) |
| DB must sit in a private GCP VPC, PSC integration, or GCP-scoped compliance boundary | Cloud SQL for Postgres |
| HTAP on live data, read pools, vector search beside Vertex pipelines | AlloyDB |
| Document-shaped reads, offline-first sync, Firestore listener SDKs; no joins or multi-row transactions | Firestore (narrow; never a second source of truth) |
| Objects consumed by GCP compute, or tiering materially cuts cost | GCS; otherwise Supabase Storage |
| Fan-out to multiple GCP consumers with durable retry; one deferred HTTP call with per-task schedule, rate limit, dedup | Pub/Sub; Cloud Tasks |
| Single event-triggered handler; multi-route API or framework | Cloud Run functions; Cloud Run service |
| Run-to-completion work (imports, ETL, media) | Cloud Run job, not a service with a fake HTTP trigger |
| User-facing and latency-sensitive; background threads or keep-alives | `min-instances >= 1` (budget the idle cost); CPU always allocated (changes billing) |
| Cloud Run needs Cloud SQL/AlloyDB/Memorystore by private IP | Direct VPC egress; connector only if unsupported for the region/product or scale-from-zero latency is critical |
| Private-only workload needs outbound internet | Cloud NAT on the egress subnet |
| Custom WAF, multi-region anycast, or Armor DDoS features Vercel lacks | External HTTPS LB, serverless NEG, Cloud Armor |
| Public traffic for the Next.js app and API routes | Vercel edge and Firewall; no GCP LB |
| Target API accepts federated principals | Direct WIF (`principalSet` bound to roles) |
| Target needs a classic SA identity (many Terraform providers; Firebase Admin SDK has no WIF support as of 2026-08-29: isolate it in its own project with a scoped SA, any key in Secret Manager) | WIF plus SA impersonation |
| Deploy originates from Vercel; Terraform apply identity | Vercel's own OIDC federation; separate infra project, pool, and provider |

## Identity
A pool provider trusting `https://token.actions.githubusercontent.com` validates GitHub's OIDC JWT
and, only if the attribute condition is true, lets STS mint a Google token; the principal holds
roles directly (Direct WIF) or impersonates one SA via `roles/iam.workloadIdentityUser`.
- Every provider has a non-empty attribute condition (an empty or loose one is the most common WIF
  misconfiguration and is exploitable immediately), keyed on numeric `assertion.repository_id` and
  `assertion.repository_owner_id`, never on renameable `repository` or `repository_owner` strings.
- One provider per trust boundary with per-repo conditions, not one per repo (200 per pool).
- Production bindings carry an IAM Condition limiting to the release branch and excluding PR
  contexts; `id-token: write` only on trusted triggers, never blanket on `pull_request_target` (a
  missing `id-token: write` is the most common setup failure). Data Access audit logs on for
  `iam.googleapis.com` and `sts.googleapis.com`; alert on any key create or upload in the org.
- Research disagrees on action majors (`auth@v3` plus `setup-gcloud@v2` versus `auth@v2` plus
  `deploy-cloudrun@v2`): verify the current major in the README, then pin an immutable SHA.

```bash
PROJECT_ID="my-project"; POOL_ID="github-actions"; PROVIDER_ID="my-repo-provider"
PROJECT_NUMBER="123456789012"   # placeholder; read with gcloud projects describe
gcloud iam workload-identity-pools create "$POOL_ID" --project="$PROJECT_ID" --location=global
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --project="$PROJECT_ID" --location=global --workload-identity-pool="$POOL_ID" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_owner_id=='00000000' && assertion.repository_id=='000000000'"
# Direct WIF: add-iam-policy-binding --role=roles/run.developer --member=principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository_id/000000000
# Impersonation variant: grant roles/iam.workloadIdentityUser on the SA to that same member.
# Org node, once: gcloud resource-manager org-policies enable-enforce iam.disableServiceAccountKeyCreation --organization=<org-id> (and ...KeyUpload)
# Workflow: permissions: { id-token: write }; google-github-actions/auth@<pinned-sha> with workload_identity_provider:
#   projects/123456789012/locations/global/workloadIdentityPools/github-actions/providers/my-repo-provider (service_account: <name>@<project>.iam.gserviceaccount.com only for impersonation)
```

## Compute
- Packaging: Dockerfile, non-root `USER`, pinned base image (`python:3.12-slim`, `node:22-slim`),
  SHA or digest tag, never `:latest`. Source/buildpack deploys backdate file mtimes to 1980-01-01
  (breaks mtime cache busting): prototypes only. Cloud Run functions, never legacy 1st-gen Functions.
- Concurrency: run gunicorn/uvicorn with workers (a sync dev server at the default 80 queues and
  times out), or drop toward 1 for CPU-bound code; raise above 80 only after a load test. CPU is
  request-based by default and throttled near zero between requests, so background threads
  silently stall; always-allocated CPU bills continuously, and warm instances bill continuously.
- Scaling: a default `max-instances` cap applies even when unset (value [uncertain]); set it against
  Supabase connection or pooler limits. Jobs retry 3 by default.
- Shutdown and identity: handle SIGTERM and drain (grace about 10 s, configurable); local disk is
  ephemeral. Dedicated per-service SA, never the Compute Engine default SA; `roles/run.invoker`
  bound to caller SAs; `allUsers` only for a genuinely public endpoint. Manage config as
  `google_cloud_run_v2_service`; console edits only for emergency rollback.

## Data
- GCS: `uniform_bucket_level_access = true`, `public_access_prevention = "enforced"`, versioning,
  lifecycle rule (Standard to Nearline at 30 days, delete at 365); IAM per SA; `allUsers` is an incident.
- Cloud SQL: `ipv4_enabled = false`, private network, `ssl_mode = "ENCRYPTED_ONLY"` or client cert,
  `REGIONAL` in prod, backups with PITR, `deletion_protection = true`; built-in pooling or
  PgBouncer plus a `max-instances` cap, since serverless callers exhaust `max_connections`; local
  access via Cloud SQL Auth Proxy. AlloyDB only for HTAP, read pools, or co-located vector search.
- Firestore: Native mode only (Datastore mode is legacy); default-deny rules tested on the emulator
  in CI; documents over 1 MiB go to GCS with a reference.
- Pub/Sub and Tasks: at-least-once, so handlers are idempotent; every production subscription has
  an ack deadline, retry policy, and `dead_letter_policy`; ordering and exactly-once are opt-in;
  IAM per topic and subscription. Tasks and Scheduler call Cloud Run over OIDC auth with
  `--no-allow-unauthenticated`; queue rate limits protect third parties; App Engine targets are legacy.
- Secret Manager: `roles/secretmanager.secretAccessor` per secret per consuming SA; reference
  `projects/<project>/secrets/<name>/versions/latest` or a pinned version; rotation needs a redeploy;
  `user_managed` replication when residency matters; cross-cloud access through WIF, never a key file.

## Network and edge
- Direct VPC egress: dedicated subnet /26 or larger; IP reservation grows during rollouts;
  scale-from-zero can add a minute or more before the first VPC connection; `PRIVATE_RANGES_ONLY`
  unless Cloud NAT must carry all egress. Connector: size at 2 to 3; it never scales in.
- VPC firewall: default-deny ingress; Direct VPC egress and connector traffic still traverse VPC
  firewall rules, so `0.0.0.0/0` ingress exposes Cloud SQL private IPs. Cloud NAT only for private
  workloads needing outbound internet; port exhaustion looks like app bugs, so enable NAT logging.
- HTTPS LB plus Cloud Armor: global external Application LB (no new Classic ALBs) with a serverless
  NEG to Cloud Run. Policy: lowest-priority `deny(403)` default, at least one `rate_based_ban` rule,
  OWASP preconfigured rules (CRS 4.22 as of 2026-08-29) enabled per category since they are off by
  default. Standard tier covers L3/L4 DDoS only; Enterprise adds L7. Cloud CDN only for GCP-origin static content.

## Limits and pricing

All values as of 2026-08-29; [uncertain] figures were not confirmed live and need re-verification.

| Item | Value | Source |
|---|---|---|
| WIF providers per pool; SA keys per SA; logic operators per condition; pools per project; WIF pricing; access token lifetime; GitHub OIDC token lifetime | 200; 10 (policy keeps it 0); 12; not published; not separately billed [uncertain]; 1 h default, 12 h max via org policy; 5 min | iam/quotas; iam/docs/workload-identity-federation; github.com/google-github-actions/auth |
| Conditional bindings per allow policy; folder depth; children per folder | ~100 recommended (not a hard quota); 10 levels; 300 | iam/docs/conditions-overview; resource-manager/docs/creating-managing-folders |
| Cloud Run concurrency; CPU target; idle retention; cold-start queue; request timeout; instance shape | 80; adaptive tuning under ~90 percent; 15 min (10 GPU); max(3.5x startup, 10 s); 300 s default, 60 min max; up to 8 vCPU / 32 GiB [uncertain; quotas page 404] | run/docs/configuring/concurrency; run/docs/about-instance-autoscaling; run/docs/quotas |
| Cloud Run env vars; jobs | 1000 per service, 32 KB each; 10,000 tasks, 10 min default and 168 h max timeout (GPU 1 h), retries 0 to 10 | run/docs/configuring/services/environment-variables; run/docs/create-jobs |
| Cloud Run pricing; free tier | ~$0.000024/vCPU-s, ~$0.0000025/GiB-s, ~$0.40/M requests; ~2M requests, ~360k GiB-s, ~180k vCPU-s per month [uncertain] | run/pricing |
| GCS object size; bucket rate; storage price (US) | 5 TiB; ~1,000 writes/s and ~5,000 reads/s initial, 1 write/s per object; ~$0.020 Standard, $0.010 Nearline, $0.004 Coldline, $0.0012 Archive per GB-month [uncertain] | storage/quotas; storage/pricing |
| Cloud SQL storage; process ceiling; Enterprise compute | 64 TB dedicated, 3 TB shared; connections + workers <= 262,142; ~$0.04/vCPU-h, ~$0.007/GB-h [uncertain] | sql/docs/postgres/quotas; sql/pricing |
| Firestore document; free tier; Pub/Sub message; retention | 1 MiB; 50k reads / 20k writes / 20k deletes per day, 1 GiB; 10 MB; 7 d default, ~31 d max [uncertain] | firestore/docs; pubsub/docs/overview |
| Secret Manager limits; price | 64 KiB per version; 90,000 access/min/project; 600 read and 600 write ops/min; ~$0.06 per active version-location-month, ~$0.03 per 10k accesses [uncertain] | secret-manager/quotas; secret-manager/docs/overview |
| Cloud Scheduler; Cloud Tasks HTTP deadline | 3 free jobs per project-month then ~$0.10 per job-month [uncertain]; 10 min default, 30 min max | scheduler/docs; tasks/docs/dual-overview |
| Direct VPC egress; VPC connector | 1 Gbps per instance then throttled, /26 minimum, 2x instance IP reservation; min 2 (floor and default), max 10 default, never scales in | run/docs/configuring/vpc-direct-vpc; vpc/docs/serverless-vpc-access |
| Egress: internet (Premium); inter-region; cross-zone; Cloud NAT; Cloud CDN; Cloud Armor | lowest band ~$0.12/GB; ~$0.01 to 0.05/GB; ~$0.01/GB, same-zone free; ~$0.044 to 0.045 per VM-hour plus ~$0.045/GB; cache egress ~$0.02 to 0.08/GB plus cache-fill; ~$5 per policy-month, ~$1 per rule-month, ~$0.75/M requests, Enterprise ~$200 per project-month [uncertain] | vpc/network-pricing; vpc/pricing; cdn/pricing; armor/pricing |
| Always-free egress; billing budgets | Cloud Run 1 GB/mo, Cloud Run functions 5 GB/mo, GCS 100 GB/mo (North America origin only); 50,000 budgets per billing account, default thresholds 50/90/100 percent | free/docs/free-cloud-features; billing/docs/how-to/budgets |

## Cost guardrails
- Budget first: `google_billing_budget` per project, 50/90/100 percent actual plus 100 percent
  forecasted, with an `all_updates_rule` Pub/Sub topic (email-only is weak; delivery can lag hours),
  in the same change as any NAT, connector, or LB. Never wire disable-billing to a budget on shared
  or production projects; designated sandboxes only, at 150 to 200 percent, with an SA scoped to one call.
- Cap `max-instances` everywhere; `min-instances > 0` only on production user-facing services;
  preview and staging scale to zero; prefer request-based CPU. Lifecycle rule on every non-archive
  GCS bucket (unbounded growth is the most common silent GCP cost leak); regional over
  multi-region; right-size Cloud SQL from monitoring; skip AlloyDB unless its features are used.
- Egress traps: media or exports served straight from Cloud Run pay premium internet egress that
  can exceed compute; route through Vercel or Cloud CDN. A Cloud Run and Cloud SQL region mismatch
  bills inter-region per request. Connector floor of 2 bills at zero traffic; a shared NAT needs
  its own budget line. Free-tier egress is demo-scale. Armor charges per rule; prefer preconfigured groups.

## Observability
- Audit: Data Access logs for IAM and STS; Admin Activity plus Data Access for GCS, Cloud SQL, Secret
  Manager, Pub/Sub; central sink. Alert on `SetIamPolicy` touching WIF pools, providers, or CI SAs;
  any key create/upload; any new `allUsers` binding.
- Signals: Cloud Run instance count, p50/p95/p99 latency, CPU/memory per revision, cold-start
  frequency, 429/503 against `max-instances` saturation, billable instance time versus requests,
  structured JSON logs with trace ids, Cloud Trace on; Cloud SQL connections versus
  `max_connections` and replica lag; Pub/Sub oldest unacked age and dead-letter count; Tasks queue
  depth; GCS egress bytes; Secret Manager access from unexpected SAs; VPC Flow Logs and NAT logs;
  Armor per-rule counts; egress by category; connector utilization; CDN cache-hit ratio; weekly
  billing export to BigQuery; provider count versus the 200-per-pool quota; unused SAs.

## CI gates
- Secret scanning rejects JSON with `"type": "service_account"` and `"private_key"`; workflow lint
  fails on `GOOGLE_APPLICATION_CREDENTIALS` set to a path, on `google-github-actions/auth` without
  `permissions: id-token: write`, and on any `GCP_SA_KEY`-style secret.
- Policy-as-code (OPA/Conftest) on the plan fails: WIF provider without `attribute_condition`;
  `roles/owner`, `roles/editor`, or `*.admin` to a `serviceAccount:` or `principalSet://`; bucket
  without UBLA and PAP; Cloud SQL `ipv4_enabled = true` without a reviewed exception; Cloud Run
  service without `max_instance_count`; invoker `allUsers` without override; firewall ingress from
  `0.0.0.0/0`; Armor policy without default-deny or rate limit; NAT without a budget in the
  project; production subscription without `dead_letter_policy`.
- Container: SHA or digest reference only; Artifact Registry scan blocks critical CVEs; lockfiles
  scanned. Human review on `.github/workflows/**`, WIF/IAM Terraform, and diffs touching firewall,
  Armor, connector, NAT, or `vpc_access`; `min-instances > 0` and concurrency above 80 need
  written justification and a staging load test. Scheduled: weekly SA key list across projects
  (alert on any key); org-policy enforcement check; drift `terraform plan` on network resources;
  Infracost-class estimate on PRs adding NAT, LB, or connector; Firestore rules and idempotency tests.

## Failure modes and anti-patterns
- Identity: any fork or renamed repo minting tokens through a loose condition; `roles/editor`
  granted "temporarily"; one `ci-everything` SA; a key-based fallback for a library.
- Compute: concurrency 80 on a sync single-threaded Python service; a spike exhausting Supabase
  connections; SIGTERM ignored (partial writes); secrets in `--set-env-vars` visible in revision
  metadata and CI logs; an internal service relying on an unguessable URL.
- Data: an accidental `allUsers` bucket binding (the most common GCP data incident); Cloud SQL with
  public IP and open authorized networks; a poison message hidden without a dead-letter topic; a
  second Postgres splitting the source of truth.
- Network and cost: `0.0.0.0/0` VPC ingress after adding Direct VPC egress; Armor with WAF rules but
  no default-deny; NAT port exhaustion; a GCP edge stack duplicating Vercel; budget with no Pub/Sub
  action, discovered on the invoice; real ids or hostnames hardcoded in code or IaC.

## Agent codegen policy
MUST: apply every rule in Defaults and Identity; pin `google-github-actions/auth` to an immutable
SHA with explicit `permissions: id-token: write` and `workload_identity_provider`; emit a non-empty
`attribute_condition` keyed on numeric ids on every WIF provider; default to least-privilege
predefined roles and flag broad requests for review; emit a SIGTERM handler for every service and
a Cloud Run job for run-to-completion work; emit a lifecycle rule for log, export, or drop-zone
buckets; emit idempotent Pub/Sub and Tasks handlers with `dead_letter_policy`; emit a Billing
Budget with Pub/Sub in the same change as any NAT, connector, or LB; default relational code to
Supabase unless a gate is named; use placeholders only (`my-project`, `my-app`, `<region>`,
`123456789012`, `example.com`); flag, never silently fix, any encountered key-shaped JSON or
`GOOGLE_APPLICATION_CREDENTIALS` file reference.

MUST NOT: generate any file containing `"type": "service_account"`, `"private_key"`, or
`"client_email"`, even as a fixture; emit `gcloud iam service-accounts keys create` or
`GOOGLE_APPLICATION_CREDENTIALS` set to a path in CI config, Dockerfiles, or `.env` templates; emit
`roles/owner` or `roles/editor` for any automation principal; emit `--allow-unauthenticated`
unless the user states the endpoint is public; write secret literals in `--set-env-vars`,
Dockerfile `ENV`, Terraform `env` blocks, or `.env` defaults; emit `:latest` tags in production,
`ipv4_enabled = true` without acknowledged risk, `0.0.0.0/0` ingress, or an allow-by-default Armor
policy; scaffold Firestore as a relational substitute or second source of truth; stand up a GCP
edge stack for traffic Vercel already serves; wire disable-billing to a budget outside a sandbox.

## Scan signals

- Critical: JSON with `"type": "service_account"` plus `"private_key"`; `google_service_account_key`
  resource; `gcloud iam service-accounts keys create` in scripts or workflows;
  `GOOGLE_APPLICATION_CREDENTIALS` assigned a literal path; `allUsers` or `allAuthenticatedUsers`
  on a bucket or `roles/run.invoker`; `run.googleapis.com/invoker-iam-disabled: 'true'`;
  `--allow-unauthenticated` on a service not marked public; Cloud SQL `ipv4_enabled = true` with
  empty or `0.0.0.0/0` authorized networks; `google_compute_firewall` ingress from `0.0.0.0/0`.
- High: `google-github-actions/auth` without `id-token: write`; a `GCP_SA_KEY`-style secret; WIF
  provider without `attribute_condition`; conditions on `assertion.repository` or
  `assertion.repository_owner` without the numeric `_id` claims; `roles/owner`, `roles/editor`,
  `roles/iam.securityAdmin`, or `*.admin` to a `serviceAccount:` or `principalSet://`;
  `serviceAccountTokenCreator` or `workloadIdentityUser` at project level; secret-like keys (SECRET,
  TOKEN, PASSWORD, KEY, CREDENTIAL) in `--set-env-vars` or Terraform `env { value }`; plaintext
  secrets in manifests or `.env`; Cloud SQL without `ssl_mode`; bucket without UBLA or PAP.
- Medium: Cloud Run service without `max_instance_count`, or user-facing without `min-instances`;
  `--concurrency=1` beside an async framework; mutable image tags in production; no non-root
  `USER`; no SIGTERM handling; batch-shaped logic in a service; Armor policy without a
  lowest-priority deny or rate limit; NAT without a budget; connector `max_instances` far above
  `min_instances`; `vpc_access` egress `ALL_TRAFFIC` where `PRIVATE_RANGES_ONLY` suffices; budget
  without `all_updates_rule`; GCP LB duplicating Vercel for one hostname; subscription without
  `dead_letter_policy`; drop-zone bucket without a lifecycle rule.
- Hygiene: a non-placeholder 10 to 13 digit number beside `projects/`; hostnames other than
  `example.com` or IANA-reserved domains in docs; absolute home-directory paths.

## Ship checklist
```
GCP gate:
- [ ] Decision gate cited for every GCP service provisioned beyond Cloud Run
- [ ] Org policies disableServiceAccountKeyCreation/Upload enforced; one least-privilege SA per deploy target per environment; no owner/editor
- [ ] WIF condition non-empty with numeric ids; prod binding limited to the release branch and non-PR events; id-token: write set; no key-shaped JSON or credentials path
- [ ] Cloud Run: non-root Dockerfile, SHA-tagged image, min/max instances set, concurrency load-tested, CPU allocation deliberate, SIGTERM handled, invoker scoped
- [ ] Secrets via Secret Manager with per-secret accessor bindings; none in env vars
- [ ] GCS: UBLA, public access prevention, lifecycle rule; Cloud SQL: private IP, TLS, backups plus PITR, pooler; Pub/Sub: DLQ, ack deadline, idempotent handlers
- [ ] Direct VPC egress on a dedicated /26; no 0.0.0.0/0 ingress; Armor default-deny plus rate limit on any public LB; all resources in one region
- [ ] Budget with Pub/Sub action live before any NAT, connector, or LB; audit logs central; scaling, saturation, cost alerts wired; smoke per deploy-ops.md
```

## Sources

Primary (docs.cloud.google.com unless noted): iam/docs/{workload-identity-federation, workload-identity-federation-with-deployment-pipelines, service-account-overview,
best-practices-service-accounts, conditions-overview}, iam/quotas, resource-manager/docs/creating-managing-folders, github.com/google-github-actions/auth,
run/docs/{about-instance-autoscaling, create-jobs, securing/managing-access, deploying-source-code, overview/what-is-cloud-run}, run/docs/configuring/{min-instances,
concurrency, services/environment-variables, vpc-direct-vpc}, run/docs/quotas (404 during research), run/pricing, functions/docs/concepts/overview, storage/{docs/introduction,
lifecycle, pricing, quotas}, sql/docs/postgres/{introduction, quotas}, sql/pricing, alloydb/docs/overview, firestore/docs, pubsub/docs/overview, secret-manager/{docs/overview,
quotas}, tasks/docs/dual-overview, scheduler/docs, load-balancing/docs/load-balancing-overview, cdn/{docs/overview, pricing}, armor/docs/cloud-armor-overview, armor/pricing,
vpc/docs/serverless-vpc-access, vpc/{network-pricing, pricing}, billing/docs/how-to/{budgets, notify}, free/docs/free-cloud-features. Corpus:
`research/cloud/results/gcp-*.json` (review by 2026-11-29).
