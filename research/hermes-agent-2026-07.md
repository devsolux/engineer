# Hermes Agent research - 2026-07

## Scope and identity

This research covers the official MIT-licensed `NousResearch/hermes-agent` runtime, not the Hermes
model family or unrelated projects. The canonical sources are the NousResearch GitHub repository
and `hermes-agent.nousresearch.com` documentation.

The local installation inspected on 2026-07-15 reported `Hermes Agent v0.17.0 (2026.6.19)` from
a local Hermes agent checkout; the official product page advertised v0.18.2. No update was
performed. Runtime drift must be handled through a reviewed upgrade, not an automatic latest pull.

## Architecture and capabilities

- The agent loop supports provider/model abstraction, tool calls, strict role alternation, context
  compression, prompt caching, session persistence, interrupt/redirect, and structured trajectories.
- Tools cover terminal, files, web, browser, media, memory, skills, cron, delegation, MCP, and RPC-
  based `execute_code`. Toolsets can be narrowed per platform.
- Terminal backends include local, Docker, SSH, Singularity, Modal, and Daytona. Docker hardening
  drops capabilities, uses no-new-privileges, process/tmpfs limits, resource settings, and an
  explicit environment forward allowlist. Host mounts, Docker socket, egress, and forwarded secrets
  remain operator boundaries.
- Browser backends include local Chromium/CDP, local agent-browser, Camofox, Browserbase, Browser
  Use, and Firecrawl. Persistent profiles, stealth/proxy features, cloud data transfer, dialogs,
  downloads, and raw CDP each require separate risk decisions.
- Profiles isolate Hermes state through `HERMES_HOME`. Official docs explicitly state that host
  subprocesses keep the real OS `HOME` by default, sharing ordinary CLI credentials; strict tool
  identity requires `terminal.home_mode: profile` and profile-specific credential setup.
- Skills follow the agentskills progressive-disclosure pattern. Memory stores compact durable facts;
  skills store longer procedures. Background learning, `/learn`, usage tracking, curator lifecycle,
  pinning, snapshots, and opt-in consolidation form the self-improvement system.
- Cron starts fresh sessions, stores jobs/results, and scans prompts. Gateways support many messaging
  platforms; API/ACP expose programmatic/editor surfaces. Subagents get separate conversations,
  terminals, and toolsets.

## Security findings

Official documentation describes default manual dangerous-command approval, fail-closed timeout,
headless cron denial, hard deny patterns, gateway allowlists/pairing, MCP credential filtering,
context-file scanning, session/path isolation, and hardened container backends. These controls are
defense in depth, not substitutes for external sandboxing and least privilege.

Important sharp edges:

- `--yolo` and approval mode `off` disable command prompts.
- Local CLI help states that `--oneshot` auto-bypasses approvals for scripting.
- `--accept-hooks` accepts previously unseen shell hooks in headless contexts.
- Container backends skip host command guards because isolation is assumed; mounts, environment,
  egress, runtime privilege, and persistence determine whether that assumption holds.
- Profiles separate Hermes data but can share host HOME credentials.
- Persistent memory, learned skills, context files, plugins, hooks, MCP results, browser content,
  messages, and cron inputs are durable or executable prompt-injection surfaces.
- Checkpoints help working-tree rollback but do not replace repository history or system backup.

## engineer composition decision

Hermes remains the host/runtime. Engineer should provide engineering routing, scoped plans, security
policy, orchestration contracts, browser lanes, skill/MCP admission, output quality, and completion
evidence. It should not duplicate Hermes gateway, provider routing, memory engine, profiles, cron,
browser provider, terminal backend, or curator.

Private engineer should be symlinked into the relevant profile's skill directory, pinned against
curator mutation, and updated only from its canonical private source after tests. Hermes-generated
skill improvements are candidates; engineer's own self-optimization remains its governed repository
workflow.

## Primary sources

- [Official repository](https://github.com/NousResearch/hermes-agent)
- [Feature overview](https://hermes-agent.nousresearch.com/docs/user-guide/features/overview/)
- [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security/)
- [Agent loop](https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop/)
- [Context compression and caching](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching/)
- [Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles/)
- [Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/)
- [Curator](https://hermes-agent.nousresearch.com/docs/user-guide/features/curator/)
- [Browser automation](https://hermes-agent.nousresearch.com/docs/user-guide/features/browser/)
- [Code execution](https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution/)
- [Cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
- [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [API server](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server/)
- [CLI commands](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md)
- [Fallback providers](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/fallback-providers.md)
- [Credential pools](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/credential-pools.md)

## Refresh triggers

Refresh for each installed Hermes upgrade and monthly otherwise. Recheck CLI approval behavior,
terminal/container isolation, browser backends, profile/HOME semantics, skill write gates, curator
defaults, plugin/MCP provenance, cron security, gateway authorization, API binding/authentication,
context engines, and release/migration notes.
