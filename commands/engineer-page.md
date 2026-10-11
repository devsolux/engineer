---
description: Build a landing or marketing page — conversion UI, SEO, growth funnel hooks.
---

# /engineer-page

Load engineer `SKILL.md`. Pipeline: **design-taste → conversion-ui → design-patterns → design-system → seo-metadata**.

User's page brief follows this invocation.

## Checklist

- [ ] Named tone + signature (`design-taste.md`) before layout
- [ ] Structure is not the default Hero → 3 cards → CTA skeleton
- [ ] One primary CTA above fold
- [ ] Semantic tokens only — no hardcoded colors
- [ ] Page job statement + outcome-first headline
- [ ] No invented metrics, logos, or testimonials
- [ ] Metadata + OG via `seo-metadata.md`
- [ ] Loading / error states if dynamic sections
- [ ] Analytics event stubs on primary CTA
- [ ] Compose **unmachined** on hero copy when ready

## Optional

- Performance pass: `frontend-performance.md`
- Full pipeline: `/engineer-landing`

## Verify

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
bash "$ENGINEER/scripts/engineer-scan.sh" --design --strict
```
