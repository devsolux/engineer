# CSP reporting research — 2026-07

## Decision

Add a small, framework-neutral CSP ingestion template and deterministic fixture. Do not add a hosted collector, database schema, dashboard, or queue by default. Existing observability can consume the normalized events; scale those components only after measured report volume justifies them.

## Current standards evidence

- CSP Level 3 is a W3C Working Draft. It defines enforced and Report-Only response headers, `report-to`, CSP violation reports, and recommends retaining deprecated `report-uri` alongside `report-to` for compatibility.
- Reporting API Level 1 defines `Reporting-Endpoints` and `application/reports+json` batches.
- Legacy `report-uri` payloads and Reporting API envelopes are similar but not identical, so an operational endpoint must parse both shapes.
- Reports can contain document, blocked, source and referrer URLs, original policy and script samples. These are untrusted and can contain sensitive query data or attacker-controlled strings.
- Next.js nonce CSP forces dynamic rendering, disables static optimization/ISR and is incompatible with Partial Prerendering. Nonces are therefore a security/performance architecture decision, not a header-only tweak.

## Resulting controls

- same-origin protected-document admission;
- 32 KiB body and 20-report batch defaults;
- content-type allowlist and rate-limit callback;
- origin-only URL normalization;
- directive/disposition/status allowlist;
- no raw body, full URL, sample, policy, IP, user agent, cookie or identity retention;
- best-effort 204 response so hostile reports cannot create reflection or retry amplification;
- Report-Only observation before enforcement, with an explicit promotion decision.

## Primary sources

- https://www.w3.org/TR/CSP/
- https://www.w3.org/TR/reporting-1/
- https://nextjs.org/docs/app/guides/content-security-policy
- https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/CSP
