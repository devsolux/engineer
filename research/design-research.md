# Design & frontend research corpus (2026)

**Date**: 2026-07-12 · **Feeds**: `design-system.md`, `design-accessibility.md`, `design-patterns.md`

## Executive summary

2026 UI/frontend standards converge on:

1. **Three-tier design tokens** (primitive → semantic → component) with DTCG JSON + CSS `@theme`
2. **WCAG 2.2 AA as floor** — legal (EAA), ISO 40500; bake into components, not overlays
3. **8pt spacing grid** + 12-column layout + mobile-first `min-width` breakpoints
4. **shadcn as owned source** — wrapper pattern, OKLCH tokens, product abstractions
5. **Form UX**: labels above, on-blur validation, field-level errors (22% error reduction)
6. **Dashboard UX**: one task per screen, F-pattern, defaults not empty, operational not static

---

## 1. Design systems at scale

**Sources**: alphonsolabs.com, digitalapplied.com, devstudioit.com, productrocket.ro, design.dev

### Requirements checklist (2026)

- [ ] Three-tier tokens with semantic layer as primary API
- [ ] Versioned component library with documented APIs
- [ ] WCAG 2.2 AA in every primitive
- [ ] Governance model (centralized or federated)
- [ ] Figma-to-code sync or shared token JSON
- [ ] Visual regression testing in CI
- [ ] Living docs with do/don't examples

### Token architecture

```
Primitive     →  Semantic           →  Component (sparingly)
--gray-950       --color-text-primary   --button-primary-bg
--brand-500      --color-surface-canvas
```

- Name by **intent** (`color.feedback.success`), not appearance (`color.green`)
- T-shirt spacing: xs/sm/md/lg — not arbitrary numbers
- Style Dictionary or `@theme inline` for multi-platform output
- 84% mature systems use tokens as primary distribution (Specify 2024 survey)

### shadcn 2026 model

- Components are **copied source**, not npm dependency
- Theme = CSS variables on `:root` / `.dark`
- Tailwind v4: `@theme inline` maps vars to utilities
- OKLCH preferred over HSL for new palettes
- Customize via: (1) tokens, (2) className, (3) CVA variants, (4) wrappers — in that order
- Never edit generated files for one-off color patches

---

## 2. Accessibility (WCAG 2.2 AA)

**Sources**: w3.org/WAI WCAG 2.2, forasoft.com, muz.li, levelaccess.com, stauffer.com

### Legal/context (2026)

- WCAG 2.2 W3C Recommendation (Oct 2023); ISO/IEC 40500:2025
- EU Accessibility Act enforceable from June 2025
- 94.8% of top 1M homepages had ≥1 WCAG failure (WebAIM 2025)
- Accessibility overlay widgets fail technically and legally — design-system approach required

### New WCAG 2.2 criteria affecting design

| ID | Requirement |
|---|---|
| 2.4.11 | Focus not fully obscured by sticky content |
| 2.4.13 | Focus appearance (AAA aspirational): 2px+, 3:1 |
| 2.5.7 | Drag alternatives (buttons for drag actions) |
| 2.5.8 | Target size minimum 24×24 CSS px |
| 3.3.8 | Accessible authentication (no cognitive puzzles) |
| 3.2.6 | Consistent help placement |
| 3.3.7 | Redundant entry (reuse prior form data) |

### Practical checklist (90% of issues)

- 4.5:1 body text; 3:1 large text and UI components
- 16px body minimum; 65ch max line length
- 44×44px touch targets (exceed 24px WCAG minimum)
- Visible focus rings; never naked outline removal
- Labels above fields; placeholder ≠ label
- Errors: color + icon + text below field
- `prefers-reduced-motion` honored with designed static variants
- Heading hierarchy without skipped levels

### Seven pillars (forasoft 2026 playbook)

Contrast → Type → Focus → Motion → Input flexibility → Content clarity → Error recovery

---

## 3. Typography & spacing

**Sources**: uxpin.com grids guide, gridmakerpro.com, timgraf.com 8pt grid, justfigma.com

### 8pt grid

- All spacing: multiples of 8 (8, 16, 24, 32, 48, 64, 96)
- 4px half-step for dense UI only
- Gutters typically 16–32px (also 8pt multiples)
- Baseline grid aligns with 8pt for vertical rhythm

### Layout

