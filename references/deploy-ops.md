# Deploy & operations: Vercel, envs, releases

**Last verified**: 2026-07-14 · **Review cadence**: 3 months

Compose with gstack `/ship` for PR/release ritual and `/canary` for post-deploy watch.
See `enforcement.md` for CI; `workflows.md` for ship loop always-ask on prod.

## Contents
- [Environment tiers](#environment-tiers)
- [Verified deployment source](#verified-deployment-source)
- [Vercel deploy](#vercel-deploy)
- [Database migrations on deploy](#database-migrations-on-deploy)
- [Preview vs production](#preview-vs-production)
- [Rust service deploy](#rust-service-deploy)
- [Rollback](#rollback)
- [Post-deploy verification](#post-deploy-verification)
- [Anti-patterns](#anti-patterns)

## Environment tiers

| Tier | Purpose | Data |
|---|---|---|
| **local** | Dev | Supabase local / branch |
| **preview** | PR review | Supabase branch or staging project |
| **staging** | Pre-prod QA | Anonymized or seed data |
| **production** | Live users | Real data |

Never point local `.env.local` at production Supabase.

## Verified deployment source

For protected production paths, require GitHub-verified signed commits on the release branch and deploy an immutable SHA. Re-check GitHub's verification result for that exact SHA before deployment; a locally valid signature is insufficient. See `git-signing-deploy.md` and `templates/github/verified-deploy-gate.yml`.

## Vercel deploy

Standard Next.js on Vercel:

```
main push → production deploy
PR → preview deploy (unique URL)
```

Env vars in Vercel dashboard per environment:
- Production: live Stripe keys, prod Supabase
- Preview: test Stripe keys, staging Supabase branch
- Never share service role across environments without intent

```bash
# Local parity
vercel env pull .env.local
```

Build settings:
- Node 24 LTS (Node 20 is end-of-life)
- `npm run build` must pass locally first
- Enable Vercel Analytics / Speed Insights for CWV

## Database migrations on deploy

**Order matters:**

```
1. Apply migrations (supabase db push / CI migration job)
2. Deploy app code that expects new schema
3. Regenerate types if schema changed
```

Options:
- **Supabase CLI in CI** - `supabase db push` on merge to main
- **Manual review** - human applies migration before deploy for breaking changes
- **Expand-contract** - add column → deploy code → remove old column (zero-downtime)

Never deploy code requiring new columns before migration runs.

## Preview vs production

Preview deploys:
- Use Supabase **branch** or isolated staging project
- Stripe **test mode** keys only
- Disable or sandbox outbound email
- Don't use production webhook endpoints (Stripe CLI for local)

Protect preview URLs if sensitive: Vercel authentication or IP allowlist.

## Rust service deploy

If hybrid stack (`system-architecture.md`):

| Target | Pattern |
|---|---|
| Fly.io / Railway | Docker + health checks |
| Kubernetes | Deployment + HPA + `/health/ready` |
| Same VPC as Postgres | Private network for DB |

Docker essentials:
- Non-root user
- Multi-stage build
- `RUST_LOG` env
- Graceful shutdown (SIGTERM)

Env: `DATABASE_URL`, JWT secret for auth from Next gateway.

## Rollback

Vercel: **instant rollback** to previous deployment in dashboard.

If migration was applied:
- App rollback alone may be insufficient
- Prefer forward-fix migration over down migrations in prod
- Test rollback path in staging

## Post-deploy verification

```
Post-deploy smoke (5-15 min):
- [ ] Homepage loads; LCP acceptable
- [ ] Login / signup works
- [ ] Critical API/Action path works (activation path if product change)
- [ ] Stripe webhook endpoint healthy (signed test or dashboard deliveries)
- [ ] Security headers present (securityheaders.com)
- [ ] No spike in Sentry errors / new issue cluster (observability.md)
- [ ] Health endpoints if any: /api/health or service /health/ready
- [ ] gstack /canary against production URL when available
- [ ] gstack /qa optional for visual/regression on critical flows
```

### Canary composition

| Step | Owner |
|---|---|
| Preflight scan + CI green | engineer-ship / loop-ship |
| Merge + deploy | gstack ship / land-and-deploy / Vercel |
| Watch errors, 5xx, basic journeys | gstack canary + Sentry |
| Rollback | Vercel previous deployment; forward-fix migrations |

Always-ask before production deploy (`workflows.md` risk table). On red canary: roll back first, then diagnose - do not "fix forward" on money paths.

## Anti-patterns

- Prod secrets in preview env
- Deploy Friday without rollback plan
- Migration + code deploy as single unreviewed step
- Skipping smoke test after deploy
- Force push to main to fix deploy
- Running prod migrations from laptop without backup
- Treating green build as green product (no smoke)

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
