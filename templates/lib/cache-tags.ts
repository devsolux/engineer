/**
 * Central cache tag registry (copy to app lib/cache-tags.ts).
 * CODEOWNERS: assign this file to platform owners — tags must stay stable.
 *
 * Use with revalidateTag / updateTag (Server Actions only for updateTag).
 */
export const cacheTags = {
  user: (userId: string) => `user:${userId}`,
  org: (orgId: string) => `org:${orgId}`,
  project: (projectId: string) => `project:${projectId}`,
  billing: (orgId: string) => `billing:${orgId}`,
  /** Public marketing / pricing pages */
  pricing: () => "pricing",
  /** Knowledge base or docs tree (public or per-org) */
  content: (orgIdOrPublic: string) => `content:${orgIdOrPublic}`,
  /** RAG source document - invalidate on re-ingest */
  ragSource: (sourceId: string) => `rag:source:${sourceId}`,
  ragOrg: (orgId: string) => `rag:org:${orgId}`,
} as const;

export type CacheTag = ReturnType<(typeof cacheTags)[keyof typeof cacheTags]>;
