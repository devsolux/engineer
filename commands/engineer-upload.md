---
description: File upload pipeline — Supabase Storage, RLS, Server Actions, pgTAP tests.
---

# /engineer-upload

Load engineer `SKILL.md` + `references/workflows.md` (File upload).

Upload feature follows this invocation.

## Pipeline

```
backend-storage → backend-api → backend-database → backend-testing
```

## Hard gates

- Server generates storage path from `userId` — not client
- Storage RLS on `storage.objects` (folder prefix)
- Optional `public.files` metadata row
- Zod: size + MIME validation
- `getUser()` on upload Server Action
- Short TTL signed URLs for private reads

## Verify

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
supabase test db  # storage RLS tests when configured
bash "$ENGINEER/scripts/engineer-scan.sh" --backend --strict
```
