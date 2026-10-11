# Executable Playwright browser guard research - 2026-07

## Gap

The browser-session receipt could detect a bad captured session, but the template did not prevent
or collect the relevant events. Agent-authored tests could navigate elsewhere, leak a token through
a URL, open a popup, start a download, or encounter a dialog without a common enforcement layer.

## Primary-source findings

- Playwright contexts provide cheap per-test isolation, but routes and event listeners are needed to
  constrain requests and observe popups, downloads, dialogs, console errors, and page failures.
- A popup remains in its parent browser context. Context isolation alone does not make it trusted.
- Service workers can hide network activity from ordinary routing and request interception. Blocking
  them is appropriate for a security-evidence lane unless the service worker itself is under test.
- Storage state and traces can contain authentication or page data. The runtime guard should collect
  minimal structured evidence and leave retention/redaction decisions to the session receipt.
- OpenAI's browser-agent security guidance supports exact URL checks and defense in depth instead of
  relying on domain reputation or a prompt-injection classifier.

## engineer decision

Ship a small Playwright utility rather than a custom browser framework. It validates canonical
origins before use, intercepts every routable request, blocks sensitive URL keys and userinfo,
optionally enforces exact navigation URLs, contains unexpected popups/downloads/dialogs, records
runtime errors, and provides one `assertClean` gate. User intent and mutation approval remain in the
browser-session contract because browser events cannot infer them.

## Sources

- https://playwright.dev/docs/browser-contexts
- https://playwright.dev/docs/api/class-browsercontext
- https://playwright.dev/docs/downloads
- https://playwright.dev/docs/network
- https://openai.com/index/ai-agent-link-safety/
