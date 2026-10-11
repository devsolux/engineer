# Design system: tokens, type, color, spacing, motion

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Industry-standard design system rules for 2026. Sources: W3C DTCG token spec,
Tailwind v4 `@theme`, shadcn/ui theming docs, digitalapplied/alphonsolabs design
system guides. Compose with `unmachined` for anti-slop audits.

## Contents
- [Three-tier tokens](#three-tier-tokens)
- [Naming conventions](#naming-conventions)
- [Color](#color)
- [Typography](#typography)
- [Spacing and layout](#spacing-and-layout)
- [Radius, shadow, motion](#radius-shadow-motion)
- [Dark mode](#dark-mode)
- [shadcn + Tailwind v4](#shadcn--tailwind-v4)
- [De-genericization](#de-genericization)
- [Anti-patterns](#anti-patterns)

## Three-tier tokens

| Tier | Purpose | Example |
|---|---|---|
| **Primitive** | Raw palette values | `--color-lime-500`, `--gray-950` |
| **Semantic** | Role in UI (theme here) | `--color-text-primary`, `--color-surface-canvas` |
| **Component** | Only when it removes real duplication | `--button-primary-bg` |

**Rule**: Components reference **semantic** tokens only. Primitives exist in
`:root` / token JSON; never use primitive names in JSX/CSS outside token defs.

Implement in code:

```css
:root {
 /* primitive */
 --gray-950: oklch(0.14 0.01 250);
 --brand-500: oklch(0.75 0.18 120);

 /* semantic */
 --color-bg: var(--gray-950);
 --color-text-primary: oklch(0.93 0.01 250);
 --color-text-muted: oklch(0.65 0.01 250);
 --color-accent: var(--brand-500);
}

@theme inline {
 --color-bg: var(--color-bg);
 --color-text-primary: var(--color-text-primary);
 --color-accent: var(--color-accent);
}
```

Audit quarterly: delete tokens with no references outside `@theme`.

## Naming conventions

Use **intent, not appearance**:

| Bad | Good |
|---|---|
| `color-white` | `color-text-primary` |
| `color-green` | `color-feedback-success` |
| `spacing-13` | `spacing-md` (t-shirt scale) |

Schema: `category.property.variant` - e.g. `color.background.surface`,
`font.size.heading.lg`, `spacing.inline.md`.

## Color

### Semantic roles (minimum set)

- **Surface**: canvas, elevated, overlay
- **Text**: primary, secondary, muted, disabled
- **Border**: default, strong, focus
- **Action**: primary, secondary, destructive
- **Feedback**: success, warning, error, info

### Rules

- One chromatic **accent** for primary actions; status colors reserved for feedback
- Never pure `#000` / `#fff` - micro-tint neutrals (OKLCH preferred in 2026)
- Dark mode: deep gray `#121212`-`#0a0a0a` range, not pure black (reduces halation)
- Accent footprint ≤5% of viewport on marketing surfaces
- Run **WCAG AA contrast** on every semantic pair at token definition time -
 not per-component (see `design-accessibility.md`)

### OKLCH vs HSL

- **OKLCH**: perceptually uniform steps; preferred for new systems (shadcn 2026 default)
- **HSL channels**: shadcn legacy format `hsl(var(--primary))` - keep format consistent
- Derived tints: `color-mix(in oklab, var(--accent) 40%, transparent)`

## Typography

### Scale

Use a modular scale (1.25 major third or 1.333 perfect fourth):

| Role | Guidelines |
|---|---|
| Body | **16px minimum** (not 14px) |
| Line height | Body 1.5-1.65; display 1.05-1.2 |
| Line length | 45-75 characters (~65ch max) |
| Display tracking | `-0.02em` to `-0.03em` max |
| Micro-labels | Collapse to **2 tiers** (lg/sm) - prevents 8-size drift |

### Pairing

Pick display + body before writing code. Contrast axis: serif display + geometric
sans, or characterful display + mono data face. Avoid Inter/Roboto/Poppins as
unconsidered defaults.

### Fluid type

```css
--font-size-hero: clamp(2rem, 4vw + 1rem, 3.5rem);
```

Use `text-wrap: balance` on h1-h3; `text-wrap: pretty` on prose. Sizes land on the scale, never arbitrary (`text-[19px]`, stray `1.4rem`): snap to the nearest step below with its paired line height.

## Spacing and layout

### 8pt grid (industry standard)

All spacing from multiples of **8**: 8, 16, 24, 32, 48, 64, 96.
Half-step **4px** for dense UI (icon-label gaps, tight tables).

| Token | px | Use |
|---|---|---|
| space-1 | 4 | Icon-label, dense |
| space-2 | 8 | Inline chips |
| space-3 | 16 | Card padding, field gap |
| space-4 | 24 | Section padding, gutter |
| space-5 | 32 | Module separation |
| space-6 | 48+ | Hero whitespace |

**Spacing = grouping**: gap inside a group < gap between groups.

### Layout grid

- **12-column** grid for web apps (divides by 2, 3, 4, 6)
- Mobile-first: 4 col → 8 col → 12 col
- Max content width: 1100-1200px marketing; 1280-1320px dashboards
- Use **container queries** (`@container`) for component-level responsiveness
- Breakpoints where **content breaks**, not device names (see `design-patterns.md`)

## Radius, shadow, motion

### Radius

Pick a product feel once via `--radius` (shadcn derives sm-xl from it):

| Feel | `--radius` |
|---|---|
| Sharp / infra | `0` |
| Default SaaS | `0.5rem` (only if intentional) |
| Soft / consumer | `0.75rem-1rem` |
| Pill | `9999px` |

Nested (gap <32px): **inner radius = outer − gap**; result ≤2px → leave inner square. `rounded-2xl` + 8px padding → `rounded-lg` inner.

### Shadow

- Prefer **hairline borders** over heavy shadows for cards
- One elevation scale: sm / md / lg - map to semantic `--shadow-elevated`
- Dark UI: inset highlights + border luminance > drop shadows

### Motion

- Animate **transform and opacity** only
- Duration tokens: fast (150ms), base (250ms), slow (400ms)
- Shared easing: `cubic-bezier(0.22, 1, 0.36, 1)` or custom
- **`prefers-reduced-motion`**: provide static variants; don't just `animation: none`
 on elements that start at opacity 0
- Decorative motion ≤500ms; functional motion can be longer

## Dark mode

- Class strategy: `.dark` on root (next-themes standard)
- Semantic tokens swap in `.dark { }` - components unchanged
- Design **both modes** at token time; test contrast in each
- Don't toggle light/dark without user need - commit to mode when brand demands it

## shadcn + Tailwind v4

```css
@import "tailwindcss";

:root {
 --background: oklch(0.985 0 0);
 --foreground: oklch(0.145 0 0);
 --primary: oklch(0.205 0 0);
 --primary-foreground: oklch(0.985 0 0);
 --radius: 0.625rem;
}

@theme inline {
 --color-background: var(--background);
 --color-foreground: var(--foreground);
 --color-primary: var(--primary);
 --radius-lg: var(--radius);
}
```

Rules:
- Theme in `globals.css`, not component files
- **Wrapper pattern** for structural changes - don't edit `components/ui/*`
- Product abstractions: `AppButton`, `AppDialog` wrapping shadcn primitives
- OKLCH cssVars on new projects; run the locked local CLI with `npm exec --offline -- shadcn info --json` before generating

## De-genericization

Changing tokens is not a visual identity. Load `design-taste.md` for greenfield
UI, landings, and "this looks generic" work.

Change all three before building on shadcn:

| Dial | Stock fingerprint | Fix |
|---|---|---|
| `--primary` | muted indigo/zinc/violet | one brand accent from the subject |
| `--radius` | 0.5rem | sharp, soft, or pill - pick a feel |
| `--font-sans` | Inter / Geist | deliberate display + body pairing |

Add **one signature token** the stock theme doesn't ship (custom shadow stack,
grain, easing curve, border treatment). Apply consistently. If the page still
matches a 2026 AI cluster (cream+serif+terracotta, black+acid glow, indigo three-card),
it failed — `design-taste.md`.

## Anti-patterns

- Hardcoded `bg-blue-500` in components
- Primitive color names in JSX
- Magic numbers (13px, 27px padding)
- 8 different micro-label sizes
- Heavy shadow-md on every card
- Light and dark designed independently (token swap breaks)
- Editing shadcn generated files in place
- Theme decisions in `className` instead of token layer

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
