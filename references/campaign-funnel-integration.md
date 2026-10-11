# Campaign overlays on existing acquisition funnels

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Use this reference when a campaign, limited trial cohort, giveaway, waitlist, partner push, or social CTA needs to enter an existing product funnel.

## Governing rule

Inspect the live route and repository implementation before proposing a new landing page, form, terms URL, or backend. Treat the canonical evergreen funnel as the default destination. A temporary campaign should usually be attribution plus presentation layered onto that funnel, not a duplicate funnel.

Never present a proposed route as if it exists. Label planned URLs explicitly and verify they resolve before outbound copy uses them.

## Decision sequence

1. **Map the existing funnel.** Trace public route, CTA builder, signup/login, auth callback, post-auth destination, qualification form, CRM write, activation event, conversion event, and operator view.
2. **Separate product from campaign.** Document what is evergreen product behavior versus temporary campaign rules, cohort size, deadline, or source.
3. **Prefer an overlay.** Reuse the canonical route, form, CRM opportunity, grant process, and activation instrumentation. Add a subroute only when campaign-specific legal or content requirements cannot fit cleanly. Do not create a second site for a different headline.
4. **Preserve request-time attribution.** Carry an allowlisted, bounded campaign context through every transition: marketing CTA, signup, login/signup switching, OAuth callback, safe `next` path, authenticated request, CRM evidence, and downstream metrics.
5. **Handle returning users.** Do not assume account `last_touch` is mutable. Inspect its write semantics. Preserve request-time campaign evidence separately and use account first-touch only as a fallback.
6. **Keep attribution non-authoritative.** UTM and campaign values are untrusted metadata. Bound length, strip unknown keys, normalize flags, and never let campaign fields grant access, alter billing, or change authorization.
7. **Collect qualification evidence that changes operations.** For infrastructure trials this can include workload, deployment region, current provider, benchmark goal, integration timing, and buying authority. Use bounded fields and prohibit secrets.
8. **Reuse storage before migrating.** If typed CRM evidence, bounded flags, and immutable activity detail can support the workflow, avoid a database migration. Add dedicated columns only when querying, integrity, or lifecycle pressure justifies them.
9. **Measure the whole cohort.** At minimum group requested, granted, activated, and paid by acquisition source and campaign. Vanity engagement is secondary.
10. **Keep old records readable.** Parsers must tolerate legacy evidence shapes and missing campaign fields. When extracting a narrow attribution subset from a broader stored object, strip unknown keys rather than rejecting otherwise valid source/campaign data.

## Static Next.js marketing routes

Reading `searchParams` in an App Router page can turn a static route dynamic. When the marketing app must stay prerendered:

- keep the page server-rendered and static;
- put `useSearchParams()` inside a minimal client CTA component;
- wrap it in `Suspense` with the ordinary unattributed CTA as fallback;
- copy only approved UTM keys;
- place the original campaign in a same-origin, validated post-auth `next` destination;
- verify the production build still marks the route as static.

## Auth continuity

Auth mode switches are a common attribution leak. Build one helper that:

- accepts only `/login` or `/signup` as destinations;
- validates `next` as a same-origin relative path;
- preserves only allowlisted `ft_*`, `utm_*`, referral, and destination values;
- bounds every value;
- drops email, tokens, arbitrary query keys, and external destinations;
- recognizes trial intent by pathname even when `next` contains a query string.

## CRM and metrics pattern

- Keep the existing CRM source that identifies the workflow.
- Add normalized campaign/source flags for filtering.
- Store the full bounded request attribution in immutable activity detail.
- Prefer request-time campaign flags, then fall back to account first-touch.
- Derive campaign summaries from the same lifecycle facts used for the main funnel.
- Show region and campaign in the operator queue so the added data changes decisions.

## Verification contract

Run and report:

1. URL-helper unit tests for allowlisting, bounds, and safe destinations.
2. Schema tests for qualification fields and legacy evidence parsing.
3. CRM patch tests for flag caps and non-authoritative behavior.
4. Metrics tests for requested, granted, activated, and paid grouping.
5. Type checks and lint for every touched app.
6. Production builds, including proof that static routes remain static.
7. Desktop and mobile Playwright flows for marketing CTA, auth switching, form submission, operator visibility, overflow, and Axe.
8. `git diff --check` and a scoped secret scan.

When a package script unexpectedly expands to unrelated Playwright files, do not treat the entire noisy run as focused evidence. Fix any relevant failure, then rerun the exact spec with the package-local executor, for example:

```bash
pnpm --filter <package> exec playwright test e2e/<focused-spec>.spec.ts
```

Horizontally scrollable metric tables must be keyboard-focusable and named, for example with `role="region"`, an `aria-label`, and `tabIndex={0}`.

## Pitfalls

- Inventing `/campaign-name` before inspecting `/trial`, `/signup`, or the CRM flow.
- Calling a vetted trial application a random giveaway and then adding unnecessary contest infrastructure.
- Preserving UTMs for new signups but dropping them when an existing user switches to sign-in.
- Treating a write-once `last_touch` field as current request attribution.
- Making a static marketing route dynamic only to read query parameters.
- Storing free-form UTM values as authoritative access controls.
- Adding campaign data that never appears in operations or conversion metrics.
- Breaking legacy CRM rows by requiring a new line or nested property in every old record.
