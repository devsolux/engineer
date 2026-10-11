---
description: Launch pipeline — SEO, conversion UI, growth funnels, performance, copy audit.
---

# /engineer-landing

Load engineer `SKILL.md` + `references/workflows.md` (Landing launch).

Landing brief follows this invocation.

## Pipeline order

```
seo-metadata → design-taste → conversion-ui → growth-funnels → frontend-performance
```

## Checklist

- [ ] Unique metadata + OG + canonical
- [ ] `sitemap.ts` / `robots.ts` if marketing site
- [ ] Named tone + signature (`design-taste.md`); not Inter/indigo/three-cards
- [ ] One primary CTA, semantic tokens
- [ ] CWV: LCP hero, CLS skeletons, INP client boundaries
- [ ] Analytics stubs on signup + primary CTA
- [ ] **unmachined** pass on hero + CTA copy

## Build

Use `/engineer-page` for implementation after checklist approved.

## Verify

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
bash "$ENGINEER/scripts/engineer-scan.sh" --design --strict
```
