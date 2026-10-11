# Visual communication and cross-surface assets

**Last verified**: 2026-08-19 · **Review cadence**: 2 months
**Related**: `design-system.md`, `design-taste.md`, `design-accessibility.md`, `product-marketing.md`,
`output-quality.md`, `seo-metadata.md`, `composition.md`
**Contents**: [Brief](#brief-before-pixels) · [Taxonomy](#infographic-and-diagram-taxonomy) · [Composition](#composition-system) · [Surfaces](#surface-contracts) · [Anti-slop](#anti-slop-and-creative-direction) · [Export/QA](#export-and-qa-receipt)

Use for infographics, editorial diagrams, blog and X Article images, YouTube thumbnails, watermarks, logos,
GitHub visuals, social cards, and channel/profile banners. Start from the message and viewing context, not a fashionable layout.

## Brief before pixels

Capture:

```yaml
surface: exact placement and platform
audience: who sees it and what they know
job: notice | understand | compare | remember | trust | act
one_message: one sentence the visual must communicate
evidence: facts, data, source, date, uncertainty
viewing_context: dimensions, crop variants, minimum rendered size, light/dark surroundings
brand: approved marks, tokens, type, voice, exclusions
action: what happens after comprehension
constraints: accessibility, rights, privacy, policy, localization, file size
measurement: comprehension, qualified watch/read, saves, activation, or recognition
```

If the message cannot be stated, do not decorate around the ambiguity. One asset may have one dominant
message and supporting detail; a campaign can distribute several messages across a system.

## Infographic and diagram taxonomy

Choose by the reader's task. An infographic is an output class, not a chart type.

| Reader task | Useful families | Common failure |
|---|---|---|
| Compare magnitude or rank | ranked bar, dot plot, proportional symbol, table | area/volume encodings that hide magnitude |
| Show change | line, slope, indexed series, small multiples, before/after | truncated or inconsistent axes |
| Show variation | histogram, strip/dot, box/violin, range, uncertainty interval | averages without distribution |
| Relate variables | scatter, bubble with caution, connected scatter, correlation matrix | implied causality |
| Decompose a whole | stacked/proportional bar, treemap, mosaic, limited pie/donut | too many parts or incomparable angles |
| Locate | locator, choropleth, proportional-symbol map, route, floor/site map | population or area bias and missing legend |
| Order events and duration | timeline, Gantt/Priestley, event sequence, calendar heatmap | decorative chronology with no scale |
| Explain flow or sequence | process, flowchart, lifecycle, funnel, swimlane, decision tree | crossing arrows and undefined states |
| Map dependencies | system map, network, Sankey/alluvial, causal diagram, dependency graph | hairball density or unproved causality |
| Reveal hierarchy or anatomy | hierarchy tree, org chart, taxonomy, anatomy, exploded/cutaway view | nesting that implies a false hierarchy |
| Compare options | comparison matrix, quadrant, spectrum, scorecard, side-by-side teardown | hidden weights or false precision |
| Teach a procedure | annotated steps, checklist, recipe, field guide, decision aid | too many steps in one panel |
| Present an argument | evidence card, annotated screenshot, quote/stat card, narrative sequence | illustration presented as evidence |
| Explain construction | blueprint, schematic, exploded view, wiring/topology map, dimensioned technical plate | decorative engineering language with false dimensions |
| Record observation | field notes, lab/notebook page, case log, annotated specimen, contact sheet, evidence dossier | invented handwriting, timestamps, measurements, or provenance |
| Support retrieval | field guide, cheat sheet, runbook card, playbook, reference plate, troubleshooting tree | dense poster with no retrieval hierarchy |

Compound infographics may combine families only when reading order and scale remain clear. Split a
poster into a sequence when the reader must zoom or remember one panel to decode another.

### Editorial-technical forms

- **Blueprint:** use when spatial relationships, components, dimensions, interfaces, or assembly are
  the message. Distinguish measured geometry from conceptual topology; rulers, coordinates, revision
  stamps, and dimensions require real values.
- **Schematic:** simplify physical appearance to show functional connections, signal/data flow, or
  dependency. Include a symbol legend and boundary; crossings and arrow direction must be unambiguous.
- **Technical plate / exploded view:** identify parts and their relationships with stable callouts,
  ordered labels, scale disclosure, and a parts list where useful. Illustration cannot silently stand
  in for verified product geometry.
- **Field notes / notebook:** organize observations, evidence snippets, annotations, hypotheses, and
  unresolved questions around a real investigation. Handwriting, tape, coffee stains, timestamps,
  coordinates, specimen numbers, and redactions are semantic only when grounded; otherwise they are
  costume.
- **Evidence dossier / teardown:** connect each claim to a screenshot, quote, datum, code or artifact
  with provenance. Separate observation from inference and recommendation.
- **Field guide / reference plate:** optimize retrieval rather than narrative. Use stable categories,
  visual keys, recognition cues, compact rules, and a clear use/avoid boundary.
- **Runbook / playbook card:** encode trigger, prerequisites, ordered action, decision branches,
  verification, rollback, escalation, and owner. A checklist without stop conditions is incomplete.
- **Contact sheet / pattern atlas:** compare variants under identical crop, scale, labels, and context;
  use it for selection and critique rather than pretending visual volume is evidence of quality.

Editorial styling must follow content truth. Blueprint blue, graph paper, mono labels, rough arrows,
redaction bars, stamps, and marginalia are not a default technical aesthetic.

## Composition system

1. Write the takeaway and choose the evidence before selecting a form.
2. Establish one entry point, one reading path, and one visual climax. Use position, scale, contrast,
   isolation, and whitespace before adding color or ornament.
3. Use a grid and alignment logic, but break it once when that break carries meaning. Avoid symmetric
   three-card symmetry and identical modular panels by reflex.
4. Encode each variable with the most perceptually direct channel available: position and length
   before area, angle, volume, texture, or decorative illustration.
5. Label data directly where possible. Include units, denominators, time range, source, date,
   definitions, uncertainty, missing data, and material transformations.
6. Keep typography to two main families plus an optional utility/mono role. Test the final rendered
   size, not only the master canvas. Keep body-length copy as selectable text.
7. Color has a job: hierarchy, category, sequence, status, or emphasis. Hue cannot be the only
   carrier of meaning. Reserve brand accent for the intended focal point.
8. Remove every object that does not improve comprehension, recognition, emotional tone, or action.
   Beauty means the form makes the intended reading feel inevitable, not that it has more effects.

## Surface contracts

Platform dimensions drift. Verify current official documentation before export; keep a dated source
in the asset manifest. Master files are not delivery files.

### X Articles and blog posts

- The cover earns the open: one topic signal, one tension or mechanism, and a composition readable as
  a small card. Duplicate the full title only when the distribution surface needs it.
- Inline visuals must advance the argument: system map, evidence chart, annotated example, comparison,
  sequence, or reusable field guide. Decorative stock art does not count.
- Place a visual at a conceptual turn, not every fixed word count. Introduce it in prose, state the
  takeaway, and provide a complete text equivalent for complex information.
- X Article production composes with a content-pipeline skill (if installed), which owns composer formatting, cover/inline
  packaging, article gates, and launch assets. Engineer owns factual visual logic, accessibility,
  provenance, engineering, and reusable asset systems.
- Blog delivery uses responsive `<picture>`/`srcset`, explicit dimensions, art-directed crops where
  needed, modern compressed raster formats, and SVG only from a trusted sanitized pipeline.

### YouTube thumbnails

- Treat title and thumbnail as one promise. The image creates recognition or a question; the title
  supplies missing specificity. Avoid repeating the same sentence twice.
- One focal subject, one conflict or transformation, strong figure-ground separation, and minimal
  text. Verify at the smallest feed size, in light and dark contexts, and with the duration badge zone.
- No fabricated expressions, outcomes, UI, money, people, or scale. Curiosity cannot contradict the
  video. Optimize qualified watch time and satisfaction, not clicks alone.
- Current official guidance recommends 16:9 and high resolution. Use YouTube's native concurrent test
  for up to three materially different title/thumbnail variants when eligible; judge by watch-time
  share, record inconclusive results, and avoid sequential-test certainty.

### Logos and identity marks

- Begin with category, audience, name, pronunciation, brand attributes, competitors, trademark search
  boundary, and real placements. Distinctiveness and recognition outrank visual cleverness.
- Deliver a system: primary lockup, wordmark, symbol, horizontal/stacked variants, monochrome,
  light/dark, small-size simplification, favicon/avatar, clear space, minimum size, misuse examples,
  color/type tokens, and editable vector source.
- Test silhouette, one color, 16-32px, blur, grayscale, embroidery/print constraints, unfamiliar
  viewers, and collision against category competitors. Font-plus-random-icon output is not a
  a finished identity.
- Aesthetic generation is not legal clearance. Record authorship, asset/font licenses, source files,
  and the jurisdiction-specific trademark review owner.

### Watermarks and provenance

- Choose the actual purpose: attribution, subscription affordance, leak tracing, authenticity signal,
  or deterrence. A visible watermark does not prove ownership or prevent copying.
- Keep branding marks recognizable but subordinate to the content; test busy/light/dark scenes,
  crops, captions, mobile viewing, and compression. Never obscure evidence or accessibility-critical
  content.
- For traceable provenance, consider signed Content Credentials/C2PA and durable bindings. State what
  the mechanism proves and does not prove. Invisible watermarking has false-positive, removal,
  privacy, and interoperability risks; do not deploy it silently for user tracking.

### X, GitHub, and channel banners

- Design the crop system first. Keep identity and message in the intersection of safe regions; let
  edge artwork tolerate cropping. Preview desktop, mobile, high-DPI, light/dark surroundings, and
  profile-avatar overlap.
- X currently recommends 1500x500 and warns that top/bottom cropping varies. Treat the central band as
  the robust message zone and verify on live surfaces.
- GitHub has no native personal profile banner. A profile README header is content, while repository
  social preview is platform metadata. GitHub currently recommends 1280x640 for best social preview,
  under 1 MB, with solid-background fallback when transparency may fail.
- YouTube currently recommends 2560x1440, with a central text/logo safe region, because the same banner
  crops differently on TV, desktop, and mobile. Never stretch an X header into this canvas.

## Anti-slop and creative direction

- Reject automatic purple gradients, generic glowing brains, circuit heads, stock rocket imagery,
  glass cards, fake browser chrome, tiny all-caps labels, random 3D blobs, and a centered title over an
  unrelated cinematic scene.
- Technical topics do not automatically require dark, neon, isometric, or blueprint-like styling. Derive material,
  texture, geometry, photographic treatment, illustration language, and density from the subject.
- Define one signature device per asset family, then vary framing, crop, scale, rhythm, and visual
  metaphor. Consistency is shared grammar, not duplicated composition.
- Use generated imagery only with a factual brief, rights/provenance decision, and manual inspection
  for text, hands, symbols, topology, brands, cultural errors, and unintended claims.

## Export and QA receipt

For each asset record source, owner, license, evidence date, master dimensions, delivery variants,
crop/safe zones, color profile, fonts, alt/long description, checksum, and approval status.

Before ship:

- factual and source review;
- comprehension test without surrounding copy;
- thumbnail/minimum-size and blur test;
- crop/occlusion previews for every declared surface;
- contrast, color-blind, alt text, and complex-image equivalent;
- spelling, number, unit, axis, legend, and logo-permission review;
- raster/vector security and metadata/privacy review;
- file-size, compression, transparency, and dark/light-background checks;
- one native preview or rendered-browser capture;
- measurement plan tied to the asset's job, with guardrails against clickbait or vanity metrics.

**Research basis**: `../research/visual-communication-assets-2026-07.md`
