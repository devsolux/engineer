# Long-horizon and ongoing agent session dynamics research

**Date:** 2026-07-16  
**Feeds:** `references/long-horizon-agents.md`

## Findings encoded

- Long sessions degrade through named, measured mechanisms: context rot (reliability falls with
  input length long before the window limit; effective context commonly ~50-65% of advertised),
  lost-in-the-middle positional bias (U-shaped recall; attention sinks), multi-turn instruction and
  output drift (a reliability collapse, not a capability drop), and self-conditioning (per-step
  accuracy falls once the model's own errors enter context — long-horizon failure is compounding
  execution error, not a reasoning ceiling).
- Compaction is the most consequential state transition in a long session: summaries reliably drop
  exact paths/hashes, failed-attempt records, pending approvals, constraints, and decision
  rationale, and can be re-read as active instructions (task resurrection). It became a
  configurable API primitive in 2025-2026.
- Prompt-cache economics force append-only, byte-stable prefixes: agent loops run near 100:1
  input:output; cache reads price ~0.1x vs ~1.25-2x writes; any edit to earlier context busts the
  cache from that point; hit rate is a first-class production metric.
- The mitigation architectures converge on one contract: conversation is cache, files are truth —
  a durable spine (plan files, journals, receipts) written at phase boundaries, resumed by
  fresh-context read plus independent environment verification, with failed attempts recorded then
  purged from active context.
- Fan-out vs single-thread is a decision boundary, not a winner: fresh-context sub-agents win for
  independent read-heavy exploration at ~15x token cost; coherence-critical work with shared
  mutable state stays single-threaded.
- Ongoing/cron agents sidestep in-session degradation structurally (fresh session per run,
  snapshot-read startup, idempotent fire-claimed work, snapshot + append-only journal on exit); the
  failure surface shifts to cross-run drift, so per-run quality gates and state-file
  freshness/integrity checks replace the in-session operator.
- Sleep-time/background consolidation is a real cost lever on reused contexts but every background
  write is an unattended memory mutation; admission gates, dry-run, snapshots, and pins apply.

## Primary sources

- Liu et al., [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) (TACL 2024)
- Chroma, [Context Rot: How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot) (2025)
- Modarressi et al., [NoLiMa: Long-Context Evaluation Beyond Literal Matching](https://arxiv.org/abs/2502.05167) (ICML 2025)
- Hsieh et al., [RULER: What's the Real Context Size of Your Long-Context Language Models?](https://arxiv.org/abs/2404.06654) (COLM 2024)
- Sinha et al., [The Illusion of Diminishing Returns: Measuring Long Horizon Execution in LLMs](https://arxiv.org/abs/2509.09677) (2025)
- METR, [Measuring AI Ability to Complete Long Tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) (2025)
- Laban et al., [LLMs Get Lost in Multi-Turn Conversation](https://arxiv.org/abs/2505.06120) (2025)
- Xiao et al., [Efficient Streaming Language Models with Attention Sinks](https://arxiv.org/abs/2309.17453) (ICLR 2024)
- Anthropic, [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic, [How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system) (2025)
- Cognition, [Don't Build Multi-Agents](https://cognition.ai/blog/dont-build-multi-agents) (2025)
- Manus, [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) (2025)
- Packer et al., [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) (2023)
- Lin et al., [Sleep-time Compute: Beyond Inference Scaling at Test-time](https://arxiv.org/abs/2504.13171) (2025)
- Dong et al., [MINJA: A Practical Memory Injection Attack against LLM Agents](https://arxiv.org/abs/2503.03704) (2025)

## Local corpus

Full 12-item validated corpus with local implementation evidence (a Hermes agent checkout's
`context_compressor.py` and cron fire-claims, the private strategy skill's long-lived agent
snapshot + journal, Claude Code compaction behavior): `agent-longevity-research` in the skills
workspace — start at `playbooks/long-horizon-playbook.md`. Private; not shipped with this skill.

## Limits

Benchmark-derived curves are directional for production, not laws. Exact constants (compaction
thresholds, cache pricing/TTLs, tool-count cliffs, reliability horizons) are harness-, model-, and
pricing-version-sensitive; re-verify on the review cadence before citing them as current.
