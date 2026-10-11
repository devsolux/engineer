---
description: GDPR engineering pipeline — export, delete account, consent, security review.
---

# /engineer-privacy

Load engineer `SKILL.md` + `references/workflows.md` (EU privacy).

Privacy requirements follow this invocation.

## Pipeline

```
compliance-privacy → backend-security → backend-testing
```

## Deliverables

- Data export Server Action (user-scoped, rate-limited)
- Delete account flow (Stripe cancel → storage → DB → auth.admin.deleteUser)
- Re-auth before destructive action
- Consent fields for marketing email
- **Not legal advice** — note legal review required

## Related modules

- Storage delete: `backend-storage.md`
- Billing cancel: `billing-stripe.md`

## Verify

Export cannot leak other users' data (RLS + getUser()).
