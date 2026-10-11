---
description: Auth and form pipeline — form UX, SSR sessions, middleware, RLS.
---

# /engineer-auth

Load engineer `SKILL.md` + `references/workflows.md` (Auth + form).

Auth feature follows this invocation.

## Pipeline

```
design-patterns (forms) → frontend → backend-auth → backend-database
```

## Hard gates

- Cookie SSR auth with middleware `getAll` + `setAll`
- Server Actions: `getUser()` + Zod
- Labels above fields, on-blur validation, errors below field
- RLS on user-owned rows

## Security

Before webhooks/OAuth production → gstack `/cso`

## Related

- Schema: `/engineer-schema`
- Audit: `/engineer-audit` on `app/api` and `actions`
