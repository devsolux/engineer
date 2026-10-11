---
description: Systematic product QA across behavior, responsive UI, accessibility, network, and critical flows.
---

# /engineer-qa

Load `references/browser-qa.md`, `references/frontend-testing.md`,
`references/design-accessibility.md`, and relevant feature modules.

Run a maker/checker QA loop:

1. Baseline deterministic tests and critical browser smoke.
2. Report Critical/High/Medium/Low findings with evidence.
3. If the user requested fixes, repair minimal source scope.
4. Re-run exact failures plus the critical smoke bundle.
5. Stop only when acceptance and verification commands pass.

Report-only requests do not authorize code edits.
