# Accessibility: WCAG 2.2 AA (design + frontend)

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Accessibility is a **component property**, not a post-ship audit. WCAG 2.2 AA is
the 2026 legal and industry floor (EU Accessibility Act, ISO/IEC 40500). Bake
requirements into tokens and primitives - overlays and widgets fail in production.

Sources: W3C WCAG 2.2, WAI "What's New in 2.2", forasoft/muzli 2026 checklists.

## Contents
- [Seven design pillars](#seven-design-pillars)
- [Contrast](#contrast)
- [Typography and readability](#typography-and-readability)
- [Focus and keyboard](#focus-and-keyboard)
- [Touch and pointer targets](#touch-and-pointer-targets)
- [Forms and errors](#forms-and-errors)
- [Motion and media](#motion-and-media)
- [Component checklist](#component-checklist)
- [Testing](#testing)
- [Anti-patterns](#anti-patterns)

## Seven design pillars

Encode at design-token and component level:

1. **Contrast** - token pairs audited for AA
2. **Type** - 16px body floor, line-length caps, spacing tokens
3. **Focus** - visible, not obscured by sticky chrome
4. **Motion** - reduced-motion variants designed alongside animations
5. **Input flexibility** - no drag-only; no cognitive puzzle auth
6. **Content clarity** - heading hierarchy, link purpose, labels
7. **Error recovery** - specific, field-level, multi-signal errors

## Contrast

| Element | WCAG 2.2 AA minimum |
|---|---|
| Body text (<18px, non-bold) | **4.5:1** |
| Large text (≥18px or ≥14px bold) | **3:1** |
| UI components + graphical objects | **3:1** |
| Focus indicator | **3:1** against adjacent colors |

Design-stage: aim **APCA Lc 75** for 14px body when tooling supports it.
When WCAG and APCA disagree, WCAG AA decides compliance.

**Dark mode**: WCAG formulas can miss perceptual failures - manually verify
muted text on `#121212` surfaces. Never grey text on colored backgrounds;
adjust lightness/saturation of the hue instead.

Lint semantic token pairs in CI where possible. See `enforcement-rules.md` § design token grep and axe Playwright gate.

## Typography and readability

- Body text: **minimum 16px**
- Line width: max **80 characters** (~65ch)
- Line height: ≥1.5 body; letter-spacing ≥0.12em where specified
- Heading hierarchy: h1 → h2 → h3 - **never skip levels**
- Link text must describe destination (not "click here")
- `lang` attribute on `<html>`

## Focus and keyboard

WCAG 2.2 new criteria relevant to design:

| Criterion | Requirement |
|---|---|
| **2.4.11 Focus Not Obscured (Minimum)** | Focused element partially visible - not fully hidden by sticky headers/modals |
| **2.4.13 Focus Appearance (AAA aspirational)** | Focus ring ≥2px perimeter, 3:1 contrast |

Implementation:
- Never `outline-none` / `outline-hidden` without `focus-visible:ring-*` replacement
- Tab order follows visual order
- Modals: focus trap, Esc dismiss, restore focus on close
- Skip link to main content on marketing/app shells
- All actions reachable via keyboard (Tab, Enter, Space, arrows where appropriate)

## Touch and pointer targets

| Standard | Minimum |
|---|---|
| WCAG 2.2 AA (2.5.8) | **24×24 CSS px** (with spacing alternative) |
| Apple HIG | 44×44 pt |
| Material | 48×48 dp |
| **Engineer default** | **44×44px** hit area (encode in button/link tokens) |

Icon-only controls: visual icon can be smaller; tappable area must meet minimum.
Space between targets so adjacent taps don't misfire.

## Forms and errors

See `design-patterns.md` for full form UX. Accessibility minimums:

- **Visible labels** always - never placeholder-only
- `htmlFor` / `aria-label` on every control
- `aria-invalid` + `aria-describedby` linking to error text
- Errors: **color + icon + text** - never color alone
- Required fields: programmatically indicated (`required` or `aria-required`)
- Autocomplete attributes for name, email, address, payment fields
- Never block paste on password or any field (WCAG 2.2 **3.3.8** Accessible Authentication — password managers must work)

## Motion and media

- **`prefers-reduced-motion`**: static alternatives for all non-essential animation
- No flashing >3 times per second
- Video/audio: captions/transcripts where applicable
- `alt` on informative images; decorative images `alt=""`

## Component checklist

Every interactive component in the library:

```
- [ ] Keyboard operable
- [ ] Focus visible and not obscured
- [ ] Touch target ≥44px (or 24px + spacing per WCAG)
- [ ] Color contrast passes on all states (default, hover, disabled)
- [ ] aria-label or visible label
- [ ] Dialog/Sheet: Title, focus trap, Esc
- [ ] Icon-only: aria-label
- [ ] Status not conveyed by color alone
- [ ] Reduced-motion variant exists if animated
```

Radix/shadcn primitives: **don't strip ARIA** when wrapping.

## Testing

Minimum per feature:
- Keyboard-only pass through primary flow
- VoiceOver (macOS) or NVDA (Windows) on signup/checkout
- axe or Lighthouse accessibility scan - fix critical/serious
- 320px viewport + 200% zoom

### Enforcement (make it stick)

| Layer | Tool | CI |
|---|---|---|
| Static JSX | `eslint-plugin-jsx-a11y` strict | `lint:ci --max-warnings=0` |
| Runtime | `@axe-core/playwright` | `test:a11y` on critical paths |
| Manual | Keyboard-only pass | PR checklist |

See `enforcement-rules.md` for the Playwright axe template and `enforcement.md` for the GitHub Actions workflow.

## Toasts / live regions

Transient messages must not steal focus or rely on color alone.

| Rule | Practice |
|---|---|
| `aria-live` | Prefer `polite` for success/info; `assertive` only for critical errors |
| Focus | Do not move focus into the toast on open (unless error requires it) |
| Dual channel | Icon **and** text; never color-only |
| Motion | Respect `prefers-reduced-motion` (no slide spam) |
| Duration | Errors longer / dismissible; don't auto-hide critical failures |

```tsx
// shadcn/sonner-style: role="status" aria-live="polite" on viewport
// Ensure toast content is a full sentence, not icon-only
```

## Anti-patterns

- Accessibility overlay widgets (AccessiBe, etc.) - legal and technical failure mode
- Placeholder as label
- `div onClick` instead of `<button>`
- Removing focus rings for aesthetics
- Disabled submit with no explanation
- Auto-advancing carousels without pause control
- `user-scalable=no` / `maximum-scale=1`
- Toast that steals focus mid-form

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
