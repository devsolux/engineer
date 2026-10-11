# Mobile-web quality research

**Verified**: 2026-07-16 · **Review cadence**: 3 months

## Decision

Keep Engineer's existing mobile-first guidance and add one executable Playwright quality spec. A new
mobile module would duplicate `design-patterns.md`, `design-accessibility.md`, `frontend-testing.md`,
and `browser-qa.md` without improving enforcement.

The shipped gate checks public routes in an emulated iPhone profile and a 320 by 568 compact profile:

- `<meta name="viewport">` exists and uses `width=device-width`;
- `user-scalable=no` and `user-scalable=0` fail;
- a declared numeric `maximum-scale` below 2 fails;
- the document root does not horizontally overflow by more than one rounding pixel.

Document-level overflow is deliberately narrower than banning every horizontal scroller. Maps,
diagrams, code, data tables, and other content whose meaning requires two dimensions may use a
contained, labeled scroll region without forcing the entire page to pan.

## Evidence

- WCAG 2.2 Understanding 1.4.10 defines the reflow target for vertically scrolling content as 320
  CSS pixels and distinguishes content that genuinely requires two dimensions:
  https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- W3C ACT rule `b4f0c3` rejects viewport declarations with `user-scalable=no` or a valid
  `maximum-scale` below 2. Passing this automated rule still needs further conformance testing:
  https://www.w3.org/WAI/standards-guidelines/act/rules/b4f0c3/
- MDN documents `width=device-width`, the accessibility harm of disabled zoom, viewport-fit safe
  areas, and interactive-widget behavior:
  https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/viewport
- Playwright's stable emulation guide confirms that device profiles cover viewport, screen, user
  agent, touch, and mobile viewport behavior; overrides must follow the device spread:
  https://playwright.dev/docs/emulation

## Limits

An emulated pass is not a real-device pass. It cannot establish physical touch ergonomics, mobile
assistive-technology behavior, virtual-keyboard and browser-chrome resizing, safe-area correctness,
thermal or memory pressure, radio latency, or production performance. Release evidence still needs
representative iOS and Android hardware for material mobile journeys.
