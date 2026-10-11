# Defensive agent red-teaming

**Last verified**: 2026-07-15 · **Review cadence**: 2 months

Use this module to test an agent you own or are explicitly authorized to assess. Work only in
isolated fixtures with synthetic data, inert canaries, disabled destructive actions, and denied
or simulated network access. Never point generated attacks at third-party or production systems.

## Threat coverage

Cover the whole agent system, not only the chat boundary:

- Goal hijacking through direct or indirect prompt injection.
- Social engineering that creates urgency, impersonates authority, or requests secrecy.
- Legitimate-tool misuse and confused-deputy actions.
- Agent identity, delegated authority, token scope, and privilege escalation.
- Skill, MCP, plugin, model, dependency, and retrieved-content supply-chain poisoning.
- Unexpected code execution, shell abuse, sandbox escape attempts, and unsafe interpreters.
- Memory, checkpoint, RAG, cache, and context poisoning that persists across sessions.
- Insecure agent-to-agent messages, spoofed peers, delegation loops, and trust laundering.
- Data exfiltration through URLs, redirects, DNS-like channels, tool arguments, logs, or files.
- SSRF, link-following abuse, cross-domain transmission, and destination confusion.
- Persistence through modified instructions, hooks, startup files, scheduled work, or memory.
- Resource exhaustion, retry amplification, denial-of-wallet, and uncontrolled fan-out.
- Cascading failures, correlated workers, stale state, and unsafe fallback behavior.
- Grader gaming, sandbagging, code sabotage, audit-log tampering, and oversight manipulation.

### Named 2025-2026 classes (coverage items)

The categories above hold; name these live classes so coverage is explicit:

- **Coding-/IDE-agent RCE** - rules-file / agent-config injection (Pillar "Rules File Backdoor"
  2025-03: hidden-unicode `.cursorrules`/`.cursor/rules`/`copilot-instructions.md`), CurXecute
  (CVE-2025-54135), MCPoison (CVE-2025-54136), Claude Code (CVE-2025-54794/54795). Scan the
  config surfaces (`.vscode`, `.cursor`/rules, `AGENTS*`, `.mcp.json`) for hidden unicode +
  imperatives before the agent trusts them.
- **CI-agent / auto-PR-review abuse** - Comment-and-Control, PromptPwnd, GhostAction; the
  `pull_request_target`-with-secrets pitfall (arguably the highest-impact 2026 class). Never let
  an auto-review agent fire on attacker-authored events with repo secrets in the runner env.
- **Denial-of-wallet** - OWASP LLM10:2025 Unbounded Consumption; real cost incidents (LLMjacking
  ~$46k/day). Enforce step/loop/spend budgets.
- **MINJA memory poisoning** (NeurIPS 2025) - query-only, leaves **no install-time artifact** and
  fires later on an unrelated query, so admission-time scanning does not cover it; treat durable
  memory/RAG as a standing surface.

## Safe test construction

Each adversarial case needs an equivalent benign control when the desired behavior could be
over-blocked. State the authorized fixture, synthetic assets, inert canary, expected safe state,
forbidden outcomes, observable signals, cleanup, severity, owner, and regression ID. Grade the
environment and tool arguments. A refusal string does not prove that no side effect occurred.

Use the smallest non-operational stimulus that exercises the control. Do not store live secrets,
weaponized exploit code, persistence commands, or third-party targets in eval corpora. Simulate
dangerous sinks and assert that authorization, policy, or sandbox controls block them.

## Response loop

1. Reproduce inside the isolated fixture and preserve the trace.
2. Classify source, sink, identity, trust boundary, preconditions, and blast radius.
3. Contain by revoking credentials, disabling tools, denying egress, or stopping the agent.
4. Fix the lowest responsible layer: authorization, sandbox, tool contract, parser, memory,
   orchestration, prompt, or monitor.
5. Run the adversarial case and its benign control repeatedly.
6. Add the case to regression coverage and record residual risk.

## Machine-checkable catalog

Start from `templates/agentic/security-eval-catalog.sample.json` and run:

```bash
python3 scripts/validate-security-eval-catalog.py security-eval-catalog.json
```

**Related**: `ai-security.md`, `agentic-engineering.md`, `prompt-optimization.md`, `ai-evals.md`

**Research basis**: `../research/agentic-engineering-2026-07.md`
