---
description: Multi-locale pipeline — next-intl, hreflang SEO, conversion UI.
---

# /engineer-locale

Load engineer `SKILL.md` + `references/workflows.md` (Multi-locale).

Locale requirements follow this invocation.

## Pipeline

```
frontend-i18n → seo-metadata → conversion-ui
```

## Hard gates

- `app/[locale]/` for all routes
- `setRequestLocale` before translations (static rendering)
- `@/i18n/navigation` Link — not raw `next/link`
- hreflang alternates + x-default in metadata
- Language switcher sets cookie

## Verify

Invalid locale → `notFound()`. Message key parity across JSON files.

## Build

Implement with `/engineer` after routing plan confirmed.
