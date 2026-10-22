# Design taste: distinctive UI, not token-compliant slop

**Last verified**: 2026-10-22 · **Review cadence**: 2 months
**Related**: `design-system.md`, `design-patterns.md`, `design-motion.md`, `conversion-ui.md`, `frontend.md`, `output-quality.md`

Tokens, WCAG, and shadcn wrappers can still produce a page that looks like every other 2026 AI app. This module is the aesthetic contract. Load it for new UI, landings, redesigns, "make it look good," and audits that mention generic / slop / taste.

Compose `unmachined` on the finished surface. If `hallmark` or `frontend-design` is installed and the task is a greenfield page or visual identity, they may own the exploration pass; Engineer still owns tokens, a11y, RSC, and ship gates.

## Contents
- [What taste is](#what-taste-is)
- [Before pixels](#before-pixels)
- [Default clusters (do not emit)](#default-clusters-do-not-emit)
- [Measured tells (2026)](#measured-tells-2026)
- [Structure is a choice](#structure-is-a-choice)
- [Type, color, copy](#type-color-copy)
- [States and craft](#states-and-craft)
- [Restraint](#restraint)
- [Pre-ship taste check](#pre-ship-taste-check)
- [Anti-patterns](#anti-patterns)

## Before pixels

Project truth first (`project-detect.md`). If `globals.css`, `DESIGN.md`, or brand tokens exist, **keep them**. Taste work is inside the product system, not a second palette.

Then state, in one short block, before writing JSX:

| Axis | Required |
|---|---|
| Subject | What this product/page actually is |
| Audience | Who is looking |
| Job | One action or understanding |
| Tone | A real extreme (editorial, brutalist, utilitarian, luxury, playful, technical, austere) — never "clean and modern" |
| Signature | One memorable element justified by the subject |

If the brief is silent, infer from the product and **say the inference**. Do not stall behind a questionnaire on routine component work. Ask once only on a true greenfield with no tokens and no brand.

Spend boldness in **one** place. Everything else stays quiet.

## What taste is

Taste is a **chosen default**, not a mood. Dieter Rams: useful, understandable, unobtrusive, honest, thorough, as little design as possible — aesthetic quality is part of usefulness ([Vitsœ](https://www.vitsoe.com/us/about/good-design)). Hierarchy is contrast, scale, and grouping (NN/g).

In 2026 the failure mode is the **LLM median**: polished, coherent, interchangeable. Krebs scored 1,590 Show HN pages (April 2026): 22% hit 4+ of 16 AI patterns, 32% hit 2–3, 46% hit 0–1. Slop converts; it does not distinguish. Ship ugly on purpose before you ship accidental shadcn.

Trends (3D, collage, neo-brutalism, "imperfect by design," tactile grain) are **not** taste if you picked them because they are trending. Same rule as Inter.

## Default clusters (do not emit)

These are legitimate for some briefs. They are not choices. Do not emit them unless the user named that look:

1. Warm cream paper + high-contrast serif display + terracotta accent
2. Near-black canvas + one acid-green or vermilion accent + glow
3. Broadsheet: hairline rules, zero radius, dense newspaper columns
4. Default shadcn: indigo/violet primary, Inter or Geist everywhere, 0.5rem radius, three equal feature cards
5. Purple-to-cyan hero gradient, glassmorphism cards, centered badge-above-H1

Also refuse as unconsidered defaults: Inter/Roboto/Poppins/Geist as the whole type system; Space Grotesk + Instrument Serif + Fraunces as a "distinctive" combo used for any subject; gradient-clipped headlines; fake browser/phone chrome; numbered `01 / 02 / 03` section kickers; italic display headings.

If a design plan would look the same for a bakery, a bank, and a GPU dashboard, it failed.

## Measured tells (2026)

Do not emit these unless the brief names them. Highest-signal extras beyond the five clusters:

| Tell | Why |
|---|---|
| Colored left or top stripe on rounded cards | A designer Krebs quotes: almost as reliable a tell as em-dashes in text |
| Icon tile (rounded square) stacked above a heading | Universal feature-card template |
| Hero metric: big number + tiny label + three supporting stats | Trusted nowhere; invents proof |
| Permanent dark theme as the only mode, grey body, all-caps labels | One of Krebs's 16 patterns |
| Nested cards, or hairline border **plus** a wide soft shadow | Cardocalypse / generated elevation |
| Card radius ≥24px on small cards | Everything becomes the same blob |
| Radial/spotlight glow, decorative grid, pulsing status dot, logo marquee | Motion or texture without a job |
| Lucide/emoji as the whole icon system on a marketing hero | Decoration larger than the message |
| "Supercharge / empower / streamline / world-class" | Copy slop riding visual slop |

Clean pages in the same dataset (Developers Digest's write-up): a palette that is not the default "VibeCode purple"; a type system that is not Inter-only; **one layout primitive repeated** until it is the signature.

Sources: [Krebs](https://www.adriankrebs.ch/blog/design-slop/), [Developers Digest](https://www.developersdigest.tech/blog/ai-design-slop-and-how-to-spot-it), [Impeccable slop](https://impeccable.style/slop). Notes: `research/design-taste-2026-08.md`.

## Structure is a choice

Do not default to Hero → 3 icon cards → logo strip → CTA → footer.

Pick a structure that fits the job:

- Workbench / app-first (the product is the hero)
- Document / editorial (reading is the job)
- Stat-led only when the numbers are real
- One long column when the argument is sequential
- Dense tool UI when the user is already inside the product

Marketing pages still need one primary action (`conversion-ui.md`). They do not need the same six-section skeleton. Numbered markers only when order carries information.

## Type, color, copy

**Type.** Pair display + body before code. Display is used with restraint; body carries the product. Data/captions may get a third utility face. Self-host via `next/font`. Body ≥16px. `text-wrap: balance` on headings. Italic is for body emphasis, not H1.

**Color.** One chromatic accent, small footprint. Neutrals are OKLCH-tinted, never pure `#000`/`#fff`. Status colors are for status. Accent ≤5% of a marketing viewport. Contrast is proven on semantic pairs (`design-accessibility.md`).

**Copy is design material.** Name controls by what the user does, not the system. "Save changes," not "Submit." Same verb through button → toast. Empty and error states give a next action. Say it once — no label + sublabel + helper restating the same line. Do not invent metrics, customer counts, or testimonials; use real figures, an honest placeholder, or a different layout. Do not lean on em-dashes as cadence.

**Content realism (demo/sample content).** Generation tells in draft content read as unfinished: no Lorem Ipsum (write real draft copy), no "John Doe" (diverse realistic names, unique avatars, varied dates), no placeholder brands ("Acme Corp", "Nexus", "SmartFlow" — invent contextual, believable names), no suspiciously round numbers in demo data (`50%`, `$100.00` — organic figures like `47.2%` read real). Sentence case headers, not Title Case Everywhere. This governs demo/sample surfaces only — marketing **proof** stays under the honesty rule above: real or labeled placeholder, never fabricated data dressed as organic.

## States and craft

Interactive controls need default, hover, `:focus-visible`, active, disabled, plus loading/error/success when the control can enter those states. Focus rings are instant and visible. Motion: transform/opacity only, honor `prefers-reduced-motion` (`design-motion.md`).

Prefer hairline borders over heavy shadows. No glow, frost, or mesh gradient unless the signature requires it and the rest of the page is quieter.

Images: real product, subject-matter photography, or honest placeholders. No stock "team at laptop," no generated faces as social proof, no Lottie where CSS would do.

## Restraint

Remove one accessory before ship (an adage often credited to Chanel, without evidence). If the signature is the type pairing, do not also add grain, glow, and a marquee. Maximalist briefs need execution density; minimal briefs need spacing and type precision. Both fail when every section shouts.

Match existing product chrome on interior app pages. A dashboard that suddenly becomes a poster is not taste; it is a broken system.

## Pre-ship taste check

Every new or redesigned UI surface, before calling it done:

1. Name subject, job, tone, and signature in the work notes.
2. None of the five default clusters unless the brief named them.
3. Structure would not fit an unrelated product without edits.
4. Type pairing is loaded and used; Inter/Geist are not the whole system unless the product already locked them.
5. No hardcoded `bg-indigo-*`, `bg-violet-*`, `bg-gradient-to-*`, gradient text, or colored side-stripe cards.
6. Copy has no invented proof, no "Build the future," and no hero-metric theater.
7. Interactive states exist; focus is visible; reduced-motion is respected.
8. Mobile 320/375: no root overflow, primary CTA reachable, no two-line buttons.
9. `unmachined` UI scan when installed; disclose if it did not run.
10. Browser-verify the affected flow (`browser-qa.md`).

## Anti-patterns

- Shipping shadcn defaults and calling it a design system
- Three equal-weight cards with lucide icons and two lines of copy
- Colored left-border cards and stacked icon-tiles
- Badge chip above a centered H1 on every landing
- Chasing 2026 trend lists (brutalism, collage, 3D, grain) without a subject reason
- Sidebar emoji nav on a serious product
- All-caps mono section labels as decoration
- Rewriting an existing product's tokens to chase a mood
- Asking the user for a 20-option theme catalog on a one-component task

Research: `research/design-taste-2026-08.md`. Do not bulk-load.
