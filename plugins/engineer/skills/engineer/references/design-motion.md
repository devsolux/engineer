# Motion and density

**Last verified**: 2026-08-21 · **Review cadence**: 3 months

Product feel without breaking a11y or INP. Load with `design-system.md`,
`design-accessibility.md`, `frontend-performance.md` (INP), `design-patterns.md`.

## Density (layout rhythm)

Pick **one** product density; do not mix comfortable and compact in the same app shell.

| Density | Base spacing | Use |
|---|---|---|
| Comfortable | 4/8/12/16/24/32 | Consumer, marketing-adjacent apps |
| Default SaaS | 4/8/12/16/24 | Most B2B dashboards |
| Compact | 2/4/8/12/16 | Data-dense ops / trading-style UIs |

Rules:
- Map density to spacing tokens (`--space-*`), not one-off `p-[13px]`
- Tables and side nav can be one step denser than marketing pages in the same brand if intentional
- Touch targets stay **≥44px** even in compact mode (padding may grow hit area)
- Prefer fewer nested cards; density is whitespace discipline, not more boxes

```css
/* Tailwind v4 @theme sketch */
@theme {
 --space-1: 0.25rem;
 --space-2: 0.5rem;
 --space-3: 0.75rem;
 --space-4: 1rem;
 --space-6: 1.5rem;
 --space-8: 2rem;
}
```

## Motion tokens

| Token | Duration | Use |
|---|---|---|
| `--motion-fast` | 120-150ms | Hover, focus ring settle, micro feedback |
| `--motion-base` | 200-250ms | Panels, dialogs, expand/collapse |
| `--motion-slow` | 350-450ms | Rare page-level transitions |

Easing: one product curve, e.g. `cubic-bezier(0.22, 1, 0.36, 1)`. Never
default/linear easing on visible motion — pick a curve with weight. Avoid
bounce on data UIs.

Active press feedback: `scale(0.98)` or `translateY(1px)` at `--motion-fast`
makes buttons feel physical; keep it micro.

## What to animate

| Yes | No |
|---|---|
| `transform`, `opacity` | `width` / `height` / `top` layout thrash |
| Skeleton → content opacity | Page-wide parallax on dashboards |
| Dialog enter/exit | Infinite decorative loops that fight INP |

## Scroll-triggered reveals

- Drive reveals with `IntersectionObserver` or Framer Motion `whileInView` —
 never an unthrottled `window.addEventListener("scroll")` (continuous reflow,
 kills mobile INP).
- Reveal = transform + opacity only; reserve element dimensions so reveals
 never shift layout (CLS).
- Every revealed element has a static end state under reduced motion; content
 must exist without the animation.
- One reveal treatment per page. Stagger steps ≤150ms, and only where order
 means something. Word-by-word scroll reveals are a template tell
 (`design-taste.md`) — only with a named-brief reason.

## Reduced motion (required)

```css
@media (prefers-reduced-motion: reduce) {
 *,
 *::before,
 *::after {
 animation-duration: 0.01ms !important;
 animation-iteration-count: 1 !important;
 transition-duration: 0.01ms !important;
 scroll-behavior: auto !important;
 }
}
```

Also provide **static end states** for elements that start at `opacity: 0` - do not leave content invisible when motion is reduced.

In JS (Framer Motion / CSS-in-JS):

```typescript
const reduce =
 typeof window !== "undefined" &&
 window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// duration: reduce ? 0 : 0.2
```

## INP-aware motion

- Do not run heavy animation on the same frame as large React state updates
- Prefer CSS transitions over JS springs for chrome chrome
- Defer non-essential motion until after first interaction settles
- Charts/maps: load dynamically; animate series only after idle if needed

See `frontend-performance.md` INP checklist.

## Density + motion anti-patterns

- Mixing three card paddings on one page without token names
- 800ms menu animations on every navigation
- Animating layout on filter changes that reflow large tables
- Ignoring reduced-motion (a11y fail)
- Motion that blocks clicks until complete

## Related

- `design-system.md` - radius/shadow/motion short section
- `design-accessibility.md` - reduced-motion checklist
- `frontend-performance.md` - INP
- `design-patterns.md` - layout patterns
- `unmachined` - avoid decorative AI-slop motion

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
