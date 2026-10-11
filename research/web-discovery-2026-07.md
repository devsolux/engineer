# Web discovery engineering research - 2026-07

## Scope

Current technical SEO, paid search/SEA implementation, AI answer discovery, crawler control,
structured data, sitemaps, IndexNow, `robots.txt`, and `llms.txt`. This research informs product
engineering; channel strategy and spend decisions remain outside engineer.

## Findings

### Standards and crawl/index controls

- RFC 9309 is the IETF Standards Track Robots Exclusion Protocol. It defines `/robots.txt` as
  UTF-8 `text/plain` at the service root and explicitly says it is not authorization.
- Robots meta and `X-Robots-Tag` are indexing/presentation controls only when the crawler can fetch
  them. Blocking a URL in robots can prevent a crawler from seeing `noindex`.
- Sitemaps are hints. Google supports XML, RSS/Atom, and text formats; one file is limited to 50 MB
  uncompressed or 50,000 URLs. Include canonical desired URLs and honest significant `lastmod`.
  Google says it ignores `priority` and `changefreq`.
- Structured data uses Schema.org vocabulary, but search features accept engine-specific subsets
  and policies. Markup must describe visible page truth and does not guarantee a rich result.
- IndexNow authenticates site control with a key and notifies participating engines about added,
  updated, or deleted URLs. It complements crawlable pages and sitemaps; it is not a Google control.

### AI and LLM discovery

- Google states that AI Overviews and AI Mode use normal Search eligibility. Current robots meta,
  `nosnippet`, `max-snippet`, and `data-nosnippet` controls extend to these presentations. Google
  does not document a special AI schema or `llms.txt` requirement.
- OpenAI separates `OAI-SearchBot` discovery from `GPTBot` training policy. Its July 2026 publisher
  FAQ says public sites can appear in ChatGPT search, recommends allowing OAI-SearchBot for
  summaries/citations, and notes `noindex` requires crawl access to be read.
- OpenAI's current advertiser guidance adds `OAI-AdsBot` for landing-page validation and recommends
  allowing OAI-SearchBot too. WAF/CDN challenge behavior can block these crawlers even when
  `robots.txt` allows them.
- `llms.txt` remains a community proposal from llmstxt.org, not an IETF RFC, W3C Recommendation,
  access-control mechanism, universal crawler directive, or proven ranking signal. Treat it as a
  low-cost derived navigation experiment and measure actual fetch/referral evidence.

### Quality, anti-slop, and programmatic publishing

Google's spam policies, updated May 2026, define scaled content abuse by purpose and user value,
not by whether AI generated the text. Doorways, scraping, hidden text, expired-domain abuse, thin
affiliation, and site-reputation abuse remain prohibited. Engineer therefore requires first-hand
evidence, unique user value, source/proof provenance, finite inventories, duplicate detection,
editorial sampling, lifecycle ownership, and unmachined output gates.

### SEA, landing systems, and measurement

- Google Ads uses the Google tag/event snippets or imported analytics events for web conversions.
- Auto-tagging adds GCLID; privacy-preserving GBRAID/WBRAID variants may appear. Redirect and URL
  handling must preserve permitted identifiers without leaking PII or private state.
- Consent Mode v2 includes `ad_storage`, `analytics_storage`, `ad_user_data`, and
  `ad_personalization`. Defaults must precede measurement commands and updates must occur when the
  user acts. Google distinguishes basic mode (no pre-consent transmission) from advanced mode
  (cookieless measurements while denied). This is implementation behavior, not legal advice.
- Enhanced conversions use normalized hashed first-party data. April 2026 Google Ads changes unify
  web and lead setup, but lawful basis, disclosure, minimization, retention, security, and deletion
  remain operator responsibilities.
- Engineering quality depends on business-result conversion definitions, stable transaction IDs,
  retry deduplication, value/currency correctness, consent-state tests, crawler access, and
  reconciliation through activation, refunds, retained revenue, CAC, and payback.

## Primary sources

- [RFC 9309: Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html)
- [Google Search: AI features and website controls](https://developers.google.com/search/docs/appearance/ai-features)
- [Google Search: robots meta and X-Robots-Tag](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)
- [Google Search: build and submit a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google Search: JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Google Search spam policies](https://developers.google.com/search/docs/essentials/spam-policies)
- [Google Search generative AI content guidance](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content)
- [OpenAI publisher and developer FAQ](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq)
- [OpenAI advertiser crawler guidance](https://help.openai.com/en/articles/20001243-advertiser-guidance-for-allowing-openai-web-crawlers)
- [llms.txt proposal](https://llmstxt.org/)
- [IndexNow protocol documentation](https://www.indexnow.org/documentation)
- [Google Consent Mode implementation](https://developers.google.com/tag-platform/security/guides/consent)
- [Google Ads enhanced conversions](https://support.google.com/google-ads/answer/15712870)
- [Google Ads GCLID definition](https://support.google.com/google-ads/answer/9744275)

## Refresh triggers

Recheck immediately when a major engine changes crawler user agents, AI-answer controls,
structured-data eligibility, ad landing validation, click identifiers, consent requirements, or
official support for `llms.txt`. Otherwise refresh monthly for crawler/ads policy and quarterly for
stable protocols.
