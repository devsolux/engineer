# Building an agent that engineers like a 20x senior — research synthesis

Date: 2026-07-20. Method: four parallel web-research streams (harness/loop
architecture; senior-engineer judgment; skill-authoring + evals; verification &
reliability), synthesized against engineer's current design. Sources listed per
section; contested claims flagged. This is a **gap analysis + prioritized upgrade
roadmap**, not generic advice — engineer already implements much of the field's
consensus.

## The convergent thesis

All four streams land on the same claim: **senior-level agent behavior comes from
harness engineering — context + loop + external verification — not model choice.**
SWE-agent lifted GPT-4 from 3.8% → 12.47% on SWE-bench purely by redesigning the
agent-computer interface, no model change (SWE-agent, NeurIPS 2024). The single
highest-leverage practice, named independently by the harness and verification
streams, is **binding "done" to an independent, executable verifier — the grader
must not be the doer** (Anthropic Claude Code best practices, 2025–26).

Two forces work against this and must be engineered around:
- **Context rot** — recall degrades as the window fills; the middle 40–60% of a
  large window is a "dumb zone." Curate to the smallest high-signal set; budget to
  ~40% fill (Anthropic, "Effective Context Engineering," Sept 2025; 12-factor
  agents, Factor 3).
- **Structural false-done** — agents verify only against checks they can *see*, and
  drift from investigating to "wrapping up" as the turn budget runs down. One study:
  an agent's "all tests pass" was true on only 26/45 tasks; it confidently claimed
  success on 19 where hidden tests failed (BSWEN, June 2026).

## Gap analysis: engineer vs. the research

| Practice (research consensus) | engineer today | Gap / sharpening |
|---|---|---|
| Independent verifier, doer≠grader, bound to ship | `browser-qa`, `verify`, enforcement gates | **Make the ship-gate a fresh-context reviewer that re-runs the suite independently and never trusts a sub-agent's own test report.** |
| Executable definition of done + real-browser grounding | `engineer-fix-standard` (browser/UI-tested), prd-to-evidence | Strong. Add an **acceptance-criteria → evidence table** (each criterion → command output/screenshot) as a required `ship` artifact. |
| Hold-out checks the writer never saw; re-run after "done" | partial (evals) | **Add:** commit acceptance tests before impl; keep ≥1 check the code-writer didn't see; parent re-runs post-"done". |
| Diff-scanner for mocks/stubs/TODO/skipped/disabled + test-file edits in feature diffs | `implementation-completeness` module (prose) | **Convert to a deterministic hook** — prose gates survive compaction poorly; hooks don't. |
| Hard prohibitions as hooks, not prose | hooks exist (secrets, repo-lifecycle) | Extend the pattern: every "MUST/never" that's checkable → a `PreToolUse` hook. |
| Senior-judgment forcing prompts (reversibility, root-cause evidence, YAGNI) | principles cover the ideas | **Make them presence-enforced forcing questions**, not just narrative principles. |
| Tool-grounded adversarial review | red-team, decision-engineering | Sharpen: "how could this be wrong?" must **emit new checks to run**, not re-grade prose. |
| Context budget ~40% fill, just-in-time grep/glob, subagent summaries ≤2k tok | per-verb load budgets, L1/L2/L3 disclosure | Add the **runtime** context-budget guidance (retrieval over dumping). |
| Writes single-threaded; subagents = read-only fan-out + review only | `multi-agent-orchestration` | Ensure it **enforces single-threaded writes**; parallel writers demonstrably fail. |
| Description = routing signal (one trigger, no double-"and"); 500-line bodies; refs one level deep | progressive disclosure in place | Run a **description-routing audit** on every module + a bloat/one-level-deep pass. |

**Bottom line:** engineer is already aligned with ~70% of the field's consensus.
The high-value deltas are (1) a genuinely *independent* verification gate with
hold-outs, (2) turning completeness/hard-rules from prose into hooks + an evidence
table, and (3) encoding senior judgment as presence-enforced forcing prompts.

## Prioritized upgrade roadmap

### P0 — the verification core (highest leverage, unanimous)
1. **Independent ship-gate.** `engineer ship` spawns a *fresh-context* reviewer
   agent (no access to the writing context) that (a) re-runs the full suite itself,
   (b) drives the real UI/browser for any UI change, (c) checks the diff against
   acceptance criteria. The doer's own "tests pass" is never sufficient evidence.
   *Why:* self-verification is unreliable — 88% of SWE-bench-Verified trajectories
   self-verify yet 35.7% of those still fail (trajectory analysis, 2025);
   R2E-Gym's hybrid (execution + LLM) verifier lifted 34%→51% at best-of-N (arXiv
   2504.07164).
2. **Hold-out + re-run.** Commit acceptance tests before implementation; keep at
   least one check the writer didn't see; the parent re-runs after "done." The
   visible-pass vs hidden-pass gap is "the only honest measure" (BSWEN, 2026).
