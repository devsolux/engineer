# SEO & metadata: technical discoverability

**Last verified**: 2026-07-14 · **Review cadence**: 3 months

Marketing copy: `conversion-ui.md` + `unmachined`. Performance: `frontend-performance.md`.
For crawler standards, AI/LLM discovery, `llms.txt`, content quality, IndexNow, and SEA, load
`web-discovery-engineering.md`; this file owns Next.js metadata implementation details.

## Contents
- [Metadata API](#metadata-api)
- [Open Graph and Twitter](#open-graph-and-twitter)
- [Sitemap and robots](#sitemap-and-robots)
- [JSON-LD structured data](#json-ld-structured-data)
- [Canonical URLs](#canonical-urls)
- [SEO + performance](#seo--performance)
- [AI search / answer engines](#ai-search--answer-engines)
- [Anti-patterns](#anti-patterns)

## Metadata API

```typescript
// app/layout.tsx or page.tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
 metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL!),
 title: {
 default: "Product - outcome in ≤60 chars",
 template: "%s | Product",
 },
 description: "Benefit-led description ≤155 characters for SERP snippet.",
 alternates: { canonical: "/" },
 robots: { index: true, follow: true },
};
```

Dynamic pages:

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
 const post = await getPost(params.slug);
 return {
 title: post.title,
 description: post.excerpt,
 alternates: { canonical: `/blog/${params.slug}` },
 };
}
```

Rules:
- One `<h1>` per page; logical heading hierarchy
- Unique title + description per route
- `lang` on `<html>`

## Open Graph and Twitter

```typescript
export const metadata: Metadata = {
 openGraph: {
 title: "...",
 description: "...",
 url: "https://example.com/page",
 siteName: "Product",
 images: [{ url: "/og.png", width: 1200, height: 630, alt: "..." }],
 locale: "en_US",
 type: "website",
 },
 twitter: {
 card: "summary_large_image",
 title: "...",
 description: "...",
 images: ["/og.png"],
 },
};
```

OG image: 1200×630, readable at thumbnail size, brand + outcome text.

## Sitemap and robots

```typescript
// app/sitemap.ts
import type { MetadataRoute } from "next";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
 const posts = await getPublishedPosts();
 return [
 { url: `${baseUrl}/`, lastModified: new Date(), changeFrequency: "weekly", priority: 1 },
 { url: `${baseUrl}/pricing`, lastModified: new Date(), priority: 0.8 },
 ...posts.map((p) => ({
 url: `${baseUrl}/blog/${p.slug}`,
 lastModified: p.updatedAt,
 changeFrequency: "monthly" as const,
 priority: 0.6,
 })),
 ];
}
```

```typescript
// app/robots.ts
export default function robots(): MetadataRoute.Robots {
 return {
 rules: { userAgent: "*", allow: "/", disallow: ["/app/", "/api/"] },
 sitemap: `${process.env.NEXT_PUBLIC_BASE_URL}/sitemap.xml`,
 };
}
```

## JSON-LD structured data

```tsx
// app/page.tsx - SoftwareApplication or Organization
<script
 type="application/ld+json"
 dangerouslySetInnerHTML={{
 __html: JSON.stringify({
 "@context": "https://schema.org",
 "@type": "SoftwareApplication",
 name: "Product",
 applicationCategory: "BusinessApplication",
 offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
 }),
 }}
/>
```

Sanitize if any user content in JSON-LD. Prefer static JSON for marketing pages.

## Canonical URLs

- Always set `alternates.canonical` on paginated/filter pages → base URL
- Avoid duplicate content: `/blog?page=2` canonical to `/blog` or self with params strategy
- HTTPS only in production (`metadataBase`)

## SEO + performance

CWV affects ranking - see `frontend-performance.md`:
- LCP hero optimized
- No carousel hero (LCP + CLS)
- Semantic HTML (`<main>`, `<article>`, `<nav>`)
- Internal links with descriptive anchor text

## AI search / answer engines

Traditional SEO still matters. Also optimize so assistants can **cite** you:

| Practice | Why |
|---|---|
| Clear H1 + first-paragraph answer | Models and featured snippets extract lead answers |
| FAQ + HowTo JSON-LD when accurate | Structured extraction |
| Public docs /blog as RSC HTML | Crawlable; not client-only paywall for key facts |
| Stable canonical URLs | Avoid duplicate fragments |
| `llms.txt` (optional) | Nonstandard community proposal - keep public, short, factual, measured, and removable |

```text
# public/llms.txt (optional sketch)
# Product: one-line job
# Docs: https://example.com/docs
# Pricing: https://example.com/pricing
```

Do not keyword-stuff for LLMs. Prefer accurate product facts over marketing fog (`unmachined`).
Do not block legitimate crawlers that you want citations from without product reason.
Do not claim `llms.txt` is a standard, ranking signal, crawler permission file, or replacement for
public crawlable pages. Separate search, training, user-fetch, and ads crawler policies.

## Anti-patterns

- Duplicate titles across pages
- Missing meta description (Google picks random text)
- Blocking `/app/` in robots but linking it publicly
- Keyword stuffing in headings
- Client-only rendered content for critical SEO text (keep key copy in RSC)
- Broken OG images (wrong dimensions, HTTP not HTTPS)
- Fake FAQ schema that does not match visible content

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
