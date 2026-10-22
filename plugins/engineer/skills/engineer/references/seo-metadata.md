# SEO & metadata: technical discoverability

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

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
 default: "Product - outcome, key words first", // no Google length limit; truncated by width
 template: "%s | Product", // applies to child segments only
 },
 description: "Benefit-led, page-specific summary (~155 chars: display heuristic, not a limit).",
 alternates: { canonical: "/" },
 robots: { index: true, follow: true },
};
```

Dynamic pages:

```typescript
type Props = { params: Promise<{ slug: string }> }; // or PageProps<"/blog/[slug]">

export async function generateMetadata({ params }: Props): Promise<Metadata> {
 const { slug } = await params; // Next 16 removed synchronous params access
 const post = await getPost(slug);
 return {
 title: post.title,
 description: post.excerpt,
 alternates: { canonical: `/blog/${slug}` },
 };
}
```

Rules:
- One `<h1>` per page; logical heading hierarchy (structure and accessibility; Google says heading
 order does not matter for Search)
- Unique title + description per route
- `lang` on `<html>` for accessibility; Google detects language from visible content, so declare
 variants with `alternates.languages` (hreflang)
- `metadata`/`generateMetadata` are Server Component exports, never both in one segment. Since
 15.2 dynamic `generateMetadata` can stream into `<body>`; HTML-limited bots (`htmlLimitedBots`,
 e.g. `facebookexternalhit`) still get blocking `<head>` tags. Prefer static `metadata`.

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

OG image: 1200×630, readable at thumbnail size, brand + outcome text. Meta recommends at least
1200×630 near 1.91:1, ≤8 MB; X's large card uses 2:1, <5 MB, no SVG. Set `twitter.card`
explicitly: X falls back to `og:title`/`og:description`/`og:image`, but may then render only a
summary card. Prefer `opengraph-image`/`twitter-image` files (`.png`/`.jpg`, or `.tsx` returning
`ImageResponse` from `next/og` with `size`, `alt`, `contentType` exports); files override config,
and in Next 16 their `params` is a Promise.

## Sitemap and robots

```typescript
// app/sitemap.ts - Google ignores priority/changeFrequency; lastModified = real content change
import type { MetadataRoute } from "next";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
 const posts = await getPublishedPosts();
 return [
 { url: `${baseUrl}/`, lastModified: homeUpdatedAt }, // never new Date() on every request
 { url: `${baseUrl}/pricing`, lastModified: pricingUpdatedAt },
 ...posts.map((p) => ({
 url: `${baseUrl}/blog/${p.slug}`,
 lastModified: p.updatedAt,
 })),
 ];
}
```

Absolute canonical URLs only. Split above 50,000 URLs or 50 MB uncompressed with nested
`sitemap.ts` files or `generateSitemaps` (Next 16 passes `id` as `Promise<string>`).
`sitemap.ts` and `robots.ts` are cached Route Handlers unless they use request-time APIs.

```typescript
// app/robots.ts
import type { MetadataRoute } from "next";

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
 }).replace(/</g, "\\u003c"), // JSON.stringify alone is XSS-unsafe
 }}
/>
```

Always escape `<` as Next's JSON-LD guide shows; never trust user content. Prefer static JSON for
marketing pages. Mark up only visible, true content. Google's Software app rich result also needs a
real `aggregateRating` or `review`, and no markup guarantees a rich result. Validate with the Rich
Results Test and the Schema Markup Validator.

## Canonical URLs

- Self-canonicalize indexable pages with `alternates.canonical`; `metadataBase` makes it absolute
- Paginated `/blog?page=2` canonicalizes to itself, never to `/blog` (Google: do not use page 1 as
 canonical; it also no longer uses `rel=prev/next`)
- Filter/sort variants: robots.txt-disallow or `noindex` when they need no Search presence, else
 canonical to the unfiltered URL (Google calls canonical weaker long-term for crawl control)
- HTTPS only in production (`metadataBase`)

## SEO + performance

Google's ranking systems use Core Web Vitals (one signal, no ranking guarantee) - see
`frontend-performance.md`:
- LCP hero optimized
- No carousel hero (LCP + CLS)
- Semantic HTML (`<main>`, `<article>`, `<nav>`)
- Internal links with descriptive anchor text

## AI search / answer engines

Traditional SEO still matters. Also optimize so assistants can **cite** you:

| Practice | Why |
|---|---|
| Clear H1 + first-paragraph answer | Models and featured snippets extract lead answers |
| FAQPage/HowTo JSON-LD only if visible | Extraction; Google retired HowTo (2023) and FAQ (2026) rich results |
| Public docs /blog as RSC HTML | Crawlable; not client-only paywall for key facts |
| Stable canonical URLs | Avoid duplicate fragments |
| `llms.txt` (optional) | Nonstandard community proposal - keep public, short, factual, measured, and removable |

Optional `public/llms.txt` sketch (one H1, then H2 link lists; full rules in
`web-discovery-engineering.md`):

```markdown
# Product
> One-line job.

## Docs
- [Docs](https://example.com/docs): Setup and API reference.
- [Pricing](https://example.com/pricing): Current plans and limits.
```

Do not keyword-stuff for LLMs. Prefer accurate product facts over marketing fog (`unmachined`).
Do not block legitimate crawlers that you want citations from without product reason.
Do not claim `llms.txt` is a standard, ranking signal, crawler permission file, or replacement for
public crawlable pages. Separate search, training, user-fetch, and ads crawler policies.

## Anti-patterns

- Duplicate titles across pages
- Missing or boilerplate meta description (snippets then come only from page text)
- Blocking `/app/` in robots but linking it publicly
- Keyword stuffing in headings
- Client-only rendered content for critical SEO text (keep key copy in RSC)
- Broken OG images (wrong dimensions, HTTP not HTTPS)
- Fake FAQ or other schema that does not match visible content

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
