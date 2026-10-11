# Infrastructure security: cloud, network, containers, nodes

**Last verified**: 2026-07-16 · **Review cadence**: 3 months

Hardening **below the app layer**. Complements `backend-security.md` (headers/CSP/HTTP),
`ai-security.md` (LLM tools/MCP), `deploy-ops.md` (release mechanics), and
`git-signing-deploy.md` (deploy provenance). Delegate gstack `cso` before shipping
changes to auth, payment, or exposed-node surfaces.

## Scope and boundary

This module owns cloud accounts, tokens, networks, hosts, containers, and backups.
App-layer controls (CSP, headers, Server Actions, uploads) stay in `backend-security.md`;
RLS and identity stay in `backend-database.md` / `backend-auth.md`.

**Explicitly out of scope until the stack actually uses them**: Kubernetes-at-scale
(admission controllers, pod security standards, service mesh) and formal cloud-provider
organizational frameworks (AWS Organizations SCPs, GCP org policy). The current stack is
Vercel + Supabase + GitHub + OrbStack + hardened VPS/edge nodes; covering K8s or
hyperscaler org policy now would be speculative. Revisit when a real deployment adds them.

## Stack surface map

| Surface | What it is here | Highest-value control |
|---|---|---|
| Vercel | App deploys, env vars, tokens | Scoped tokens; env separation per tier |
| Supabase | DB, auth, storage, service keys | Service role server-side only; RLS stays on |
| GitHub org | Source, Actions, releases | Fine-grained/OIDC credentials; signed deploys |
| OrbStack (macOS) | Local/dev containers | Non-root, pinned digests, no socket mounts |
| RPC edge-node fleet (VPS) | Exposed RPC endpoints in front of customers | Keys-only SSH, default-deny inbound, rate limiting |

For an RPC edge-node fleet, node hardening is **directly load-bearing**: exposed RPC endpoints attract
scanning and abuse from day one, and a compromised edge node sits in front of customers.

## Cloud IAM least privilege

- **Scope every token to the job**: GitHub fine-grained PATs or GitHub App/OIDC per repo
  and permission; Vercel tokens scoped to the team/project; Supabase service keys per
  environment. No token that can touch everything.
- **No long-lived personal tokens in CI.** Prefer OIDC federation (GitHub Actions →
  cloud provider) so CI mints short-lived credentials; where a static secret is
  unavoidable, store it in the provider's secret store, scope it minimally, and rotate it.
- **Rotation is scheduled, not aspirational**: record owner + issue date + scope per
  credential; rotate on a calendar and immediately on personnel or incident events.
- **Separate human from machine identity**: deploys and automation run as service
  identities, never a founder's personal account. `backend-admin.md` owns break-glass.
- Org settings: 2FA required, signed-commit ruleset on protected branches
  (`git-signing-deploy.md`), Actions restricted to pinned immutable SHAs
  (`scan-doc-supply-chain.py` enforces this in-repo).

## Network exposure discipline

- **Default-deny inbound.** Open exactly the ports the service contract requires
  (443, and SSH from admin ranges where feasible); everything else closed at the
  firewall/cloud level, not in the app.
- **TLS everywhere** — public edges and node-to-node/origin links. No plaintext admin
  panels, metrics endpoints, or internal APIs "because it's internal".
- **No origin-server bypass of the edge/CDN**: if traffic is supposed to flow through
  Vercel/Cloudflare-class edges, the origin must reject direct connections (allowlist
  edge IPs or mutual TLS) — otherwise WAF, rate limits, and DDoS absorption are decorative.
- Rate limiting exists at this layer too: connection/abuse limits on exposed RPC and
  SSH, not only the app-level limits in `backend-api.md`.

## SSH and VPS/edge-node hardening

Baseline for every edge node and any VPS:

- **Keys only**: `PasswordAuthentication no`, `PermitRootLogin no`, per-operator keys
  (1Password SSH agent on workstations — never private-key files copied around).
- **fail2ban-class rate limiting** on SSH and exposed services.
- Unattended security updates on; kernel/reboot window scheduled. Alert on sustained
  auth-failure clusters instead of ignoring them.
- One service per exposure: the RPC process runs as a dedicated non-root user with
  systemd hardening (`ProtectSystem`, `NoNewPrivileges`, resource limits).
- Host firewall active even behind a cloud firewall; ship auth + firewall events to
  observability (`observability.md`).

## Container hardening

OrbStack-hosted (and any future runtime) containers:

- **Non-root images**: explicit `USER`; drop capabilities; read-only root filesystem
  where the workload allows.
- **Pinned digests**: `image@sha256:…`, not floating tags — same rule as the immutable
  GitHub Action pins already enforced in this repo.
- **Never mount the container socket** (`docker.sock`/OrbStack equivalent) into a
  workload; a socket mount is host root.
- **Resource limits** (CPU, memory, pids) on every long-running container so one workload
  cannot starve or wedge the host.
- Minimal base images; rebuild on base-image security updates rather than patching live.

## Secrets management

- **Environment separation**: local/preview/staging/production each get their own
  credentials; never point local at production (`deploy-ops.md` environment tiers).
- **Provider secret stores over `.env` files in production**: Vercel/Supabase/GitHub
  encrypted secret stores are the runtime source of truth; `.env` files are a local-dev
  convenience only.
- **No secrets in images, layers, logs, or repos.** The existing hard gates stay binding:
  gitleaks + push protection in CI (`enforcement-rules.md`), no-secrets-in-logs (SKILL.md
  hard gates), and the `backend-security.md` § Secrets and env client/server split. Build
  args and image layers are permanent — inject at runtime instead.
- Rotate on any suspected leak; "committed then force-pushed away" counts as leaked.

## Backup and DR security

- **Encrypted** at rest and in transit; backup credentials **access-separated** from
  production credentials so one compromised identity cannot destroy live data and backups.
- **Tested restore** on a schedule — a backup that has never been restored is a hope,
  not a control. Record last-restore-test date next to the backup job.
- Retention documented and privacy-aware: deletions required by `compliance-privacy.md`
  must propagate to backups within the documented window.

## Ship checklist

```
Infra gate:
- [ ] Every CI/automation credential: scoped, short-lived or store-managed, owner recorded
- [ ] Inbound default-deny verified on nodes (port scan from outside)
- [ ] SSH: keys-only, no root login, fail2ban-class limiter active
- [ ] Origin rejects edge-bypass traffic (direct-to-origin test fails)
- [ ] Containers: non-root, pinned digest, no socket mount, resource limits
- [ ] Production secrets in provider stores; no .env in prod images
- [ ] Backups encrypted, access-separated, restore tested with date recorded
```

## Anti-patterns

- Personal PAT with org-wide scope living in CI secrets "temporarily"
- SSH password auth or root login on an internet-facing node
- Origin reachable directly while the edge enforces the WAF
- `docker.sock` mounted into an app container for convenience; floating `latest` tags
- Backups writable/deletable by the production service identity
- Hardening the app's CSP while port 5432 is open to the world

## Related

- `backend-security.md` — app-layer headers, CSP, uploads, dependency security
- `deploy-ops.md` / `git-signing-deploy.md` — release tiers, verified deploy provenance
- `ai-security.md` — agent/MCP/skill credential and egress boundaries
- `agent-incident-response.md` — containment when a node or credential is compromised
- `compliance-controls.md` — mapping these controls to audit frameworks
