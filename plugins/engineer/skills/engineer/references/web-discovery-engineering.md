# Web discovery engineering: SEO, SEA, and AI answers

**Last verified**: 2026-10-22 · **Review cadence**: 2 months (crawler user agents and ad-crawler guidance drift; recheck those first)
**Related**: `seo-metadata.md`, `product-marketing.md`, `product-analytics.md`, `compliance-privacy.md`, `output-quality.md`

Load this module for organic search, paid search landing systems, AI answer discovery, crawler
policy, or a combined acquisition audit. It implements a supplied product position and campaign
brief. It does not invent keyword demand, proof, budgets, or legal consent.

## Contents
- [Status map: do not confuse standards and experiments](#status-map-do-not-confuse-standards-and-experiments)
- [Discovery architecture](#discovery-architecture)
- [Technical SEO and crawl controls](#technical-seo-and-crawl-controls)
- [AI and LLM discovery](#ai-and-llm-discovery)
- [Content quality and anti-slop](#content-quality-and-anti-slop)
- [SEA and paid-search engineering](#sea-and-paid-search-engineering)
- [Measurement contract](#measurement-contract)
- [Ship gate](#ship-gate)

## Status map: do not confuse standards and experiments

| Mechanism | Status | What engineer may claim |
|---|---|---|
| `/robots.txt` | IETF Standards Track, RFC 9309 | Cooperative crawl control, never authorization or secrecy |
| robots meta / `X-Robots-Tag` | Search-engine directives | Page/resource indexing and preview controls when the bot can crawl them |
| XML/text/RSS sitemap | Widely supported protocol | Discovery hint for canonical indexable URLs, never an indexing guarantee |
| `rel=canonical` | Search-engine-supported hint | Preferred duplicate URL, not an access control and does not ensure selection |
| Schema.org JSON-LD | Shared vocabulary | Machine-readable facts; rich-result eligibility depends on engine-specific support and policy |
| IndexNow | Participating-engine protocol | Change notification for added, updated, or deleted URLs, not a Google indexing control |
| `/llms.txt` | Community proposal (v2, Aug 2026) | Optional curated navigation aid; not RFC/W3C, access control, crawler permission, or ranking signal |
| AI-answer optimization | Ordinary crawl/index/quality systems plus engine controls | No secret AI schema, assured citation, or universal crawler switch |

## Discovery architecture

Build from one canonical product-fact source:

```text
facts/proof → visible page + metadata + JSON-LD + docs → sitemap
            → optional llms.txt index
            → organic/AI/paid landing variants with the same claims
            → query/click → consent-aware events → activation/revenue evidence
```

Every derivative must link to or be generated from the same factual source. A crawler-only claim,
hidden keyword block, or richer schema value than the visible page is drift or cloaking risk.

## Technical SEO and crawl controls

- Serve stable crawlable `https` URLs with ordinary `<a href>` links and useful server-rendered HTML.
- Maintain one self-consistent canonical URL across HTML, redirects, sitemap, hreflang, structured data,
  Open Graph, and internal links. Do not canonicalize every filtered or paginated page blindly.
- Return accurate status codes: `200` for content, permanent redirects for durable moves, `404` or
  `410` for gone content, and `5xx` only for temporary server failure. Do not soft-404.
- Keep indexable content and required CSS/JS crawlable. `robots.txt` blocking does not remove an
  already known URL; use `noindex` while allowing the crawler to read it.
- Generate sitemaps from canonical publish state. Include only URLs intended for indexing, use
  absolute URLs, honest significant `<lastmod>`, and split above 50,000 URLs or 50 MB uncompressed.
  Google ignores sitemap `priority` and `changefreq`.
- Treat faceted navigation, internal search, tracking parameters, calendars, and infinite spaces as
  crawl-budget risks. Prefer finite linked taxonomies and explicit parameter/canonical policy.
- Validate mobile-rendered content, headings, links, metadata, hreflang return links, structured
  data, Core Web Vitals field data, server logs, and Search Console/Bing Webmaster evidence.

`robots.txt` is public and cooperative. Never list secret paths assuming they become protected.
Authorization, tenant isolation, rate limiting, and WAF policy remain server controls.

## AI and LLM discovery

Separate crawler purposes instead of using "AI bot" as one category:

- search/retrieval crawlers that may surface links, summaries, or citations;
- training crawlers governed by their own user agent and publisher policy;
- user-triggered fetchers acting for a request;
- advertising landing-page validators such as OpenAI's `OAI-AdsBot`;
- unknown agents, which receive normal public access controls and rate limits.

As of this review, OpenAI documents `OAI-SearchBot` for ChatGPT search discovery, `GPTBot` for
potential training controls, and `OAI-AdsBot` for ad landing-page readiness. Keep their rules
separate. Verify current official user agents and published IP ranges before changing production
WAF rules; a user-agent string alone is spoofable.

Google's AI Overviews and AI Mode use normal Search eligibility and preview controls. There is no
special Google AI schema requirement. `nosnippet`, `max-snippet`, `data-nosnippet`, and `noindex`
affect eligible Search presentations according to Google's current documentation; test the exact
surface before promising behavior.

### Optional `llms.txt`

Publish it only when it reduces navigation cost for public, authoritative material:

```markdown
# Product name

> One factual sentence describing the product and intended user.

## Documentation
- [Quickstart](https://example.com/docs/quickstart): Supported setup and prerequisites.
- [API reference](https://example.com/docs/api): Versioned public contract.

## Product facts
- [Pricing](https://example.com/pricing): Current plans and limits.
- [Security](https://example.com/security): Dated controls and scope.

## Optional
- [Changelog](https://example.com/changelog): Product changes by date.
```

Rules:

- derive it from canonical public facts; use absolute canonical links and short factual descriptions;
- never include secrets, hidden endpoints, private docs, prompt instructions, unsupported claims,
  keyword blocks, or content different from what humans can open;
- return plain UTF-8 Markdown at `/llms.txt` (v2 also allows path-scoped files such as
  `/docs/llms.txt`; the most specific applies); monitor access logs before claiming adoption or value;
- do not use it instead of `robots.txt`, sitemaps, metadata, internal links, or accessible HTML;
- treat `llms-full.txt` and vendor extensions as optional experiments with owners and removal criteria.

## Content quality and anti-slop

- Satisfy a real query/job with first-hand evidence, dated facts, limitations, authorship, and clear
  update ownership. Use unmachined on every public page.
- AI assistance is not itself the failure. Google treats scaled low-value content made primarily to
  manipulate rankings as abuse regardless of how it was produced.
- Reject doorway/location permutations, scraped or lightly rewritten pages, site-reputation rental,
  fake comparison/review pages, fabricated experience, hidden text, and schema beyond visible truth.
- Programmatic pages need unique data, a defensible user task, index eligibility gates, finite
  inventory, editorial sampling, duplicate detection, and automatic deindex/retirement rules.

## SEA and paid-search engineering

SEA is a paid acquisition system, not a synonym for adding pixels:

1. Bind campaign/ad group/query intent to one canonical landing job and offer.
2. Keep ad, keyword, landing headline, proof, price, eligibility, and CTA materially consistent.
3. Make landing pages fast, mobile-usable, accessible, crawlable to the platform's declared ad
   validator, and free of cloaking, forced redirects, deceptive scarcity, or surprise data capture.
4. Preserve permitted click IDs and UTMs through same-site redirects without putting PII, tokens,
   consent choices, or private state into URLs. Canonical tags normally exclude tracking parameters.
5. Define primary conversions by business outcome; keep diagnostic micro-events secondary.
6. Send value, currency, timestamp, stable transaction/order ID, and deterministic deduplication.
   Separate platform conversion time from internal event time and reconcile both.
7. Set consent defaults before measurement commands, update on the interaction page, honor
   withdrawal, and distinguish basic from advanced consent behavior. Consent Mode is a signaling
   mechanism, not legal consent or a substitute for policy review.
8. Enhanced conversions or offline uploads use normalized, hashed first-party data only with a
   documented lawful basis, disclosure, minimization, access control, retention, and deletion path.
9. Test crawler access, redirect chains, click-ID retention, consent denied/granted/withdrawn,
   duplicate purchase retries, ad blockers, cross-domain flows, and server/browser discrepancies.

OpenAI's current advertiser guidance requires `OAI-AdsBot` access to submitted landing pages and
recommends `OAI-SearchBot`; verify WAF, CDN, bot challenge, auth, geo, JavaScript, and response-code
behavior without weakening the site's general security policy.

## Measurement contract

Report by source and landing cohort through activation and retained revenue:

| Surface | Operational evidence | Outcome evidence | Guardrail |
|---|---|---|---|
| Organic search | valid indexed pages, impressions, non-brand query coverage | activated/revenue cohorts | crawl waste, spam/manual actions |
| AI answers | verified crawler access, citations/referrals by engine | activated/revenue cohorts | unsupported answer/claim rate |
| Paid search | eligible ads, impression share, qualified clicks | conversion value, CAC, payback, retained ROAS | invalid traffic, consent loss, refund/churn |
| Content/docs | indexed useful pages, assisted journeys | activation and retained accounts | duplication, decay, factual drift |

Do not collapse zero-click visibility into sessions or assign unattributed revenue to AI. Store raw
referrer, UTM/click IDs, consent state, landing URL, and event time; compute attribution downstream.

## Ship gate

- standards-status labels are accurate and dated;
- robots, meta/X-Robots, canonical, sitemap, hreflang, status codes, rendered HTML, and JSON-LD agree;
- crawler and WAF rules are purpose-specific and tested without user-agent trust alone;
- `llms.txt`, if present, is public-fact-derived and treated as experimental;
- ad landing and conversion tests cover consent and retry/dedup behavior;
- Search Console, Bing/IndexNow, analytics, ad-platform, server-log, activation, and revenue evidence reconcile;
- unmachined, accessibility, performance, privacy, security, and browser QA gates pass.

---

Research: `../research/web-discovery-2026-07.md`. Reverify crawler names, AI presentation controls,
rich-result eligibility, ad measurement, and consent behavior before each production rollout.
