# Browser-agent security research - 2026-07

## Gap

engineer's browser lane model correctly isolated Playwright workers and warned that page content is
untrusted. It did not make browser-agent authority observable. There was no receipt for profile and
auth-state selection, origins, page-derived URLs, redirects, popups, downloads/uploads, clipboard,
device permissions, prompt-injection response, or artifact leakage.

## Primary-source findings

- Playwright creates isolated browser contexts, but popups remain inside the parent context. Storage
  state can contain cookies, local storage, and IndexedDB authentication data and must be treated as
  sensitive. Mutating parallel tests should use one account per worker.
- Playwright traces contain DOM snapshots, requests, actions, and screenshots. Retain them for
  failure diagnosis, but do not assume authenticated traces are safe public artifacts.
- OpenAI describes prompt injection as social engineering against an agent reading third-party
  content. Logged-out browsing, sandboxing, reduced permissions, monitoring, and confirmation for
  sensitive actions reduce impact but do not solve the problem.
- OpenAI's link-safety work reasons about the exact URL rather than domain reputation. URLs can
  themselves exfiltrate user-specific information through query values and fetches.
- OWASP agentic guidance treats misuse of legitimate browser and rendering tools as a source-to-sink
  exfiltration path, even when the agent has not technically exceeded its assigned identity.

## engineer decision

Add one combined browser policy and observed-session receipt. Default to logged out, ephemeral,
first-party-only, read-only, no transfers, no clipboard/device permissions, failure-only redacted
artifacts, and exact approval for mutations. Every navigation and request is checked independently;
page content never becomes authority.

The validator proves receipt consistency and retained local hashes. It does not inspect hidden page
behavior that the browser instrumentation failed to record.

## Sources

- https://playwright.dev/docs/browser-contexts
- https://playwright.dev/docs/auth
- https://playwright.dev/docs/trace-viewer
- https://openai.com/index/prompt-injections/
- https://openai.com/index/ai-agent-link-safety/
- https://openai.com/index/designing-agents-to-resist-prompt-injection/
