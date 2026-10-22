# Frontend performance: Core Web Vitals and bundle discipline

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

Targets (75th percentile field data - CrUX, not lab-only):

| Metric | Good | Fix category |
|---|---|---|
| **LCP** | ≤ 2.5s | Loading - hero image, TTFB, fonts |
| **INP** | ≤ 200ms | Interactivity - JS long tasks, hydration |
| **CLS** | ≤ 0.1 | Stability - dimensions, fonts, dynamic inserts |

SPA soft navigations: CrUX added experimental soft-nav LCP/INP/CLS variants (Sept 2026 release);
collect with `web-vitals` `reportSoftNavs: true` (Chromium 151+). Track them; keep gating on the stable CWV.

Compose with vercel `react-best-practices` for the full 70-rule set.

## Contents
- [LCP checklist](#lcp-checklist)
- [INP checklist](#inp-checklist)
- [CLS checklist](#cls-checklist)
- [Fonts (`next/font`)](#fonts-nextfont)
- [Dynamic imports](#dynamic-imports)
- [Bundle hygiene](#bundle-hygiene)
- [Measurement](#measurement)
- [Anti-patterns](#anti-patterns)
- [Enforcement](#enforcement)

## LCP checklist

1. **Hero image**: `next/image` `preload` (Next 16 deprecates `priority`) or `loading="eager"` / `fetchPriority="high"` (the docs' usual pick) - 1-2 per page max
2. **Never lazy-load** above-the-fold LCP element
3. **`sizes` prop** on every responsive image - prevents oversized downloads
4. **WebP** via next/image (automatic); AVIF is opt-in via `images.formats`
5. **TTFB** ≤ 800ms - CDN, edge cache, fast server/data layer
6. **Self-host fonts** via `next/font` - no Google Fonts `<link>` at runtime

```tsx
import Image from "next/image";
import hero from "@/public/hero.webp";

<Image
 src={hero}
 alt="Product dashboard showing real-time metrics"
 preload
 sizes="(max-width: 768px) 100vw, 1200px"
 placeholder="blur"
 className="h-auto w-full"
/>
```

## INP checklist

INP (Interaction to Next Paint) is the interactivity Core Web Vital (target ≤200ms).

1. **Minimal client JS** - RSC default; push `"use client"` to leaves
2. **Break long tasks** >50ms - split work; `scheduler.yield()` where supported
3. **`next/dynamic`** for heavy libs (charts, editors, maps) with fixed-height fallback
4. **No barrel imports** in hot paths - direct file imports
5. **Defer third-party scripts** - analytics/chat after interactive (`afterInteractive` / `lazyOnload`)
6. **Selector-based subscriptions** in Zustand - not whole-store re-renders
7. **Urgent vs transition updates** - keep click feedback on the urgent path; push list refilters to `startTransition` / `useDeferredValue`
8. **Hydration cost** - fewer client islands; avoid serializing huge props into client trees
9. **Handlers stay thin** - no sync JSON parse of megabyte payloads on click
10. **Motion** - transform/opacity only; respect reduced-motion (`design-motion.md`)

```tsx
import { startTransition, useDeferredValue, useState } from "react";

// Typing stays snappy; expensive filter is non-urgent
const [query, setQuery] = useState("");
const deferred = useDeferredValue(query);

function onFilterClick(next: string) {
 // paint press state immediately if needed, then:
 startTransition(() => setQuery(next));
}
```

Measure: Chrome DevTools Performance panel live metrics (the Web Vitals extension is end-of-life); field data via RUM (`observability.md`).

## CLS checklist

1. **Width + height** (or `fill` + aspect container) on every image/video/iframe
2. **`next/font`** with `display: "swap"` and CSS variable in root layout
3. **Skeleton dimensions** match final layout - Suspense fallbacks reserve space
4. **Reserve space** for ads, banners, cookie bars before they load
5. **No content injection** above existing content without reserved height

## Fonts (`next/font`)

```tsx
// app/layout.tsx
import { Geist, Geist_Mono } from "next/font/google";

const geistSans = Geist({
 subsets: ["latin"],
 variable: "--font-geist-sans",
 display: "swap",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
 return (
 <html lang="en" className={geistSans.variable}>
 <body className="font-sans antialiased">{children}</body>
 </html>
 );
}
```

- One sans + optional mono/display - don't load 4 families
- Pass via CSS variables to `@theme` / shadcn tokens

## Dynamic imports

```tsx
import dynamic from "next/dynamic";

const RevenueChart = dynamic(
 () => import("@/features/analytics/revenue-chart"),
 {
 loading: () => <ChartSkeleton height={320} />,
 ssr: false, // only when lib requires window; Client Components only
 }
);
```

Fallback must have **fixed height** to prevent CLS.

## Bundle hygiene

- Run `next analyze` (Turbopack; 16.4+, `experimental-analyze` in 16.1-16.3) or `@next/bundle-analyzer` (webpack builds) periodically; `next build` stopped printing JS sizes in 16.0
- Audit `"use client"` file count - each adds to client graph
- Prefer CSS over JS for hover/focus states
- Tree-shake icon imports (`lucide-react` - import named icons only)
- Server Components for data - never fetch in client `useEffect` when RSC works

## Measurement

- **Field data first** - Search Console CrUX, Vercel Speed Insights, web-vitals RUM
- Lab: Lighthouse for regressions, not as sole pass/fail
- Fix template-level issues before individual URLs
- Set performance budgets: JS bundle, LCP element weight, third-party count

## Anti-patterns

- `preload` / `priority` on every image
- Raw `<img>` without dimensions
- Google Fonts CDN link in production
- Full-page `"use client"` layout
- Chart library in main bundle
- Measuring only Lighthouse lab score
- Suspense fallback with no reserved dimensions

## Enforcement

| Rule | Tool |
|---|---|
| Hardcoded colors | `engineer-scan --design` |
| `"use client"` on layouts | `engineer-scan --strict` |
| CWV regression | Lighthouse CI / RUM threshold alert (`web-vitals`, Speed Insights drain) |
| Bundle size | `next analyze --output` or `@next/bundle-analyzer` + size-limit in CI |

See `enforcement.md` for CI templates.

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
