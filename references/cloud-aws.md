# Cloud: AWS for a Next + Python + Supabase stack

**Last verified**: 2026-08-29 · **Review cadence**: 3 months

**Related**: `deploy-ops.md` (release tiers, rollback, smoke), `infra-security.md` (IAM least privilege,
network default-deny, container hardening), `backend-security.md` (app-layer secrets split), `python.md`
(service packaging), `background-jobs.md` (queue/worker patterns), `cloud-platforms-iac.md` (IaC, FinOps).

Opinionated greenfield defaults, not a catalog. Limits and prices carry an as-of date and a primary URL;
`[uncertain]` marks unconfirmed items. Placeholders only: `123456789012`, `my-app`, `example-org`, `example.com`.

## Contents
- [Scope and boundary](#scope-and-boundary)
- [Defaults](#defaults)
- [Decision gates](#decision-gates)
- [Identity](#identity)
- [Compute](#compute)
- [Data](#data)
- [Edge and network](#edge-and-network)
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

Owns AWS-specific choices: service selection, CI and workload identity, compute/data/network configuration,
and cost. AWS enters **only when an AWS resource is actually needed** (S3, Lambda, SES, a VPC-bound service).

| Concern | Owner |
|---|---|
| Release ritual, env tiers, rollback, post-deploy smoke | `deploy-ops.md` |
| Generic IAM/token hygiene, SSH, containers, backups | `infra-security.md` |
| Postgres, Auth, Storage, RLS, Edge Functions for the app itself | `backend-supabase.md` / `backend-database.md` |
| Next.js hosting, Vercel functions, Vercel-to-AWS OIDC | `cloud-vercel.md` |
| Terraform/CDK mechanics, multi-provider secrets, OTel | `cloud-platforms-iac.md` |

## Defaults

- **Identity**: one IAM OIDC provider per account for GitHub Actions; one role per repo + environment;
  humans via IAM Identity Center; zero IAM user access keys, root included.
- **Compute**: Lambda (ARM64) for spiky, event-driven work under 15 min; ECS Fargate for steady or
  long-running Python workers; App Runner for the fastest container-to-HTTPS path without custom VPC.
- **Relational data**: Supabase Postgres. RDS/Aurora only for a stated VPC-only, Aurora-feature, or
  data-residency requirement; then Aurora Serverless v2 (variable load) or Graviton `db.r7g`/`db.t4g`.
- **Objects**: Supabase Storage for user-facing assets; S3 for large, AWS-native, or archival objects.
  Every bucket: Block Public Access, versioning, SSE, lifecycle rule.
- **Secrets**: Secrets Manager when rotation is needed; SSM Parameter Store SecureString (free tier) otherwise.
- **Async**: SQS Standard + DLQ for work queues; EventBridge for routed and scheduled events.
- **Edge/network**: API Gateway HTTP API before Lambda; ALB before Fargate; CloudFront + OAC over
  public S3 content; two-AZ VPC, private subnets, VPC Endpoints instead of NAT.
- **Cost**: `aws_budgets_budget` + Cost Anomaly Detection in the first IaC apply.

## Decision gates

**When AWS, when not**: 100% Supabase + Vercel means skip AWS entirely, including IAM. A function that only
talks to Supabase Postgres/Auth/Storage is a Supabase Edge Function, not Lambda. Code colocated with the Next
app (API routes, server actions) stays on Vercel functions unless a VPC-only resource, an AWS-specific SDK, or
a long job forces AWS; for AWS reads from Vercel, evaluate Vercel's built-in OIDC-to-AWS role first (`cloud-vercel.md`).

**Supabase vs RDS/Aurora**: stay on Supabase unless the service must run in a private VPC with no public hop,
you need Aurora-only features (Serverless v2 instant scaling, cross-region replicas, I/O-Optimized), or a
contract makes AWS the data-residency boundary. Never run both for one logical dataset without a documented
source of truth. DynamoDB only for single-digit-ms key lookups at high volume; joins or ad-hoc filters mean Postgres.

| Pick (Lambda vs Fargate vs App Runner) | When |
|---|---|
| Lambda | Spiky or low-volume traffic, SQS/EventBridge/S3 consumers, cron under 15 min, cost should idle near zero. Escalate when cold starts are user-visible and provisioned concurrency cost nears a small always-on task |
| Fargate | Persistent process (WebSocket, warm DB pool, in-memory cache), runs over 15 min, steady load where per-request billing loses, more than 10 GB memory, sidecars. Spot for interruption-tolerant workers only, never request-serving without a non-Spot baseline |
| App Runner | Small internal API or admin tool from an image or repo, no custom VPC topology, single container |

## Identity

- **CI**: GitHub Actions OIDC JWT to `AssumeRoleWithWebIdentity`. Trust `sub` pinned to
  `repo:example-org/my-app:environment:production` (Environment with required reviewers), never `repo:example-org/*`.
  `MaxSessionDuration` 1h. `configure-aws-credentials` v6 line pinned to an exact tag or SHA with `permissions:
  id-token: write` + `contents: read`; v1 to v3 lack immutable-subject-claim protections, so do not pin new
  setups to v4. First workflow step: `aws sts get-caller-identity`.
- **Workloads**: Lambda execution role, ECS execution role **plus a separate** task role, App Runner
  instance role. The SDK chain finds them; never inject `AWS_ACCESS_KEY_ID`.
- **Humans**: IAM Identity Center permission sets (ReadOnly for most, scoped Admin for a small break-glass
  group), MFA enforced, `aws sso login` for CLI; preferred even solo.
- **Backstops**: permission boundary on every CI role; SCP blocking access-key creation once Organizations exists;
  Access Analyzer and a CloudTrail org trail from day one; never co-locate `iam:PassRole` with create actions unscoped.
- Repos created after 2026-07-15 emit subject claims embedding org/repo ids; name-based trust still works
  but review it for new repos `[uncertain: migration timeline]` (as of 2026-08-29).

Skeleton (placeholders only; provider created once per account; inline policy is explicit actions on ARNs):
```hcl
data "aws_iam_policy_document" "gha_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals { type = "Federated", identifiers = [aws_iam_openid_connect_provider.github.arn] }
    condition { test = "StringEquals", variable = "token.actions.githubusercontent.com:aud", values = ["sts.amazonaws.com"] }
    condition { test = "StringEquals", variable = "token.actions.githubusercontent.com:sub", values = ["repo:example-org/my-app:environment:production"] }
  }
}
resource "aws_iam_role" "gha_deploy_prod" {
  name                 = "my-app-gha-deploy-production"
  assume_role_policy   = data.aws_iam_policy_document.gha_trust.json
  max_session_duration = 3600
  permissions_boundary = aws_iam_policy.ci_boundary.arn
}
```

## Compute

**Lambda (Node/Python)**
- Runtimes: Node.js 22.x and Python 3.13 as of 2026-08-29 `[uncertain: exact latest minor]`; check the live
  deprecation schedule before pinning. ARM64 unless a native wheel forces x86.
- Memory via AWS Lambda Power Tuning (memory also scales CPU and network; 128 MB usually costs more in
  duration than it saves). Timeout below the API Gateway ceiling.
- Cold starts: trim dependencies (esbuild for Node; `uv`/pip `--platform` for Python), init SDK clients and
  pools at module scope, provisioned concurrency only for a measured problem, reviewed monthly.
- Zip by default; container image only past zip/layer limits, a custom runtime, or heavy native deps (then Fargate).
- Any Lambda-to-RDS/Aurora path at real concurrency goes through RDS Proxy or a pooler.
- Managed Instances and Durable Functions `[uncertain: maturity]`: not greenfield defaults.

**ECS Fargate**: `awsvpc` mode, private subnets, security groups scoped to source groups; distinct
`executionRoleArn` (pull image, logs) and `taskRoleArn` (app code); explicit CPU/memory, health check,
`stopTimeout` + SIGTERM handling, Service Auto Scaling (no scale-to-zero); private ECR, scan-on-push, pinned digests.

**App Runner**: `apprunner.yaml` for source builds; secrets via Secrets Manager ARN references; auto-deploy on push is a production path, gate it with branch protection; memory bills while provisioned even when idle.

## Data

**S3**: account-level Block Public Access first (`aws s3control put-public-access-block`); versioning for anything
you cannot regenerate; SSE-S3 by default (SSE-KMS CMK only for key-usage audit); lifecycle to IA/Glacier after a
defined window; presigned URLs scoped to one key and method, expiry in minutes (skeleton 300 s); public content
via CloudFront + OAC, never a public bucket.

**RDS/Aurora when justified**: `PubliclyAccessible: false`, private subnets, IAM DB auth where the driver
supports it, else Secrets Manager rotation (AWS rotation Lambda templates, 30-day rule), RDS Proxy for Lambda.

**DynamoDB**: On-Demand until traffic is characterized; PITR on; a capacity raise does not fix a hot
partition key. Standard-IA class for cold tables.

**Secrets Manager vs Parameter Store**: rotation or cross-account/region replication means Secrets Manager
(per-secret fee); static config means Parameter Store SecureString, never plain `String`, Supabase keys included.

**SQS / EventBridge**: every consumed queue has a DLQ with tuned `maxReceiveCount`; Standard unless ordering or
exactly-once is a real requirement (FIFO costs more, caps throughput). EventBridge for fan-out, routing, Scheduler cron; narrow rules.

## Edge and network

- **API Gateway vs ALB**: HTTP API for Lambda (throttling, JWT authorizer, proxy integration). REST API only
  for usage plans/API keys, request transformation, or private endpoints. ALB for Fargate/EC2, WebSockets
  beyond API Gateway's model, host/path routing across services. Never stack both without a stated reason.
- **CloudFront**: OAC (SigV4) to a private S3 origin, bucket policy scoped to the one distribution; explicit
  cache behaviors per path so authenticated responses are never cached cross-user; WAF managed Core rule
  set + rate-based rule on one layer (CloudFront or ALB, not both); Shield Standard is automatic.
- **VPC**: two AZs, public + private subnets, Fargate and RDS private. Verify with VPC Reachability Analyzer
  that private subnets have no `0.0.0.0/0` route to an IGW. Cross-AZ and cross-region transfer is billed.
- **NAT gateway trap**: S3/DynamoDB via free Gateway Endpoints, Secrets Manager/ECR/SSM via Interface Endpoints;
  NAT only for unavoidable public egress, one per AZ (not per subnet), alarmed on data-processing GB, which dominates real bills.

## Limits and pricing

All values as of 2026-08-29. Re-verify against the live page before quoting to anyone.

| Item | Value | Source |
|---|---|---|
| IAM role session; OIDC provider; Identity Center | 15 min to 12 h `MaxSessionDuration` (1 h for CI); max 5 thumbprints, 100 audiences, 100 RSA + 100 EC JWKS keys; Identity Center has no charge | IAM OIDC provider guide; singlesignon docs |
| Lambda quotas | 128 MB to 10,240 MB (1,769 MB is about 1 vCPU); 900 s timeout; /tmp 512 MB to 10,240 MB; 50 MB zipped, 250 MB unzipped incl. layers, 10 GB image, 5 layers; env 4 KB aggregate; 1,000 concurrent per region (soft) | lambda gettingstarted-limits |
| Lambda price (x86) | $0.0000166667/GB-s + $0.20/1M requests; 400k GB-s + 1M req/month free `[uncertain under 2025-07 Free Tier]` | lambda/pricing |
| Fargate (us-east-1, x86) | $0.0404/vCPU-h, $0.00444/GB-h; ARM about 20% less; Spot up to 70% off | fargate/pricing |
| App Runner | $0.064/vCPU-h active, $0.007/GB-h provisioned; per-second, 1 min minimum | apprunner/pricing |
| Aurora | Standard $0.10/GB-month + $0.20/1M I/O; I/O-Optimized $0.225/GB-month; Serverless v2 about 2 GiB per ACU, 0.5 ACU steps, per-ACU-hour price `[uncertain]` | rds/aurora/pricing |
| DynamoDB | on-demand $0.125/1M RRU, $0.625/1M WRU `[uncertain: from summarized fetch]`; provisioned $0.00013/RCU-h, $0.00065/WCU-h; $0.25 (Standard) / $0.10 (IA) per GB-month; 25 RCU + 25 WCU + 25 GB free `[uncertain post 2025-07]` | dynamodb/pricing |
| Secrets Manager; Parameter Store | $0.40/secret/month + $0.05/10k calls; Parameter Store Standard free, 10,000 params, 4 KB each, Advanced price `[uncertain]` | secrets-manager/pricing; systems-manager advanced parameters |
| SQS; EventBridge | SQS 1M requests/month free, per-million rate `[uncertain: about $0.40 Standard / $0.50 FIFO historically]`; EventBridge $1.00/1M custom events, Pipes $0.40/1M, Scheduler 14M invocations/month free | sqs/pricing; eventbridge/pricing |
| NAT Gateway; Gateway Endpoint | $0.045/h + $0.045/GB processed; Gateway Endpoints (S3, DynamoDB) free | vpc/pricing |
| ALB (us-east-1) | $0.0225/h + $0.008/LCU-h | elasticloadbalancing/pricing |
| API Gateway | HTTP $1.00/1M (first 300M), REST $3.50/1M (first 333M); WebSocket $1.00/1M msgs + $0.25/1M conn-min; $0.09/GB out | api-gateway/pricing |
| CloudFront | PAYG: 1 TB/month + 10M requests free, then $0.085/GB (US), $0.0100 per 10k HTTPS req; flat-rate: $0/month (1M req, 100 GB) up to $1,000/month, no overage `[uncertain: tier detail, rollout]` | cloudfront/pricing (+ pay-as-you-go) |
| Free Tier (new accounts) | since 2025-07-15: up to $200 credit over 6 months; account closes at 6 months or when credit is spent; about 30 "always free" services `[uncertain: which per-service allowances survive]` | aws.amazon.com/free |

**Free Tier, honestly**: accounts created after 2025-07-15 do not get the legacy 12-month per-service
allowances tutorials describe (750 RDS hours, 5 GB S3, 1M Lambda requests); their fate is `[uncertain]` and the
API Gateway page still advertises one, a disagreement this module does not resolve. Plan on the $200/6-month runway.

## Cost guardrails

- Budgets (cost and usage) at 50/80/100% routed to a monitored channel, plus Cost Anomaly Detection, in the
  first apply; per-service budgets as each service enters use.
- Cost-allocation tags (project/environment) on every resource from day one; Infracost-style estimates on
  plans flagging new NAT Gateways, oversized ALBs, unbounded API usage.
- Scope CloudTrail data events deliberately ("log everything" bills per event); denial-of-wallet is a
  threat, so WAF rate rules and CloudFront caching protect the bill.

Top three bill surprises in practitioner reports: NAT Gateway data processing a VPC Endpoint would have made free
(most common); capacity that never scales down (provisioned concurrency, peak-sized Fargate, idle App Runner memory,
DynamoDB floors, provisioned Aurora where Serverless v2 fit); the free-tier cliff (old 12-month framing burning the
$200 credit in weeks) plus REST API chosen by habit.

## Observability

Compose with `observability.md`; AWS-specific signals:
- CloudTrail org trail (multi-region) retained beyond 90 days. Alert on `AssumeRoleWithWebIdentity` from an
  unexpected repo/environment claim, any access-key creation, any root sign-in, any policy change widening
  a CI role. Access Analyzer findings to a channel; unused access older than 90 days.
- Lambda: errors, throttles, duration near timeout, `Init Duration` trend. ECS/App Runner: restart count,
  unhealthy targets. Structured JSON logs; X-Ray or OTel (AWS Distro). Data: SQS DLQ count above 0,
  oldest-message age, DynamoDB throttles, RDS connections near `max_connections`, rotation failures, S3 4xx/5xx.
- Network: VPC Flow Logs, CloudFront/API Gateway/ALB access logs with retention, NAT data-processing GB
  trend, WAF blocked-request spikes. Cost Explorer by tag, weekly.

## CI gates

- `terraform plan`/`cdk diff` with human approval for any IAM, OIDC provider, or compute-role change;
  production applies only from a protected GitHub Environment.
- Policy scanning (checkov/tfsec/Access Analyzer validation) failing on: wildcard action/resource on CI
  roles, `sub` without repo scope, `aws_iam_user`, S3 Block Public Access disabled, `publicly_accessible =
  true` on RDS, `Principal: "*"` on SQS/SNS/S3 without a condition, security group `0.0.0.0/0` on a non-web
  port, CloudFront S3 origin without OAC, missing `aws_budgets_budget` in a new environment stack.
- Secret scanning (gitleaks/trufflehog) on `AKIA`/`ASIA` keys and connection-string literals
  (`enforcement-rules.md` binds this); Lambda zip well under 50 MB; ECR scan gate on critical/high CVEs.
- Staging deploy + synthetic invoke or health-check smoke before production; scheduled `terraform plan` drift
  detection on data-layer resources; migration review gate for the primary Postgres store, separate from app deploy.

## Failure modes and anti-patterns

Failure modes seen in audits: wildcard or missing `sub` condition letting any fork PR assume a production role;
`AdministratorAccess` on CI "temporarily", then permanent; static keys "until OIDC is set up", never removed (the
most common real finding); `iam:PassRole` + create on one role; Lambda burst exhausting Postgres connections
without RDS Proxy; Lambda timeout at or above the API Gateway ceiling (29 s REST) producing 504s; Fargate
crash-loop on a bad health check or port binding; deploys dropping requests for lack of `stopTimeout`; presigned
URLs with day-long expiry or bucket-wide scope; a "CloudFront-fronted" bucket still public; CloudFront default TTL
caching a per-user response; poison messages with no DLQ; silent rotation failure; hot partition throttling; unread budget alerts.

Anti-patterns (do not generate): `aws-access-key-id` inputs to `configure-aws-credentials`; `aws_iam_user` for
workloads; `"Action": "*"` or `"Resource": "*"` on a deploy role "to unblock the build"; same role ARN for ECS
execution and task; plaintext secrets in `Environment.Variables`; `Timeout: 900` with `MemorySize: 128`; DB pool
opened inside the handler body; RDS provisioned "by default" while Supabase already holds the data; FIFO by reflex;
NAT Gateway per subnet, or any NAT without a VPC Endpoint check; REST API by habit; `FROM python:latest` in production.

## Agent codegen policy

Must:
- Authenticate CI with `role-to-assume` + `permissions: id-token: write`; scope the trust `sub` to
  `repo:org/name:environment:<env>` or `repo:org/name:ref:refs/heads/<branch>`.
- Emit explicit actions on explicit ARNs; attach a permission boundary to CI roles.
- Resolve secrets through Secrets Manager/Parameter Store references; separate ECS execution and task
  roles; include health check, `stopTimeout`, and a stated memory/timeout rationale in every compute definition.
- Default relational storage to Supabase; presigned URLs with short explicit expiry and one key/action; DLQ on
  every consumed SQS queue; PITR and versioning on durable stores; public Lambda APIs on HTTP API; CloudFront-to-S3
  through OAC; VPC Endpoints before NAT; scoped security groups; `aws_budgets_budget` in every environment stack.
- Flag rather than silently fix: `iam:PassRole` + create combinations, a NAT Gateway request, or parallel
  Supabase + RDS for one dataset. These are human decisions.

Must not: generate `aws_iam_user`, `AWS::IAM::User`, or static keys in any variable, `.env`, Dockerfile, task
definition, or Lambda env block; leave Lambda defaults unexamined; reuse one role across many functions/services;
pull production images from public unpinned tags; cache authenticated responses at the edge; ship a Lambda
timeout at or above the API Gateway ceiling without flagging it.

## Scan signals

What `check-oss-leaks.sh` (and `engineer-scan`) flags in this domain:

| Flag | Pattern |
|---|---|
| Access keys | `AKIA[0-9A-Z]{16}`, `ASIA[0-9A-Z]{16}`, `aws_secret_access_key` literals |
| Real ARNs | `arn:aws:...:<12-digit account>:` where the account id is not the docs sample `123456789012` |
| Private hosts | `<acct>.dkr.ecr.<region>.amazonaws.com`, `*.rds.*.amazonaws.com`, `*.execute-api.*.amazonaws.com`, `*.elb.*`, `<bucket>.s3.<region>.amazonaws.com`, `s3://<bucket>`, `<hash>.cloudfront.net` |
| Local credential paths | the aws credentials folder under the home directory (and its ssh, kube, gcloud equivalents) referenced from repo code or docs |
| Connection strings | `postgres://user:pass@...`, `mysql://...` in source, env files, or IaC defaults |
| IaC posture | `aws_iam_user`, `"Action": "*"`/`"Resource": "*"` on CI roles, bare `repo:org/*` trust, `publicly_accessible = true`, `Principal: "*"` without condition, `0.0.0.0/0` on database ports, `aws_nat_gateway` with no `aws_vpc_endpoint`, no `aws_budgets_budget` |

Neutral placeholders the gate accepts: `123456789012`, `my-app`, `example`, `example-org`, `<project>`.
Positive signals (not flags): `id-token: write` with `role-to-assume`; distinct execution/task roles;
`redrive_policy`; Block Public Access block; `aws_vpc_endpoint` next to private route tables; scoped OAC bucket policy.

## Ship checklist

```
AWS gate:
- [ ] No AWS resource in the plan that Supabase or Vercel already covers (documented rationale per service)
- [ ] OIDC provider once per account; each CI role scoped to repo + environment, boundary attached, 1h session
- [ ] Zero IAM user access keys (root included); humans via Identity Center with MFA
- [ ] Compute choice justified; memory/timeout tuned; ARM64 unless blocked; execution and task roles distinct
- [ ] No plaintext secret in any env block, image, or IaC default; Secrets Manager/Parameter Store references only
- [ ] RDS Proxy or pooler on every Lambda-to-Postgres path; RDS not publicly accessible
- [ ] Every S3 bucket: Block Public Access, versioning, SSE, lifecycle; presigned URLs short and single-key; SQS DLQs; DynamoDB PITR
- [ ] HTTP API unless a REST-only feature is named; CloudFront origins via OAC; WAF baseline on public entry points
- [ ] No NAT Gateway without a VPC Endpoint check; security groups scoped; private subnets verified
- [ ] Budgets + Cost Anomaly Detection + cost tags applied before the first workload; alert channel is monitored
- [ ] CloudTrail org trail, Access Analyzer, Flow Logs, access logs shipped with retention; cost plan on the 2025-07-15 credit model
```

## Sources

- Identity (primary, as of 2026-08-29): https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html · https://github.com/aws-actions/configure-aws-credentials · https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/ · https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html
- Quotas and tiers: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html · https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-advanced-parameters.html · https://aws.amazon.com/free/
- Pricing: https://aws.amazon.com/lambda/pricing/ · https://aws.amazon.com/fargate/pricing/ · https://aws.amazon.com/apprunner/pricing/ · https://aws.amazon.com/rds/aurora/pricing/ · https://aws.amazon.com/dynamodb/pricing/ · https://aws.amazon.com/secrets-manager/pricing/ · https://aws.amazon.com/sqs/pricing/ · https://aws.amazon.com/eventbridge/pricing/ · https://aws.amazon.com/vpc/pricing/ · https://aws.amazon.com/elasticloadbalancing/pricing/ · https://aws.amazon.com/api-gateway/pricing/ · https://aws.amazon.com/cloudfront/pricing/ · https://aws.amazon.com/cloudfront/pricing/pay-as-you-go/
- Research corpus: `research/cloud/results/aws-*.json` (identity/compute confidence high, data/edge medium); load on demand.