3. **False-done diff-scanner hook.** Deterministic `PreToolUse`/pre-ship scan:
   grep the diff for `TODO`, `mock`, `stub`, `skip`, `it.only`/`xit`,
   `@Disabled`, `NotImplemented`, hardcoded return values, and **test-file edits
   inside a feature change**. Block or force-flag. (BSWEN; vscode#274912.)
4. **Acceptance-criteria → evidence table** as a required completion artifact —
   each criterion mapped to a real command output or screenshot. This operationalizes
   "complete means real and verified, including the browser."

### P1 — senior judgment as forcing functions (cheap, high-signal)
5. **Reversibility classification.** Before a change, classify one-way vs two-way
   door; require a written tradeoff note + explicit human sign-off *only* for
   one-way doors; timebox two-way doors and move on (Bezos model). Ties to
   `repo-lifecycle-guard`.
6. **Root-cause-evidence gate.** Before a fix, require a stated root-cause
   hypothesis + evidence (repro/log/trace) distinguishing cause from symptom;
   forbid symptom patches unless explicitly flagged temporary. **Nuance from the
   research:** prefer "identify contributing causes" over "find THE root cause" —
   rigid single-chain 5-Whys is a known failure mode (Salesforce Eng).
7. **YAGNI / Rule-of-Three gate.** Block new abstractions/config/params with no
   current consumer; don't abstract before the third real duplication.
8. **Confidence labels + explicit unknowns** on every load-bearing claim
   (observed / inferred / unknown) — already the user's standing preference
   (`correct-me-when-wrong`); make it a checked output, not a hope.

### P2 — harness hygiene
9. **Tool-grounded adversarial review** (not debate-to-consensus — see contested).
10. **Context-budget discipline**: ~40% fill target, just-in-time retrieval,
    subagent summaries ≤2k tokens, compaction tuned recall-then-precision.
11. **Skill-description routing audit** across all modules; enforce ≤500-line
    bodies, references one level deep with a TOC.
12. **Eval harness with hold-outs**: ≥3 scenarios per module, baseline *without*
    the module, trace-level behavior/drift checks — the only defensible proof a
    module earns its context cost. engineer's `skill-behavior-evals`/`telemetry`
    already start this; add hold-out grading.

## Contested / must-flag (do not hard-code naively)

- **Forcing agents to write their own tests ≠ reliability.** A Feb 2026 study
  found forcing GPT-5.2 to write tests over ~500 SWE-bench tasks was *net-zero*
  resolved; Gemini-3-pro was **−5**. Agent self-tests are mostly print statements
  (3–8% relational assertions) — an *observation channel*, not QA (DevAssure, arXiv
  2602.07900). **Implication:** correctness comes from *independent/hold-out
  execution*, not from the agent grading its own tests. Encode tests as evidence to
  be *independently re-run*, never as self-certification.
- **Intrinsic self-correction is unreliable.** "LLMs cannot self-correct reasoning
  yet" (ICLR 2024) — but *tool-interactive* critique does help (CRITIC, ICLR 2024).
  So "how could this be wrong?" only pays when grounded in a tool result (a failing
  test, a diff, a browser observation), not pure re-reasoning.
- **Multi-agent debate can manufacture false consensus** — the "deliberative
  illusion": agents converge on confidently-wrong answers via communication
  hallucinations (arXiv 2606.03032 / 2606.10296). Prefer read-only fan-out +
  *independent* verification over debate-to-consensus.
- **Keep writes single-threaded.** Parallel writer agents make conflicting implicit
  decisions (Cognition, "Don't Build Multi-Agents"). Note Cognition softened toward
  *some* multi-agent patterns (~2026), but the single-writer rule holds.
- **Version-volatile:** skill numeric limits (500-line body, 1024-char description),
  Anthropic's memory tool (beta), and SWE-bench numbers all drift — re-verify before
  hard-coding. Several 2026 arXiv IDs are un-reviewed preprints; BSWEN's 26/45 is a
  single practitioner study (directionally strong, not a controlled benchmark).

## Pattern: agents that read untrusted DOM or social content

Treat prompt injection as unsolved-by-default: quarantine untrusted content in a
tool-less reader that returns only structured fields (dual-LLM pattern; DeepMind
CaMeL blocked 67% of AgentDojo injections), provenance-tag tool outputs so only
authorized-origin text is actionable, and fail closed behind a human gate after
ingesting attacker-controllable content — sanitization alone fails against
semantic/multimodal injections, so the human-in-the-loop gate is the primary
control, not the filter.

## Key sources
- Anthropic — Effective Context Engineering (Sept 2025); Writing Tools for Agents
  (Sept 2025); Building Effective Agents (Dec 2024); Claude Code best practices;
  Agent Skills eng post + skill-authoring best practices (Oct–Dec 2025).
- SWE-agent (arXiv 2405.15793, NeurIPS 2024) — ACI = +8.7pp with no model change.
- R2E-Gym hybrid verifier (arXiv 2504.07164) — 34%→51% best-of-N.
- BSWEN "Why agents say all tests pass" (June 2026) — 26/45 false-done study.
- DevAssure (arXiv 2602.07900, Feb 2026) — forcing self-tests is net-zero/negative.
- "LLMs Cannot Self-Correct Reasoning Yet" (ICLR 2024); CRITIC (ICLR 2024).
- Cognition — Don't Build Multi-Agents / Multi-Agents: What's Working.
- 12-factor agents (Factor 3, HumanLayer). Deliberative Illusion / Confident Liar
  (arXiv 2606.03032 / 2606.10296). AgentDojo (arXiv 2406.13352) + CaMeL.
- Staff-eng canon: Larson/StaffEng, Charity Majors, Pragmatic Engineer; Bezos
  reversibility; Ousterhout *A Philosophy of Software Design*; 5-Whys + Salesforce
  "How, Not Why".
