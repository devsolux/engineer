---
description: Design system, accessibility, and UI pattern audit — tokens, WCAG, forms, dashboards.
---

# /engineer-design

Load engineer `SKILL.md`. Routes: **design-system + design-accessibility + design-patterns**.
For new UI, landings, redesigns, or "looks generic / AI / slop": also load **`design-taste.md`**.

Audit target follows this invocation (path, component, or "new tokens").

## If auditing existing UI

Use `/engineer-audit` output format. Check:

- Semantic tokens vs hardcoded palette
- WCAG 2.2 AA contrast, focus, 44px targets
- Form labels above fields, on-blur validation
- Dashboard F-pattern, empty/loading states
- One primary action per view
- Named tone + signature (`design-taste.md`); not Inter/indigo/three-card defaults

## If setting up new design system

Follow `design-system.md`:

- Three-tier tokens (primitive → semantic → component)
- Tailwind v4 `@theme` bridge
- Contrast audit on semantic pairs

## Compose

**unmachined** for copy/UI tell audit on marketing surfaces.
