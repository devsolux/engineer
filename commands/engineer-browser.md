---
description: Browser-test a web surface with safe lanes, evidence, and Playwright promotion.
---

# /engineer-browser

Load `references/browser-qa.md`, `references/browser-agent-security.md`,
`references/frontend-testing.md`, and `references/workflows.md`.

1. Detect URL, environment, roles, mutations, available browser runtime, auth state, origins,
   transfers, permissions, and data classes.
2. Build a route × role × viewport × state coverage matrix.
3. Parallelize only isolated read/data lanes; serialize shared-account writes.
4. For an agent-controlled or authenticated browser, declare exact origins, page-derived URL
   policy, permissions, popups, downloads/uploads, approvals, stop conditions, and artifact rules.
5. Capture navigations, requests, redirects, actions, prompt-injection handling, assertions,
   console/network failures, screenshots/traces, and exact repro steps.
6. Emit and validate `browser-session.json` when browser authority or untrusted content matters.
7. Promote stable regressions to Playwright; leave exploratory observations in the QA report.

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
python3 "$ENGINEER/scripts/validate-browser-session.py" browser-session.json --json
```

Production and external authenticated mutations require explicit approval.
