# Design, aesthetic, and taste — 2026-08 research note

**As-of**: 2026-08-19 · Loaded only from `design-taste.md`

Taste in product UI is not a trend catalog. It is a **deliberate choice against a known default**, plus craft (hierarchy, contrast, states) so the choice is usable.

## What "taste" means (stable)

Dieter Rams ([Vitsœ](https://www.vitsoe.com/us/about/good-design)): useful, understandable, unobtrusive, honest, thorough, as little design as possible. Aesthetic quality is part of usefulness, not decoration.

NN/g visual hierarchy: importance is encoded by **contrast, scale, and grouping**. A page with no hierarchy is not "minimal"; it is unread.

2026 product writing (Krebs, Impeccable, Unslop UI): slop is **mass-produced default**, not "ugly." An ugly page with a point of view outperforms a polished page with none. Bootstrap was the pre-LLM version of this.

## Measured AI visual defaults (2026)

Adrian Krebs scored **1,590 Show HN** landings with Playwright DOM/CSS checks ([essay](https://www.adriankrebs.ch/blog/design-slop/), [write-up](https://www.developersdigest.tech/blog/ai-design-slop-and-how-to-spot-it)):

| Bucket | Share |
|---|---|
| Heavy (4+ of 16 patterns) | 22% |
| Mild (2–3) | 32% |
| Clean (0–1) | 46% |

Most common single tells: **permanent dark theme (34%)**, **gradient backgrounds (27%)**, **icon-card grids (22%)**.

The 16 patterns: Inter-everywhere; Space Grotesk / Instrument Serif / Geist combos; italic serif accent word; "VibeCode" lavender-purple; perma-dark + grey body + all-caps labels; failing dark-theme contrast; gradients; colored glows; centered generic-sans hero; **badge above H1**; **colored top/left card borders**; identical icon-top cards; numbered 1-2-3 steps; **stat banner rows**; emoji nav; all-caps section labels. CSS fingerprints: stock shadcn, glassmorphism.

Clean sites: a palette that is not lavender; a type system that is not Inter-only; **one layout primitive repeated** as the signature.

Impeccable's [slop catalog](https://impeccable.style/slop) adds craft tells: nested cards; hairline+wide-shadow; over-rounding; stacked icon-tiles; hero-metric (big number + 3 stats); radial/spotlight glow; cream-beige "tasteful" paper; redundant helper copy; SaaS buzzwords; em-dash cadence; marquees; pulsing dots; bounce easing; image-hover scale; decorative grids.

Unslop UI (Reddit, 2026-06, from 3.2M posts) ranks **complaint frequency**: shadcn defaults, indigo/violet, purple-blue gradients, unprompted neon, emoji-as-icon, Inter/Geist, hero+three-cards. It **does not** nag mesh/bento/glass unless people name them — still treat glass/glow as LLM defaults unless the brief asks.

## 2026 aesthetics (do not chase)

Figma's [2026 trend list](https://www.figma.com/resource-library/web-design-trends/) is inspiration, not a recipe: 3D/WebGL, experimental nav, dopamine color, kinetic type, dark mode, motion, gamification, neumorphism, retrofuturism, maximalism, collage, neo-brutalism, sustainable lean sites.

Counter-movements in 2026 design writing: "imperfect by design," tactile/grain/CSS texture, "tactile brutalism" (1px borders, no fake depth). Those are also **clusters**. Using them because they are trending is the same failure as Inter+indigo.

## What Engineer should do

Portable contract, not a theme catalog: name subject/job/tone/signature; refuse measured tells unless chosen; repeat one primitive; keep Rams-level restraint on app chrome; do not invent proof; do not chase the Figma list. Optional partners (`hallmark`, `frontend-design`) may explore; Engineer still owns tokens, a11y, RSC, and ship.
