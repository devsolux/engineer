# Visual communication, infographic, and channel-asset research

**Verified**: 2026-07-16

## Applied conclusions

The primary design decision is the reader's question and the evidence shape. Infographic families
cover quantitative comparison, change, distribution, relationship, part-to-whole, spatial and
uncertainty tasks plus explanatory sequence, process, system, hierarchy, anatomy, decision, and
instructional tasks. Editorial-technical forms add blueprints, schematics, exploded plates, field
notes, evidence dossiers, runbooks, field guides, contact sheets, and pattern atlases. Their visual
conventions must encode real construction, observation, provenance, or retrieval structure rather
than serve as technical-looking decoration. Asset surfaces then add crop, recognition, legibility, policy, and measurement
requirements. A universal beautiful-infographic template is therefore a category error.

The Financial Times Visual Vocabulary provides a task-based chart selection model. W3C guidance
requires text alternatives for complex images, discourages images of text outside essential cases,
and applies contrast to meaningful graphical objects. X confirms that Article header and inline
images support opening and skimmability. YouTube now recommends high-resolution 16:9 thumbnails and
offers concurrent A/B/C title/thumbnail testing decided by watch-time share rather than CTR alone.
Official X, GitHub, and YouTube documentation confirms that banner and preview assets have distinct
sizes and crop behavior. C2PA provides a provenance framework; visible or invisible watermarks alone
must not be described as authenticity proof.

## Safe GitHub implementation inputs

- Financial Times `chart-doctor` for a task-oriented visual vocabulary.
- Observable Plot for a concise layered grammar of graphics.
- Excalidraw for editable open-format diagrams; review current security releases before integrating
  Mermaid conversion because its release history includes an upstream Mermaid XSS mitigation.
- Kroki for self-hostable text-to-diagram formats when the supply chain, renderer versions, untrusted
  diagram input, network access, and SVG output are sandboxed and pinned.

These repositories are pattern and tooling candidates, not default dependencies. Admission still
requires license, maintenance, security, output, and task-fit review.

## Sources

- Financial Times, [Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md)
- Observable, [Plot](https://github.com/observablehq/plot)
- X, [About Articles](https://help.x.com/en/using-x/articles)
- X, [Profile header guidance](https://help.x.com/en/managing-your-account/common-issues-when-uploading-profile-photo)
- YouTube, [Custom thumbnails](https://support.google.com/youtube/answer/72431)
- YouTube, [A/B test titles and thumbnails](https://support.google.com/youtube/answer/16391400)
- YouTube, [Channel branding, banner, and watermark](https://support.google.com/youtube/answer/10456525)
- GitHub, [Repository social preview](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
- GitHub, [Profile README](https://docs.github.com/en/account-and-profile/concepts/personal-profile)
- W3C WAI, [Images tutorial](https://www.w3.org/WAI/tutorials/images/)
- W3C WAI, [Non-text contrast](https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast)
- MDN, [Responsive images](https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images)
- C2PA, [Specifications](https://spec.c2pa.org/specifications/specifications/2.2/index.html)
- WIPO, [Trademark distinctiveness](https://www.wipo.int/en/web/trademarks/protection)
- Excalidraw, [repository](https://github.com/excalidraw/excalidraw) and [security release](https://github.com/excalidraw/excalidraw/releases)
- Kroki, [repository](https://github.com/yuzutech/kroki)
