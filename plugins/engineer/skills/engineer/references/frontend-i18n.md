# Frontend i18n: next-intl on App Router

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Internationalization for Next.js App Router. SEO cross-ref: `seo-metadata.md`.
Design copy: `conversion-ui.md` + `unmachined`.

## Contents
- [When to add i18n](#when-to-add-i18n)
- [Architecture](#architecture)
- [Setup checklist](#setup-checklist)
- [Core files](#core-files)
- [Server vs client translations](#server-vs-client-translations)
- [Message file conventions](#message-file-conventions)
- [Language switcher](#language-switcher)
- [SEO (with seo-metadata.md)](#seo-with-seo-metadatamd)
- [Forms and validation](#forms-and-validation)
- [Testing](#testing)
- [Anti-patterns](#anti-patterns)
- [Composition](#composition)

## When to add i18n

| Signal | Action |
|---|---|
| Single locale, no roadmap | Skip - use `lang="en"` on `<html>` |
| EU market or multi-region launch | Add before public marketing pages ship |
| User-generated content only | Locale UI strings only; UGC stays as-is |
| Existing app without `[locale]` | Plan migration - touches routing, metadata, sitemap |

## Architecture

```
app/
 [locale]/
 layout.tsx # validate locale, setRequestLocale, NextIntlClientProvider
 page.tsx
i18n/
 routing.ts # defineRouting - locales, defaultLocale, localePrefix
 request.ts # getRequestConfig - load messages per locale
 navigation.ts # createNavigation - Link, useRouter, redirect
messages/
 en.json
 de.json
proxy.ts # Next 16: createMiddleware(routing) from next-intl, export as proxy
         # Next 15: middleware.ts with the same createMiddleware(routing)
```

**Locale-prefixed URLs** (`/en/pricing`, `/de/pricing`) keep caching, SEO, and
analytics deterministic. Prefer `localePrefix: 'always'` for production SaaS.

## Setup checklist

- [ ] `app/[locale]/` wraps all routes (not mixed with un-prefixed routes)
- [ ] Invalid locale → `notFound()` in root layout
- [ ] `generateStaticParams` returns all locales (static rendering)
- [ ] `setRequestLocale(locale)` **before** any `useTranslations` / `getTranslations`
- [ ] Navigation uses `@/i18n/navigation` - not `next/link` directly
- [ ] Language switcher sets cookie + navigates (don't rely on Accept-Language alone)
- [ ] `generateMetadata` per locale with hreflang alternates
- [ ] Sitemap includes all locale variants

## Core files

### routing.ts

```typescript
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
 locales: ["en", "de"],
 defaultLocale: "en",
 localePrefix: "always",
});
```

### request.ts

```typescript
import { getRequestConfig } from "next-intl/server";
import { hasLocale } from "next-intl";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
 const requested = await requestLocale;
 const locale = hasLocale(routing.locales, requested)
 ? requested
 : routing.defaultLocale;

 return {
 locale,
 messages: (await import(`../messages/${locale}.json`)).default,
 };
});
```

### proxy.ts (Next 16)

```typescript
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

const handleI18n = createMiddleware(routing);

export function proxy(request: Request) {
  return handleI18n(request);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
```

On Next 15, keep `middleware.ts` with `export default createMiddleware(routing)` and the same matcher. Compose i18n with the Supabase `updateSession` helper in one root interceptor — do not run two competing boundary files.

### layout.tsx (static rendering)

```typescript
import { hasLocale } from "next-intl";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";

export function generateStaticParams() {
 return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
 children,
 params,
}: {
 children: React.ReactNode;
 params: Promise<{ locale: string }>;
}) {
 const { locale } = await params;
 if (!hasLocale(routing.locales, locale)) notFound();

 setRequestLocale(locale);

 return (
 <html lang={locale}>
 <body>{children}</body>
 </html>
 );
}
```

Call `setRequestLocale` in **every** layout and page that should static-render.

## Server vs client translations

```typescript
// Server Component
import { getTranslations } from "next-intl/server";

export async function Hero() {
 const t = await getTranslations("Home");
 return <h1>{t("title")}</h1>;
}
```

```typescript
"use client";
import { useTranslations } from "next-intl";

export function CtaButton() {
 const t = useTranslations("Home");
 return <button>{t("cta")}</button>;
}
```

Keep client boundaries at leaves - same RSC rules as `frontend.md`.

## Message file conventions

```json
{
 "Home": {
 "title": "Ship faster",
 "cta": "Start free trial"
 },
 "Settings": {
 "title": "Settings",
 "saveSuccess": "Saved"
 }
}
```

Rules:
- Namespace by feature/page (`Home`, `Settings`, `Billing`)
- ICU syntax for plurals and interpolation: `{count, plural, one {# item} other {# items}}`
- No HTML in JSON - use `t.rich()` for links/emphasis
- Type-safe keys: enable `next-intl` TypeScript augmentation when stable

## Language switcher

```typescript
"use client";
import { useRouter, usePathname } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

export function LocaleSwitcher({ locale }: { locale: string }) {
 const router = useRouter();
 const pathname = usePathname();

 function onSelect(next: string) {
 document.cookie = `NEXT_LOCALE=${next};path=/;max-age=31536000;SameSite=Lax`;
 router.replace(pathname, { locale: next });
 }

 return (
 <select value={locale} onChange={(e) => onSelect(e.target.value)}>
 {routing.locales.map((l) => (
 <option key={l} value={l}>{l.toUpperCase()}</option>
 ))}
 </select>
 );
}
```

## SEO (with seo-metadata.md)

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
 const { locale, slug } = await params;
 const base = process.env.NEXT_PUBLIC_BASE_URL!;
 const languages: Record<string, string> = {};

 for (const l of routing.locales) {
 languages[l] = `${base}/${l}/blog/${slug}`;
 }
 languages["x-default"] = `${base}/en/blog/${slug}`;

 return {
 title: "...",
 alternates: { canonical: `/${locale}/blog/${slug}`, languages },
 };
}
```

## Forms and validation

- Zod error messages: map codes to i18n keys in the UI layer, not in schema strings
- Date/number: use `useFormatter()` / `format.dateTime()` - never `toLocaleString()` ad hoc
- RTL locales: test layout with logical properties (`ms-`, `me-`, `ps-`, `pe-`)

## Testing

| Layer | Tool |
|---|---|
| Message completeness | Script diff locale keys across JSON files |
| Routing | Playwright: `/` redirects, switcher preserves path |
| SEO | Assert hreflang in metadata / `<head>` |
| a11y | `lang` on `<html>` matches active locale |

Storybook: see `storybook-dx.md` for next-intl addon.

## Anti-patterns

| Don't | Do |
|---|---|
| Mix `/about` and `/en/about` routes | All pages under `[locale]` |
| Skip `setRequestLocale` | Call before every translation API |
| Hardcode strings in components | Keys in `messages/*.json` |
| `next/link` for internal nav | `@/i18n/navigation` Link |
| Translate server errors in Zod schema | Map error codes in UI |
| Header-based locale without URL | Locale in URL for cache + SEO |
| Ship without hreflang | Full alternates + x-default |

## Composition

| Module | When |
|---|---|
| `seo-metadata.md` | hreflang, sitemap, canonical per locale |
| `frontend-performance.md` | static rendering via setRequestLocale |
| `compliance-privacy.md` | locale consent, GDPR copy |
| `storybook-dx.md` | component docs with locale switch |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
