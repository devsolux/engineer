# Codebase security audit (evidence-graded vulnerability hunt)

**Last verified**: 2026-10-22 · **Review cadence**: 2 months

Use this module for `engineer security-audit <target>`: hunt real vulnerabilities in a codebase
you own or are explicitly authorized to assess, prove each against a trust boundary, and report
with bound evidence. The verb is report-only: it never edits target source, deploys, or decides
what to install. `engineer audit` scores a rubric; `engineer red-team` attacks an agent you run.
This verb answers one question: can a lower-trust principal cross a boundary, and can we show
it. `security-attack-classes.md` (catalog) and `security-audit-domains.md` load per wave.

## Contents
- [Modes](#modes)
- [Boundary-and-result rule](#boundary-and-result-rule)
- [Execution safety](#execution-safety)
- [Six phases](#six-phases)
- [Verdicts and the severity rule](#verdicts-and-the-severity-rule)
- [Fingerprints and coverage ids](#fingerprints-and-coverage-ids)
- [Profiles and budget reservation](#profiles-and-budget-reservation)
- [Run status](#run-status)
- [Multi-run carry-forward](#multi-run-carry-forward)
- [Delegation](#delegation)
- [Artifacts](#artifacts)
- [Report sections](#report-sections)
- [Validators](#validators)
- [Anti-patterns](#anti-patterns)

## Modes

| Mode | Trigger | Output |
|---|---|---|
| Guidance (default) | A security question about one mechanism, file, or design ("is our JWT refresh middleware safe?") | Answer in chat from the catalog and domain companion, claims labelled observed / inferred / assumed / unknown; no run directory, no artifacts, no verdicts |
| Full run | An explicit request to audit the codebase, find vulnerabilities, do a pen-test-style source review, run a full security review, or produce findings artifacts | The six phases below, `.engineer/security-audit/run-<NNN>/`, validated `coverage.json` and `findings.json`, three reports |

An ambiguous request gets one focused question ("a one-off answer about X, or a full audit run
with artifacts?"), then proceeds. Never start a full run from an implied wish. Before a full run,
confirm ownership or written authorization for the target; refuse when neither exists.

## Boundary-and-result rule

A finding is a claim that a named principal crosses a trust boundary. Every candidate must fill:

| Field (`boundary`) | Must answer |
|---|---|
| `principal` | Who acts, at what trust level (anonymous, authenticated user, tenant admin, internal service, CI) |
| `input` | What that principal controls (parameter, header, file, message, config, timing) |
| `intended_control` | What should have stopped it (authz check, parameterization, schema, RLS, signature, sandbox) |
| `crossed` | Which boundary fails and how the control is bypassed or absent |
| `result` | What the principal observably obtains or changes (data read, write, execution, denial, money) |

A candidate missing any field is not a finding. A checklist deviation that another layer prevents
is a **hardening note** with `layer_preventing_attack` named (a JSON-only API with a custom
request header and `SameSite=Strict` cookies lacks a CSRF token: hardening note, not a finding).
Hardening notes carry no severity and never count toward `summary.confirmed`.

## Execution safety

- **Read-only inspection.** `safety.source_inspection: read_only`. Never edit target source,
  tests, config, or git state. The verb writes only under the run directory or `--out DIR`.
- **Sandbox or nothing.** Target code (tests, scripts, services) runs only inside an OS-enforced
  sandbox with `network: none`, `env: empty_allowlist`, `target_mount: read_only`,
  `writes: scratch_only`, and positive `limits {cpu_seconds, memory_mb, wall_seconds}`. Without
  one, do not execute: record `sandbox.available: false` with `unavailable_reason`, keep checks
  to `method: source`, and let affected candidates land in `needs_validation` with a `runtime`
  blocker; the validators reject `local_execution` evidence and `local` checks otherwise.
- **Synthetic principals and secrets.** `safety.principals: synthetic` and
  `safety.secrets: synthetic` are exact values. A request to confirm with production
  credentials, real accounts, or live tokens is refused and recorded in the report.
- **Never probe live systems.** `safety.live_systems_probed: false` is exact: no requests to
  staging, shared, or production hosts, no scans of third parties, no load generation.
- **One writer.** Only the parent writes shared artifacts. Every agent writes one JSON result
  into its own scratch; `security-ledger.py promote` admits it after regular-file, size (≤2 MiB),
  JSON, and assigned-unit checks. A result that fails promotion is discarded, never patched.
- **Findings are sensitive.** `.engineer/` must be gitignored in the target; never commit, push,
  paste, or upload a run directory. Use `--out DIR` outside a read-only or shared target.

## Six phases

| # | Phase | Owner | Output |
|---|---|---|---|
| 1 | Reconnaissance | parent | `run-<NNN>/architecture.md` (≤1000 words, eight headings); `coverage.json` with every cell `planned` |
| 2 | Hunting waves | isolated hunters | one `agents/<agent-id>.json` each: `{units, candidates, hardening, uncovered}` |
| 3 | Coverage critique | fresh critic per wave | proposed units (`proposed_by` = critic), never candidates |
| 4 | Refutation | verifier that did not hunt the candidate | one record per unique fingerprint with a verdict |
| 5 | Record review | reviewer independent of hunter and verifier | `findings.json` with exactly three verdict values |
| 6 | Reporting | parent | `REPORT.md`, `FINDINGS-DETAIL.md`, `NEEDS-VALIDATION.md`, target-neutral |

**Phase 1.** Read the target as an architect, not a scanner. Write the brief under exactly these
`##` headings: Principals, Authority, Protected resources, Stack, Entry surfaces, Trust
boundaries, Starting paths, Prior-run gaps. Label each statement observed (file and symbol
cited), inferred, assumed, or unknown. Read every prior `run-*/coverage.json` and
`findings.json`. Declare `dimensions`: `surfaces[] {id, ref, kind ∈ http|ui|cli|job|webhook|
rpc|message|file|other}`, `boundaries[] {id, from, to, strongest_visible_control}`,
`subsystems[] {id, paths[]}`, `attack_classes[]` from the catalog, as one small JSON file;
`security-ledger.py init` expands the cross product into `planned` units and binds the brief.
`not_applicable` and `out_of_scope` cells need a reason.

**Phase 2.** `security-ledger.py assign` hands units to hunters that share nothing but the
brief and the catalog. Each hunter loads the catalog plus the matching domain section, reads the
assigned paths in full, and returns one JSON result: `units` as `covered` (reviewed paths,
checks with a `result_fingerprint`), `candidate` (plus `candidate_fingerprints`), `blocked`, or
`not_applicable` with a reason; `candidates` with a draft boundary and trace; `hardening`
notes; `uncovered` gaps. A hunter never verifies its own candidates or reads another hunter.

**Phase 3.** After each wave a critic that hunted nothing in it reads the brief, ledger, and
wave results and proposes missing units (surfaces no unit covers, boundaries with no class
coverage, subsystems no hunter reviewed, feature interactions) as `planned` units with
`proposed_by`. Waves run until the critic returns `stop` or the hunting budget is spent.

**Phase 4.** Group candidates by fingerprint and hand each unique one to a verifier that did
not hunt it. The verifier attempts refutation first (the control the hunter missed, the
unreachable path, the type that cannot carry the payload, the migration that already shipped)
and builds the record only when that fails: trace `entrypoint` → `propagation` → `sink`, bound
evidence, conditions, remediation. One record, one verdict, `verifier_attempted_refutation: true`.

**Phase 5.** An independent reviewer reads every record against its evidence and its coverage
unit. Outcomes: verified (cosmetic fixes ride in the reason), or replaced: a rewritten boundary,
trace, or verdict, including a proposed rejection, goes to a second verifier independent of
hunter, first verifier, and reviewer (`replacement_verifier`), who reaches the verdict alone.
Assemble `findings.json`, sort records by fingerprint, compute `summary`, close the ledger with
`security-ledger.py finish`, validate both files.

**Phase 6.** Write the reports from `findings.json` only; every number must be recomputable
from the artifacts. A clean run says "zero findings in the covered units"; it never says "secure".

## Verdicts and the severity rule

| Verdict | Requires | Forbids |
|---|---|---|
| `confirmed` | trace ≥2 stages, first `entrypoint`, last `sink`, `propagation` only between; evidence ≥1; conditions ≥1; `remediation {summary, layer, paths[], regression_test\|null}`; `severity {likelihood, impact, overall}`; `confidence ∈ {medium, high}`; `record_reviewer` | `blockers`, `validation_plan`, `rejection` |
| `needs_validation` | `blockers[]` ≥1 of `{kind ∈ deployment\|runtime\|configuration\|data, unresolved_fact, why_it_matters}`; `validation_plan {local[], owner_observed[]}` with at least one non-empty list of `{action, expected_if_vulnerable, expected_if_safe, sandbox_required}`; trace ≥1 starting at `entrypoint`; evidence ≥1; `record_reviewer` | `severity` (an error, not a warning), `remediation`, `rejection` |
| `rejected` | `rejection {reason, refuted_by}` with `refuted_by == verification.verifier` | `severity`, `blockers`, `validation_plan`, `remediation` |

Severity exists only on `confirmed`. `likelihood ∈ {low, medium, high}` follows from the
conditions (`authentication_level`, `authorization_role`, `user_interaction`,
`system_configuration`, `network_routing`, `environmental_dependency`, `data_state`,
`timing_dependency`, `third_party_dependency`). `impact ∈ {low, medium, high, critical}` is what
the demonstrated result does to confidentiality, integrity, availability, or money. `overall` is
likelihood × impact and never ranks above `impact`. Conditions lower likelihood, never raise
impact. A chain of hops is one record with the final hop's impact. Do not grade hypothetical
impact ("if this were internet-reachable"): that is `needs_validation` with a blocker.

Every `evidence[]` entry is a file under the run's `evidence/<fingerprint>/` bound by
`{path, sha256, bytes}` with `kind ∈ source_excerpt|local_execution|test|config|git_history|log`.
`confidence` is the verifier's: `high` only when the sink was exercised in the sandbox or the
trace is fully static and typed; `low` only on `needs_validation`.

## Fingerprints and coverage ids

- `coverage_id = "cov-" + sha256(surface|boundary|subsystem|attack_class)[:12]`
- `fingerprint = "sa1-" + sha256(attack_class|root_cause.path|symbol|sink)[:16]`, a null
  `symbol` or `sink` serialized as the empty string

Neither includes line numbers, agent ids, titles, or severity, so one root cause carries one id
across runs and hunters, and two hunters reporting it produce one verification. Both validators
recompute the ids. `root_cause {path, symbol|null, sink|null, note}` names the fix location.

## Profiles and budget reservation

| Profile | Breadth | Typical use |
|---|---|---|
| `quick` | One wave; subsystems named in Starting paths; wildcard class only on the critic's proposals | Pre-merge spot check of one subsystem; a re-run after fixes |
| `standard` | Waves until the ledger is complete or the hunting budget ends; full catalog; one critic per wave | Default |
| `deep` | As standard plus git history, feature-interaction units, and a second critic pass over `covered` units | Pre-launch, post-incident, or inherited code |

Profiles change breadth only; evidence bar, refutation, independence, and severity rules never vary.

Reserve before hunting: `budget {unit, total, reserved {critics > 0, verification > 0},
reserved_before_hunting: true, spent {reconnaissance, hunting, critics, verification,
record_review, reporting}}`. `spent.hunting ≤ total − reserved.critics − reserved.verification`,
and the sum of `spent` never exceeds `total`. When another wave would eat the reserve, stop
hunting, mark remaining units `deferred` with a reason, and finish verification. An unverified
candidate is worth nothing; an unhunted unit is at least an honest gap.

## Run status

`status: complete` holds only when no unit is `planned` or `in_progress` **and** every surface ×
boundary × subsystem × attack_class cell exists as a unit (the coverage validator names the
missing count). Anything else is `incomplete` with an `incomplete_reason` stating the exact
cause: budget exhausted after wave N, sandbox unavailable, scope cut by the owner, paths
unreadable. `summary.clean` is true iff `confirmed == 0` and `needs_validation == 0`; a clean
run with empty `records` is valid, and the report's first line says so next to the coverage
counts that qualify it.

## Multi-run carry-forward

A new run is additive: `run-<NNN>` increments, `prior_runs[]` lists what was read, and recon
reads every prior ledger and findings file. `security-ledger.py gap --prior <prior run dir>`
marks `carried_from {run_id, prior_status, source_changed}` on shared units from
`git diff --name-only <prior source_ref>..HEAD` (no git: every unit counts as changed). Rules:

- Changed source on a `covered` or `candidate` unit → fresh checks and a wave in this run.
- Prior `confirmed` → re-verified in this run by a verifier (`carried_from {run_id,
  prior_verdict, reverified: true}`, `verified_at` inside this run). Never carry a confirmation as
  an assumption or report "still present" without the re-verification record.
- Prior `needs_validation` → re-check the blockers; new owner-observed facts become conditions.
- Prior `rejected` → stale, not a verdict in this run. Re-hunt the unit when its source changed;
  otherwise it carries forward as `covered` with the prior checks referenced.
- A fingerprint that disappears is "no longer observed", not "fixed", unless the remediation
  commit is cited as `git_history` evidence.

## Delegation

Map the roles onto `multi-agent-orchestration.md`: one owner per role per unit, a typed result
contract, an authority ceiling, hash-bound promotion; agent ids match `^[a-z][a-z0-9_-]{1,63}$`.

| Role | Reads | Writes | Must not |
|---|---|---|---|
| hunter | brief, catalog, domain section, assigned paths | one JSON result in own scratch | verify own candidates; grade severity; read other hunters |
| coverage critic | brief, ledger, wave results | proposed units | hunt; see or touch candidates |
| verifier | brief, one candidate, its paths, sandbox | one record with verdict and evidence | be the candidate's hunter; skip refutation |
| record reviewer | records and evidence | verified / replaced decisions | be hunter or verifier of the record |
| parent | everything | shared artifacts, reports | execute target code outside the sandbox; alter agent results |

Prompt bodies: `templates/agentic/prompts/security-hunter.md`, `security-coverage-critic.md`,
`security-verifier.md`, `security-record-reviewer.md`. Each states the role's inputs, the single
JSON output, the scratch-only write lane, and the ceiling (read target, no network, no target
edits, no shared writes). The findings validator enforces `hunter ≠ verifier`,
`record_reviewer ∉ {hunter, verifier}`, `replacement_verifier ∉ {hunter, verifier,
record_reviewer}`. Hosts without sub-agents serialize the roles in fresh contexts in phase order
with distinct agent ids, and the report's Method section discloses that one host model played
every role. Parallel agreement between hunters is correlated evidence, not verification.

## Artifacts

```text
.engineer/security-audit/run-<NNN>/
  architecture.md            # brief: eight headings, ≤1000 words, bound by {path, sha256}
  coverage.json              # ledger: dimensions, units, waves, summary
  findings.json              # records (three verdicts), hardening_notes, summary
  agents/<agent-id>.json     # promoted agent results; parent-written only
  evidence/<fingerprint>/    # bound files, ≤1 MiB each, ≤32 MiB per run, no symlinks
  REPORT.md                  # target-neutral summary
  FINDINGS-DETAIL.md         # one section per confirmed record
  NEEDS-VALIDATION.md        # blockers and plans per needs_validation record
```

`receipt_kind` is `captured_run` for a real run (`target.source_ref` a 40-hex commit;
`reports[]` includes `REPORT.md` when complete), `illustrative_fixture` only for the shipped
samples. Evidence paths resolve under `artifact_root`; absolute, traversal, or symlink fails.

## Report sections

`REPORT.md`, in order: scope and authorization; sandbox and safety statement (the exact
`sandbox` and `safety` values); coverage summary (units per status, `incomplete_reason`);
confirmed findings, one line each (fingerprint, title, `overall`, boundary summary); needs
validation (blocker and cheapest plan step); hardening notes; rejected count with refutation
themes; carry-forward; method and independence (roles, host, serialization disclosure); residual
risk (uncovered cells, deferred units, classes the profile skipped). `FINDINGS-DETAIL.md` expands
each confirmed record (boundary, trace, evidence digests, conditions, severity reasoning,
remediation with layer and regression test); `NEEDS-VALIDATION.md` gives the `owner_observed`
steps verbatim. Target-neutral: no product names beyond the target's own, no praise, no
"secure" or "hardened" verdicts, counts only from the artifacts, one template for every run.

## Validators

Run from the target root; the ledger tool validates on every write, the validators run after
phase 5 and on every re-run:

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
RUN=.engineer/security-audit/run-001
python3 "$ENGINEER/scripts/security-ledger.py" init --dimensions "$RUN/dimensions.json" --run-id run-001 \
  --target-name app --profile standard --architecture architecture.md --output "$RUN/coverage.json"
python3 "$ENGINEER/scripts/security-ledger.py" assign "$RUN/coverage.json" --wave 1 --hunter hunter-a --critic critic-1 cov-0123456789ab
python3 "$ENGINEER/scripts/security-ledger.py" promote "$RUN/coverage.json" "$SCRATCH/hunter-a/result.json" --agent hunter-a --wave 1
python3 "$ENGINEER/scripts/security-ledger.py" gap "$RUN/coverage.json" --prior .engineer/security-audit/run-000
python3 "$ENGINEER/scripts/security-ledger.py" finish "$RUN/coverage.json"   # or --incomplete "<exact reason>"
python3 "$ENGINEER/scripts/validate-security-coverage.py" "$RUN/coverage.json" --evidence-root "$RUN" --target-root . --json
python3 "$ENGINEER/scripts/validate-security-findings.py" "$RUN/findings.json" --evidence-root "$RUN" --target-root . --json
```

`init` expands the dimensions file into `planned` units and binds the brief (path relative to
the run directory); `assign` opens or extends a wave for one hunter with a critic that hunts
nothing in it; `promote` admits one result after the regular-file, size, JSON, content-screen,
and assigned-unit checks and copies it to `agents/<agent-id>.json`; `gap` carries a prior run
forward; `finish` closes the run. The tool never executes target code. The validators exit
0 valid / 1 invalid / 2 unreadable, print `{valid, errors, gates}` with `--json`, and prove
record consistency, independence, budget arithmetic, coverage closure, and evidence binding,
never exploitability, the absence of vulnerabilities, or that the sandbox was enforced.

## Anti-patterns

- Pasting scanner output, grep hits, or advisory ids as findings; a flag alone is not a finding.
- Severity on a `needs_validation` record, or impact inflated by hypothetical reachability.
- A hunter verifying its own candidate; a critic that also hunts; one context playing every role
  without the disclosure; spending the reserve on one more wave; a budget stop relabelled
  `complete`.
- Running the target's test suite on the host "because it is just tests"; probing staging or
  production to "quickly confirm".
- Carrying a prior confirmation forward without a re-verification record; committing, pushing,
  or pasting the run directory; hand-editing fingerprints or coverage ids.
- Editing target source "while we are here"; remediation is `engineer fix`'s job, keyed by fingerprint.
- The word "secure" in a report.

**Related**: `security-attack-classes.md`, `security-audit-domains.md`,
`multi-agent-orchestration.md`, `agent-red-teaming.md`, `epistemic-honesty.md`, `system-assurance.md`
