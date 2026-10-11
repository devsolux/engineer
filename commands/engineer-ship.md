---
description: Production pre-flight — deploy-ops, security headers, enforcement gates, observability.
---

# /engineer-ship

Load engineer `SKILL.md`. Pipeline: **deploy-ops → backend-security → enforcement → observability**.

## Checklist

- [ ] Env tiers documented (`.env.example` complete)
- [ ] Migrations applied **before** app deploy order
- [ ] CSP / security headers configured
- [ ] `engineer-scan --strict` passes
- [ ] RLS migration gate passes
- [ ] Sentry or error tracking configured
- [ ] Post-deploy smoke steps listed
- [ ] No secrets in client bundle

## Verify

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
npm run typecheck
npm run lint:ci
bash "$ENGINEER/scripts/engineer-scan.sh" --strict
```

## Compose

Run **gstack `/ship`** for final deploy checklist when user is ready to deploy.

## Loop

Until all gates pass: `/engineer-loop-ship`
