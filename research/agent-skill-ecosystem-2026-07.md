# External agent-skill landscape review

**Reviewed**: 2026-07-15

## Decision

Engineer should learn from external sources without becoming a bundled marketplace. Keep core routing,
security, evidence, browser, product, and completion contracts native. Use external skills as narrow
knowledge adapters or specialist passes only after individual supply-chain admission.

## Sources and treatment

| Source | Distinct value | Trust note | Engineer decision |
|---|---|---|---|
| OpenAI skills | Historical Codex skill patterns | Repository now says it is deprecated in favor of OpenAI plugins; per-skill licenses vary | Do not use as a current catalog; follow current official plugin guidance |
| Anthropic skills | Production-shaped document skills and skill patterns | Some content is source-available rather than open source; repository requires local testing | Reference patterns and the installed skill-creator contract; no wholesale copy |
| NVIDIA skills | Publisher signatures, skill cards, eval datasets, benchmarks, scanning | Integrity and publisher identity do not prove task safety or benchmark relevance | Adopt the evidence signals; verify and reproduce before composition |
| Microsoft, MicrosoftDocs, Hugging Face | Product and SDK grounding from the owning organizations | Organization ownership is useful provenance, not blanket authorization | Prefer narrow adapters for matching products, checked against current official docs |
| Google Gemini skills | Gemini API and SDK patterns | Repository explicitly says it is not an officially supported Google product | Treat as organization-hosted reference, not supported-product authority |
| Trail of Bits skills | Deep security review and testing specialists | Executable marketplace with dependencies and powerful analysis surfaces | Admit individual plugins; compose bounded differential, defaults, property, mutation, and spec checks |
| JetBrains skills | Filtered snapshot with source links and automated scanning | Repository still says to test thoroughly; snapshot may lag upstream | Discovery and provenance aid only; review canonical upstream candidate |
| GitHub awesome-copilot | Broad community agents, skills, hooks, and workflows | GitHub warns that third-party content must be inspected before installation | Discovery corpus only; never trust or install in bulk |
| Vercel Labs skills CLI | Cross-agent discovery, prompt use, and installation | Distribution adds a CLI, registry resolution, update, and payload trust chain | Optional distribution tool only after exact-source selection; pin resolved payload |

## Capability inputs worth retaining

1. **Artifact-level governance**: identity, immutable revision, license, skill card, evaluation dataset,
   benchmark methodology, signature, scanner output, owner, expiry, and rollback are separate fields.
2. **Security verification specialists**: differential review, false-positive checking, insecure-default
   analysis, sharp-edge review, property-based testing, mutation testing, and spec-to-code comparison
   can add depth when the individual plugin is admitted and findings are locally reproduced.
3. **Product knowledge adapters**: use first-party skills for fast-changing vendor syntax and
   workflows, but resolve conflicts in favor of current official documentation and observed tools.
4. **Catalog non-transitivity**: curated, verified, signed, popular, or organization-hosted describes
   a signal. It never grants the payload authority, safe behavior, freshness, or fit.
5. **Distribution separation**: evaluate the installer, registry, canonical source, dependency graph,
   resolved revision, and installed tree independently. Never allow an implicit latest update.

## Rejected integrations

- No bulk catalog import, always-on marketplace search, or recursive partner activation.
- No duplicate native Engineer modules merely because another repository has a similarly named skill.
- No signature-only admission, benchmark-only promotion, or scanner-only safety claim.
- No external security worker receives exploit, credential, network, or production authority by
  virtue of being a security specialist.

## Primary sources

- https://github.com/openai/skills
- https://github.com/anthropics/skills
- https://github.com/NVIDIA/skills
- https://github.com/microsoft/skills
- https://github.com/MicrosoftDocs/Agent-Skills
- https://github.com/huggingface/skills
- https://github.com/google-gemini/gemini-skills
- https://github.com/trailofbits/skills
- https://github.com/JetBrains/skills
- https://github.com/github/awesome-copilot
- https://github.com/vercel-labs/skills
