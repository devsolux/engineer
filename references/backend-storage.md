# Backend storage: Supabase files and uploads

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

File uploads, avatars, documents, and signed URLs via Supabase Storage.
Database RLS overview: `backend-database.md`. Auth: `backend-auth.md`.

## Contents
- [When to use Storage vs database](#when-to-use-storage-vs-database)
- [Bucket design](#bucket-design)
- [RLS on storage.objects](#rls-on-storageobjects)
- [Metadata table (recommended)](#metadata-table-recommended)
- [Upload flows](#upload-flows)
- [Download and signed URLs](#download-and-signed-urls)
- [Image transforms](#image-transforms)
- [Delete and GDPR](#delete-and-gdpr)
- [Testing](#testing)
- [Anti-patterns](#anti-patterns)
- [Composition](#composition)

## When to use Storage vs database

| Use Storage | Use Postgres |
|---|---|
| Images, PDFs, exports, media | Metadata, permissions, search |
| User avatars, attachments | File name, size, mime, owner_id |
| Large binary blobs | Relationships to other rows |

**Pattern**: metadata row in Postgres + object in Storage bucket. Never trust
client-provided paths alone.

## Bucket design

```
avatars/ public read, owner write - userId/filename
documents/ private - orgId/projectId/filename
exports/ private, short TTL signed URLs
```

Rules:
- One bucket per access pattern (public vs private vs org-scoped)
- Path convention: `{ownerId}/{resourceId}/{filename}` or `{orgId}/...`
- No user-controlled bucket names
- Max file size at bucket level + Zod validation server-side

```sql
-- Create bucket (migration or dashboard - prefer migration for reproducibility)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
 'avatars',
 'avatars',
 false,
 5242880,
 array['image/jpeg', 'image/png', 'image/webp']
);
```

## RLS on storage.objects

Storage uses `storage.objects` - **RLS required** like public tables.

### Private user folder

```sql
create policy "Users upload own avatar"
 on storage.objects for insert
 to authenticated
 with check (
 bucket_id = 'avatars'
 and (storage.foldername(name))[1] = (select auth.uid())::text
 );

create policy "Users read own avatar"
 on storage.objects for select
 to authenticated
 using (
 bucket_id = 'avatars'
 and (storage.foldername(name))[1] = (select auth.uid())::text
 );

create policy "Users delete own avatar"
 on storage.objects for delete
 to authenticated
 using (
 bucket_id = 'avatars'
 and (storage.foldername(name))[1] = (select auth.uid())::text
 );
```

### Org-scoped documents (via membership table)

```sql
create policy "Org members read documents"
 on storage.objects for select
 to authenticated
 using (
 bucket_id = 'documents'
 and exists (
 select 1 from public.org_members m
 where m.org_id = ((storage.foldername(name))[1])::uuid
 and m.user_id = (select auth.uid())
 )
 );
```

Checklist:
- [ ] RLS enabled on bucket (policies on `storage.objects`)
- [ ] INSERT `with check` matches SELECT `using` intent
- [ ] Path prefix cannot be spoofed (server generates path)
- [ ] `allowed_mime_types` on bucket + magic-byte check server-side for uploads

## Metadata table (recommended)

```sql
create table public.files (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users (id) on delete cascade,
 bucket text not null,
 path text not null,
 mime_type text not null,
 size_bytes bigint not null,
 created_at timestamptz not null default now(),
 unique (bucket, path)
);

alter table public.files enable row level security;
-- mirror owner policies on user_id
```

Benefits: list files in UI, audit trail, soft-delete, search - without listing
Storage API from client.

## Upload flows

### Server Action upload (preferred for auth control)

```
Client selects file
 → Server Action: getUser(), Zod (size, mime)
 → Generate path: `${userId}/${uuid}.${ext}`
 → supabase.storage.from(bucket).upload(path, file, { upsert: false })
 → Insert public.files row
 → Return signed URL or public URL
```

```typescript
"use server";
import { createClient } from "@/lib/supabase/server";
import { uploadSchema } from "./schema";

export async function uploadAvatar(formData: FormData) {
 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) throw new Error("Unauthorized");

 const file = formData.get("file");
 const parsed = uploadSchema.safeParse({ file });
 if (!parsed.success) return { error: parsed.error.flatten() };

 const ext = parsed.data.file.name.split(".").pop() ?? "bin";
 const path = `${user.id}/${crypto.randomUUID()}.${ext}`;

 const { error } = await supabase.storage
 .from("avatars")
 .upload(path, parsed.data.file, { contentType: parsed.data.file.type });

 if (error) return { error: error.message };

 await supabase.from("files").insert({
 user_id: user.id,
 bucket: "avatars",
 path,
 mime_type: parsed.data.file.type,
 size_bytes: parsed.data.file.size,
 });

 return { path };
}
```

### Signed upload URL (large files)

For files > few MB, use **signed upload URL** from server after auth:

```typescript
const { data, error } = await supabase.storage
 .from("documents")
 .createSignedUploadUrl(`${orgId}/${fileId}`);
// Client PUTs to signed URL; webhook or client callback confirms → insert metadata
```

Never expose service role to client for uploads.

## Download and signed URLs

| Bucket | Access |
|---|---|
| Public bucket | `getPublicUrl` - cache-friendly CDN |
| Private bucket | `createSignedUrl(path, expiresIn)` - server only |

```typescript
const { data } = await supabase.storage
 .from("documents")
 .createSignedUrl(path, 60 * 5); // 5 minutes
```

Rules:
- Short TTL for sensitive docs (5-15 min)
- Never embed long-lived signed URLs in HTML
- Regenerate on each request or use RSC to fetch fresh URL

## Image transforms

Use Supabase image transformation for thumbnails:

```
/storage/v1/render/image/public/avatars/{path}?width=200&height=200&resize=cover
```

Pair with `next/image` remotePatterns for allowed Storage host.

## Delete and GDPR

On account delete or file remove:
1. Delete `storage.objects` row (via API or cascade policy)
2. Delete `public.files` metadata
3. Log for compliance if required - see `compliance-privacy.md`

## Testing

See `backend-testing.md` for Storage RLS pgTAP patterns.

Manual matrix:
- User A cannot read User B's private path
- Unauthenticated cannot upload to private bucket
- MIME type rejected over limit
- Path traversal (`../`) rejected server-side

## Anti-patterns

| Don't | Do |
|---|---|
| Client picks storage path | Server generates path from auth context |
| Public bucket for private docs | Separate buckets by access model |
| Skip storage RLS | Policies on every bucket |
| Store files only in Storage | Metadata row for queries and ownership |
| Long-lived signed URLs in emails | Short TTL + auth gate on download page |
| Trust client MIME type | Bucket allowlist + server validation |
| Service role in browser upload | User-scoped client or signed URL |

## Composition

| Module | When |
|---|---|
| `backend-database.md` | Metadata table + RLS |
| `backend-api.md` | Server Action upload pipeline |
| `backend-security.md` | CSP for user content, virus scan if required |
| `compliance-privacy.md` | Export/delete file assets |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
