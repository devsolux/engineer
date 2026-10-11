# Behavioral skill evaluations research

**Verified**: 2026-07-15

## Problem

A prompt bank proves that scenarios and expected behaviors are documented. It does not prove
that an agent loaded the skill, chose the right modules, respected boundaries, used tools
correctly, or produced the required outcome. Engineer therefore needs two distinct claims:

- static bank validity: the test specification is internally sound;
- behavioral run validity: a named agent and frozen environment produced captured evidence.

## Findings adopted

1. Grade the environment outcome and the trajectory, not only the final prose. Agent work is
   multi-turn and changes state, so single-response matching is insufficient.
2. Combine deterministic, model, and human graders. No grader type covers every failure.
3. Preserve raw output, trace, and resulting-state evidence with hashes. A summary score without
   recoverable artifacts cannot support a release claim.
4. Separate infrastructure errors from agent failures. Resource and runtime configuration are
   part of an agentic benchmark and can move results materially.
5. Calibrate model graders against independently reviewed human samples. Do not let the optimizer
   grade its own candidate or expose hidden expected answers to the tested agent.
6. Keep promotion sets private or sequestered, test contamination explicitly, and turn real
   production failures into regression cases without publishing the entire holdout.

## Rejected shortcuts

- Treating `scripts/run-evals.sh --full` as a live model evaluation.
- Scoring only whether expected keywords appear in the final answer.
- Keeping only aggregate pass rates and deleting failed trajectories.
- Counting timeouts, broken fixtures, or unavailable tools as model failures.
- Using a model judge without a version, rubric, evidence, or human calibration.
- Promoting a change from the same public scenarios used during optimization.
- Passing assertions, goldens, grader rubrics, or promotion labels to the tested agent.
- Reusing an everyday developer workspace, inherited tool configuration, or broad shell environment
  for a supposedly isolated evaluation.

## Cross-host capture findings

- Codex documents `codex exec` for non-interactive pipelines. It supports ephemeral sessions,
  explicit sandbox and approval settings, isolated user configuration, JSONL events, and a separate
  final-message file. Its default non-interactive sandbox is read-only and network access is off.
- Claude Code documents print mode, JSON or stream-JSON output, bounded turns, tool allowlists and
  denylists, permission modes, and budget caps. Current local help also exposes bare mode and
  non-persistent sessions.
- Host commands are adapters, not the evidence model. Raw traces must be normalized only after the
  original output is retained, and an adapter must fail closed when a required isolation flag is
  missing or changed.
- Freezing a host name is insufficient. Bind the executable plus version/help probe hashes and the
  adapter's required advertised capabilities, then capture them again immediately before execution.
  This detects local binary and CLI-surface drift without claiming that help text proves enforcement.
- A capture manifest needs its own oracle before grading. Bind the job and every raw artifact by confined
  path, byte count, and digest; scan output, trace, and stderr for high-confidence secrets; and preserve
  `behavioral_pass` as unknown until independent outcome and trajectory graders run.
- A digest copied from the runner is not command proof. Recompile the bound job and compare a logical
  command digest independently; keep the post-resolution executed argv digest labeled as observed unless
  a trusted runner attests it.
- Claude permission rules are semantic: bare `Read` allows all reads, while `Read(./**)` scopes the allow
  rule to the current fixture and also applies best-effort to Glob and Grep. With `dontAsk`, outside or
  symlink-target misses are denied rather than prompted. This is still CLI enforcement, not an OS sandbox.
- Codex documents API keys as the automation default and warns that read-only alone does not protect
  secrets. Cross-host evals therefore use direct provider API keys plus disposable HOME/config roots,
  never developer OAuth caches or keyrings; external isolation remains required for hostile fixtures.
- Isolated config roots also remove installed skills. A valid behavioral run must bind and copy an
  expectation-free engineer package into the disposable Codex skill directory or load it as an explicit
  Claude plugin. Claude plugin skills are namespaced, so the sealed invocation is
  `/engineer-eval:engineer`; Codex uses `$engineer`. Package digests cover paths, bytes, and executable bits,
  reject symlinks, and exclude eval answers, research, fixture evidence, git state, and local plans.
- Codex cached web search may otherwise remain available independently of shell network. The adapter
  sets `web_search="disabled"` explicitly; Claude denies WebFetch and WebSearch and uses bare mode with
  only the sealed local plugin.

## Sources

- Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), 2026-01-09.
- Anthropic, [Quantifying infrastructure noise in agentic coding evals](https://www.anthropic.com/engineering/infrastructure-noise), 2026-02-05.
- OpenAI, [Graders API reference](https://developers.openai.com/api/reference/resources/graders).
- OpenAI, [Evals API reference](https://developers.openai.com/api/reference/resources/evals).
- OpenAI, [PaperBench](https://evals.openai.com/), including hierarchical rubrics and judge evaluation.
- Anthropic, [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf), 2026.
- OpenAI, [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode.md), current manual fetched 2026-07-15.
- Anthropic, [Claude Code permissions](https://code.claude.com/docs/en/permissions), current 2026-07-15.
- Anthropic, [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference), current 2026-07-15.
- Anthropic, [Create plugins](https://code.claude.com/docs/en/plugins), current 2026-07-15.
- Anthropic, [Plugins reference](https://code.claude.com/docs/en/plugins-reference), current 2026-07-15.
