# Secure package-backed HTML previews

**Last verified**: 2026-08-19 · **Review cadence**: 3 months
**Related**: `browser-qa.md`, `browser-agent-security.md`, `frontend-testing.md`

Use this pattern when a dashboard must preview article or document packages stored on disk without trusting package-authored HTML or scripts.

## Security boundary

1. Treat package Markdown, HTML, image paths, and metadata as untrusted content.
2. Resolve the requested package through the project's existing allowlist. Reject absolute paths, traversal, symlink escapes, and roots outside the approved package inventory.
3. Prefer Markdown or another structure-preserving source. Use packaged rich HTML only as a sanitized fallback.
4. Generate the review shell, controls, scripts, and CSP in trusted dashboard code. Never serve package-authored preview HTML directly in a same-origin frame.
5. Rewrite every local media reference through one allowlisted asset route. Do not expose `file://` URLs or general filesystem endpoints.
6. If trusted preview controls require JavaScript, run the document in an iframe with `sandbox="allow-scripts allow-popups"` and omit `allow-same-origin`. Keep the child at an opaque origin.
7. Probe the allowlist with an out-of-root path and require a blocked response before declaring the route safe.

## Rendering parity

- Use the richest safe source that preserves headings, figures, chapter separators, captions, tables, fenced code, and final CTAs.
- Discover cover variants and linked body families in trusted server code. Variant controls may swap only URLs admitted by the package asset route.
- Preserve a fixed feed-proof width when the publishing workflow depends on one. Verify the measured width in-browser.
- Keep code Copy behavior dashboard-owned. Do not preserve package scripts to retain controls.

## Responsive tables

A desktop comparison table with a large `min-width` can produce root-level mobile overflow even when wrapped in `overflow-x:auto`; Chromium may include scrollable descendants in `documentElement.scrollWidth`.

Preferred mobile repair:

1. Add escaped `data-label` values to each `td` from the source headers.
2. Keep the native table on desktop.
3. Below the mobile breakpoint, hide the visual `thead` and render each row as a labelled card using the `data-label` pseudo-element.
4. Constrain `html` and `body` to `max-width:100%` and `overflow-x:hidden` only after no mobile component requires root-level horizontal scrolling.
5. Verify that `documentElement.scrollWidth === clientWidth` at the real target viewport.

## Browser QA contract

Use explicit viewport setting rather than assuming constructor options were honored:

```js
const page = await browser.newPage();
await page.setViewportSize({ width: 390, height: 844 });
```

For each representative package at desktop and mobile widths, record:

- HTTP status and document title
- console and page errors
- failed images (`naturalWidth === 0`)
- root `scrollWidth` versus `clientWidth`
- cover count, linked-body count, code blocks, and tables
- exact feed-proof width when applicable
- screenshots of the top, first linked body graphic, and responsive table

A first successful run is not enough if the viewport dimensions are wrong. Assert the page's actual `clientWidth` before accepting mobile evidence. After any CSS or renderer repair, rerun unit tests, typecheck, scoped lint, and the full browser matrix.
