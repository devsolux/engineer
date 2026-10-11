# Design patterns: layout, forms, dashboards, responsive

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

UX and UI patterns backed by 2026 research (NN/g, Baymard, Luke Wroblewski form
studies, SaaS dashboard analyses). Pair with `design-system.md` (tokens), `design-taste.md` (aesthetic), and
`conversion-ui.md` (marketing funnels).
For persuasive or choice-shaping UI, also load `behavioral-design.md`; accessibility
and user autonomy are hard gates, not conversion tradeoffs.

## Contents
- [Visual hierarchy](#visual-hierarchy)
- [Responsive and mobile-first](#responsive-and-mobile-first)
- [Navigation patterns](#navigation-patterns)
- [Form design](#form-design)
- [Dashboard design](#dashboard-design)
- [Empty, loading, error states](#empty-loading-error-states)
- [Data visualization](#data-visualization)
- [Anti-patterns](#anti-patterns)

## Visual hierarchy

Users scan in **F-pattern** (dashboards, dense UI) or **Z-pattern** (marketing hero):

| Zone | Placement |
|---|---|
| Primary metric / headline | Top-left (first fixation) |
| Primary action | Top-right or end of F-bar |
| Secondary content | Below left column |
| Tertiary | Right / below fold |

Rules:
- **One primary action** per viewport section
- Size + position = importance (not color alone)
- Whitespace separates groups; tighter spacing within groups
- Strong colors (red/amber/green) **only for status** - not decoration
- Progressive disclosure: summary first, details on interaction

## Responsive and mobile-first

### Approach

1. Base CSS for smallest screen - **no media query**
2. Add `min-width` breakpoints only where layout breaks
3. Use relative units (`rem`, `%`, `fr`, `clamp`)
4. Test: **320, 375, 768, 1024, 1280** - not device names

### Reference breakpoints (Tailwind-aligned)

| Name | min-width | Typical use |
|---|---|---|
| base | - | Phone portrait |
| sm | 640px | Large phone |
| md | 768px | Tablet |
| lg | 1024px | Laptop |
| xl | 1280px | Desktop |
| 2xl | 1536px | Wide |

Use 3-4 breakpoints per project unless content demands more.

### Modern additions (2026)

- **Container queries** - component adapts to parent, not viewport
- **Fluid typography** - `clamp(min, preferred, max)` reduces breakpoint jumps
- **Mobile-specific views** for dashboards - don't squish desktop; show top 3 KPIs

### Mobile web production rules

- Use `100dvh` for interactive full-height shells with a `100svh` fallback. Do not lock content to
  legacy `100vh` where browser chrome or the virtual keyboard can cover controls.
- Pad fixed top and bottom UI with `env(safe-area-inset-*)`; keep primary actions above the keyboard
  and test focused fields, scroll-to-error, and modal/drawer resize on iOS and Android engines.
- Do not encode behavior from width alone. Pair responsive layout with input capabilities such as
  `hover: hover` and `pointer: fine`; every hover action needs a tap, keyboard, and visible-focus path.
- Preserve text zoom and user scaling. Do not disable pinch zoom. Use at least 16px input text on
  mobile when browser auto-zoom would otherwise disrupt the form.
- Avoid horizontal page overflow. Wide tables need a deliberate card, priority-column, disclosure, or
  contained scroll design with an accessible label, not a compressed desktop table.
- Keep sticky/fixed chrome small and collision-tested against cookie banners, toasts, install prompts,
  drawers, and bottom navigation. One viewport may have several independent overlays.
- Serve responsive image candidates and size them for rendered width and device pixel ratio. Mobile
  layout does not justify sending the desktop hero asset.
- Treat orientation changes, foldables, and split-screen widths as content-break cases. Do not require
  a wide orientation unless a product constraint is explained and offers a recovery path.

### Images

- `next/image` with explicit dimensions (CLS prevention)
- `srcset` / responsive sizes
- Above-fold: `priority`; below-fold: lazy

## Navigation patterns

| Surface | Pattern |
|---|---|
| Marketing landing | Minimal nav or none; single CTA focus |
| SaaS app | Collapsible **left sidebar** (scales for modules) |
| Marketing site | Top nav + sticky CTA after hero scroll |
| Deep app | Breadcrumbs for orientation |

Rules:
- Sticky headers: ensure they don't obscure focused elements (WCAG 2.4.11)
- Frosted chrome: `backdrop-filter` + semi-transparent bg - test focus visibility
- Mobile nav: render outside backdrop-filter parent if fixed positioning breaks

## Form design

Research-backed rules (22% fewer errors with on-blur validation):

### Layout

- **Single column** - multi-column only for logical pairs (city/state)
- Labels **above** fields (4-8px gap) - fastest scan path (Penzo eye-tracking)
- One field group = label + input + helper + error as a unit

### Labels and placeholders

- Labels **always visible** - never placeholder-only (NN/g explicit warning)
- Placeholder = format hint only (`MM/DD/YYYY`, `name@example.com`)

### Validation timing

| Strategy | Use |
|---|---|
| **On blur** | Default - validate when leaving field |
| On submit only | Worst - avoid except tiny forms |
| While typing | Password strength only |
| Real-time success | Checkmark when valid - reinforces progress |

Errors below field; specific + constructive:
- ✅ "Password must be at least 8 characters. You entered 6."
- ❌ "Invalid input"

Multi-signal errors: color + icon + text.

### Friction reduction

- Minimal fields on signup; defer profile to post-auth
- Smart defaults (last 30 days on date filters)
- Autocomplete attributes; support password managers
- Don't block paste
- Multi-step: honest progress indicator; preserve data across steps

## Dashboard design

### Principles (2026 consensus)

1. **One primary task per screen** - not 47 widgets
2. **Operational, not static** - suggest next action, not just charts
3. **Defaults over empty** - show last 30 days data, not "configure first"
4. **F-pattern hierarchy** - north-star metric top-left
5. **Role-based views** - admin vs operator vs viewer defaults
6. Load **<2.5s**; skeletons matching final layout

Before layout, name the audience, recurring decision, action, metric definition, freshness SLA,
comparison baseline, and failure response. A dashboard is not a warehouse browser. Every KPI exposes
its formula, unit, time zone, source, last refresh, scope, and drill path; totals reconcile with the
underlying records.

Use separate surfaces for distinct jobs: executive outcome review, operational queue, exploratory
analysis, and incident monitoring do not share one default density or refresh model. Alerts report a
meaningful state change and owner rather than mirroring every chart threshold. Preserve filters and
time range in the URL when sharing the view is part of the job.

### Layout

```
┌─────────────────────────────────────────┐
│ [Nav] │ KPI KPI KPI [filter] │
│ │───────────────────────────────│
│ │ Primary chart / table │
│ │───────────────────────────────│
│ │ Secondary panels │
└─────────────────────────────────────────┘
```

### Tables

- Sticky headers on scroll
- Zebra striping or row hover for scan
- **Right-align numbers** - decimal points stack
- Sortable columns; pagination with scope indicator
- Empty state → CTA to create first item

### Charts

- If user must hover to understand the chart, it failed
- Bar charts start at zero
- Never 3D charts
- Color + label for series - not color alone
- Line charts for change over time; bars for comparison
- Show uncertainty, missing data, partial periods, sampling, and material definition changes.
- Compare with the relevant baseline or target; a lone large number rarely supports a decision.
- Avoid dual axes unless the relationship and scales remain unambiguous.

### Dark dashboards

- Deep gray bg, not `#000`
- Semantic color tokens for status (traffic light logic sparingly)
- Test contrast on muted text (APCA/WCAG)

## Empty, loading, error states

| State | Pattern |
|---|---|
| **Loading** | Skeleton matching final layout - not spinner-only for pages |
| **Empty** | Illustration optional; **clear CTA** ("Create your first project") |
| **Error** | Human message + retry; log details server-side |
| **Partial** | Show cached/stale data + refresh indicator |

Every async surface needs all three designed - not afterthought. Copy in these
states is design material (`design-taste.md`): say what happened and the next
action. Do not invent metrics to fill an empty dashboard.

Interactive controls: default, hover, `:focus-visible`, active, disabled, plus
loading/error/success when those states exist. Focus rings are visible and not
animated on. Hover-only behavior always has a tap and keyboard path.

## Data visualization

- Reserve red for broken/critical; amber warning; green success
- Direct labels on charts when possible (reduce legend dependency)
- Sparklines for inline trends; full chart for exploration
- Accessible: table fallback or data summary for screen readers

## Anti-patterns

- Dashboard as static report with no actions
- Empty chart with no guidance
- Carousel hero on landing (hurts LCP, hides CTA)
- Multi-column forms on mobile
- Submit-time-only validation dump at top
- Generic "Please correct errors" banner
- 5+ equal-weight CTAs in one viewport
- Responsive = horizontal scroll table with no mobile view
- Custom chart types when bar/line answers the question

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
