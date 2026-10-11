# engineer evaluation telemetry

**Last verified**: 2026-07-15 · **Review cadence**: 3 months
**Scope**: measuring engineer behavior, reliability, cost, and regressions without surveillance

Telemetry is useful only when it changes a decision. Engineer defaults to an explicit, local-only,
metadata ledger derived from validated evaluation receipts. It does not silently monitor ordinary
skill use, export data, or capture prompts, responses, code, commands, paths, identities, session IDs,
tool arguments, or tool results.

## Proportionality gate

Before adding a signal, name the decision it supports:

| Decision | Minimum signal |
|---|---|
| Did the runner work? | capture success, timeout, exit code, infrastructure error |
| Did engineer behavior improve? | independently graded behavioral pass by scenario and version |
| Did efficiency regress? | duration, turns/tokens/cost when the host exposes them safely |
| Is one host adapter failing? | host, model, scenario, error class |
| Should a candidate ship? | paired baseline/candidate outcome, safety, cost, latency, holdout evidence |

Do not collect a field merely because a host exposes it. Lines changed, commits, session counts, token
volume, and acceptance rates are operational context, not standalone quality or productivity measures.

## Default local workflow

```bash
python3 scripts/record-engineer-telemetry.py \
  .engineer/eval-captures/RUN/capture.json \
  --output .engineer/telemetry/events.jsonl
python3 scripts/record-engineer-telemetry.py \
  .engineer/eval-captures/RUN/grade.json \
  --output .engineer/telemetry/events.jsonl
python3 scripts/validate-engineer-telemetry.py .engineer/telemetry/events.jsonl
python3 scripts/summarize-engineer-telemetry.py .engineer/telemetry/events.jsonl
```

Recording is explicit. The recorder canonically validates a capture or replays a deterministic grade,
derives a one-way event identifier, and appends only low-cardinality metadata. Re-recording the same
artifact is idempotent, and duplicate event/source pairs invalidate the ledger. `.engineer/telemetry/`
should remain ignored and access-limited. The summary separates capture success, graded behavioral
pass, safety failures, and the ungraded-capture backlog. An ungraded capture cannot become a quality
pass, and capture plus grade events are not double-counted as two behavioral trials.

Schema v2 adds distinct capture and grade events. Archive or explicitly migrate a schema-v1 ledger;
the recorder refuses to append to an invalid or legacy ledger instead of silently mixing semantics.

After deterministic grading, keep grade receipts beside the raw capture, record the validated grade,
and compile paired reports with `compare-skill-eval-grades.py`. Do not copy outcome booleans into
telemetry by hand. Telemetry is the trend view; the grade receipt and paired report remain the
promotion evidence.

## Privacy and security defaults

- Local only; no endpoint, SDK, daemon, account, or device identifier.
- No prompt/output/tool/file/URL content, even when a provider can expose it.
- No raw run ID; the event ID is derived from the capture digest and schema domain.
- Retain raw capture artifacts under the stricter behavioral-eval policy; keep telemetry only as long
  as it supports comparison, then delete it.
- Treat model names and timestamps as potentially sensitive operational metadata.
- Never use telemetry to rank individual developers or infer productivity from activity volume.
- Export requires a separate reviewed adapter, consent/lawful-basis decision, redaction policy,
  destination allowlist, retention, access control, deletion, and incident response.

## Optional OpenTelemetry adapter

Use OTel only when an organization already operates a collector and needs cross-system correlation.
Keep content gates disabled. Map stable metadata to existing semantic conventions where they fit and
use a versioned `engineer.*` namespace for the evaluation fields. GenAI conventions are still evolving;
pin the convention version and do not make an unstable attribute a promotion oracle.

Claude Code can export OTel metrics, events, and beta traces, but some standard attributes include
account or email identity and content flags can expose prompts, tool arguments, file contents, and API
bodies. Filter at the collector before storage. OpenAI Agents SDK tracing captures generations and tool
calls; set sensitive-data capture off or replace its processor when using engineer evidence. Neither
provider-native telemetry is a host-neutral quality score.

## Core dashboard

Keep the dashboard small:

1. Behavioral pass rate on graded private holdouts, with confidence interval and denominator.
2. Safety regression count and severity; any critical regression blocks promotion.
3. Infrastructure-error rate by host and adapter version.
4. Median/p95 duration, turns, tokens, and cost for paired successful trials.
5. Routing failure rate by scenario family.
6. Ungraded-capture backlog and grader calibration drift.

Slice by engineer version, host, model, and scenario family. Avoid unbounded labels and raw identifiers.

## Overengineering boundary

The local ledger, validator, and summary are justified now because engineer already has multiple hosts,
captured eval receipts, and self-optimization claims. A hosted trace platform, real-time dashboards,
automatic hooks, warehouse, or universal OTel collector is not justified until repeated evaluation
runs make local analysis materially painful or a team needs centralized security/audit operations.

**Research basis**: `../research/engineer-telemetry-2026-07.md`