- 12-column grid (divides by 2, 3, 4, 6)
- Mobile-first: 4 → 8 → 12 columns
- Max width: ~1200px marketing, ~1320px app content
- Container queries for component responsiveness (2026 standard alongside media queries)
- Fluid typography via `clamp()`

### Breakpoints (content-driven, Tailwind-aligned)

640 / 768 / 1024 / 1280 / 1536 — add only where layout breaks

---

## 4. Form UX (research-backed)

**Sources**: fomr.io, heurilens.com, kirro.io, uiguides.com, Baymard, Luke Wroblewski

| Finding | Source | Impact |
|---|---|---|
| Top-aligned labels fastest | Penzo eye-tracking | Fewest fixations |
| On-blur validation | Wroblewski | −22% errors |
| Inline validation overall | Baymard | −42% completion time, +22% success |
| Single column on mobile | Heurilens A/B | 15.4% higher completion |
| Placeholder as label | NN/g | Explicit anti-pattern |

### Rules encoded in engineer

1. Labels above, always visible
2. Validate on blur; success checkmark when valid
3. Errors below field, specific and constructive
4. Single column default
5. Minimal fields; progressive profiling
6. Smart defaults; don't force config before value

---

## 5. SaaS dashboard UX

**Sources**: saasframe.io, eleken.co, sanjaydey.com, flowmazeux.com, NN/g

### Core principles

- **One primary task per screen** (2.3s scan decision — NN/g)
- **F-pattern** placement: north-star metric top-left
- **Operational** dashboards suggest next action, not static reports
- **Defaults over empty** — show last 30 days, not "configure first"
- **Role-based default views** beat universal dashboards
- **Collapsible left sidebar** for multi-module SaaS
- **Empty states** = CTA to first action, not blank charts
- Load time **<2.5s**; skeleton loaders match layout

### Visualization

- Bar charts from zero; no 3D
- If hover required to understand chart → failed
- Color for status only; tables right-align numbers
- Dark mode: deep gray not pure black; test muted text contrast

---

## 6. Conversion / landing (2026)

**Sources**: vezadigital.com, saasframe.io trends, saasdesign.io

- One objective per page; 5th–7th grade reading level
- Product-first hero (screenshot/demo > abstract 3D)
- Bento grids for multi-capability products
- Sticky primary CTA after hero
- Reduced navigation on pure landing pages
- Typography personality returning (deliberate pairing vs all-neutral)
- Minimal motion with meaning

---

## 7. Color & dark mode

**Sources**: llmbestpractices shadcn-theming, tailwindcss.com/theme, design.dev

- OKLCH for perceptually uniform palettes (2026 production-safe)
- Semantic tokens enable one-file rebrand
- Dark: `#121212`–`#0a0a0a` range; avoid pure black halation
- Status colors separate from brand accent
- `color-mix()` for tints/shades
- Contrast-audit semantic pairs at token definition time

---

## 8. Motion

**Sources**: forasoft accessibility playbook, design-system motion tokens

- Transform + opacity only for performance
- Design reduced-motion variant alongside every animation
- Decorative motion <500ms
- No auto-advancing carousels without pause
- No flashing >3/sec

---

## Canonical sources

### Standards
- https://www.w3.org/TR/WCAG22/
- https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- https://tailwindcss.com/docs/theme
- https://ui.shadcn.com/docs/theming
- https://github.com/shadcn-ui/ui/blob/main/skills/shadcn/customization.md

### Design systems
- https://www.alphonsolabs.com/design-system-requirements-2026/
- https://www.digitalapplied.com/blog/design-systems-2026-scale-ui-without-chaos-methodology
- https://design.dev/guides/design-systems/
- https://llmbestpractices.com/frontend/shadcn-theming

### UX research
- https://fomr.io/blog/form-ux-best-practices
- https://heurilens.com/blog/interaction-flow/form-ux-design-rules-reduce-abandonment
- https://www.saasframe.io/blog/the-anatomy-of-high-performance-saas-dashboard-design-2026-trends-patterns
- https://www.uxpin.com/studio/blog/ui-grids-how-to-guide/
- https://developerux.com/2026/06/24/responsive-design-mobile-first-approach/

### Accessibility
- https://www.forasoft.com/blog/article/ai-accessibility-ui-ux-design
- https://muz.li/blog/how-to-make-your-ui-accessible-a-practical-checklist-for-2026/

### Performance (compose, don't duplicate)
- https://github.com/vercel-labs/agent-skills (react-best-practices)
