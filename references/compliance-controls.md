# Compliance controls: framework-to-control mapping

**Last verified**: 2026-07-16 · **Review cadence**: 6 months

**Mapper, not auditor.** This module maps compliance frameworks onto controls engineer
already engineers and onto the repo's receipt/validator evidence pattern. It never
determines certification scope, interprets law, or claims compliance status — see
[Hard boundary](#hard-boundary). GDPR engineering controls live in
`compliance-privacy.md`; this module adds the framework view on top.

## Contents
- [Framework → existing-control map](#framework--existing-control-map)
- [Gap-assessment workflow](#gap-assessment-workflow)
- [Controls register output](#controls-register-output)
- [Evidence-collection discipline](#evidence-collection-discipline)
- [Hard boundary](#hard-boundary)
- [Related](#related)

## Framework → existing-control map

Framework themes below are engineering-level summaries (SOC 2 common criteria,
ISO 27001 Annex A themes, GDPR), not authoritative criteria text.

| Framework theme | What auditors look for | Existing engineer control |
|---|---|---|
| Access control (SOC 2 CC6 / ISO A.5.15-A.5.18) | Least privilege, joiner/leaver, admin access | `backend-auth.md`, RLS + `check-rls-migration.sh` gate, `backend-admin.md` break-glass, `infra-security.md` IAM |
| Change management (SOC 2 CC8 / ISO A.8.32) | Reviewed, authorized, traceable changes | PVE plan artifacts + `validate-plan.sh`, signed commits + verified-deploy gate (`git-signing-deploy.md`), CI gates (`enforcement.md`) |
| System operations & monitoring (CC7 / ISO A.8.15-A.8.16) | Logging, alerting, anomaly detection | `observability.md`, `audit-log.md` append-only events, CSP reporting pipeline (`backend-security.md`) |
| Incident management (CC7.3-CC7.5 / ISO A.5.24-A.5.27) | Documented response, containment, lessons | `agent-incident-response.md` + incident receipt validator; breach prep in `compliance-privacy.md` |
| Vendor / supply chain (CC9 / ISO A.5.19-A.5.23) | Third-party risk assessment | `skill-supply-chain.md` admission receipts, `mcp-security.md`, dependency policy (`backend-security.md`, `oss-maintainer.md`) |
| Secure development (ISO A.8.25-A.8.31) | SDLC controls, testing, secrets hygiene | Hard gates + `engineer-scan.sh`, gitleaks (`enforcement-rules.md`), `backend-testing.md` / `frontend-testing.md` |
| Infrastructure & network (ISO A.8.20-A.8.23) | Network security, hardening, backups | `infra-security.md` (exposure, SSH, containers, backup/DR) |
| Availability & resilience (SOC 2 A1) | Backups, recovery, capacity | `infra-security.md` backup/DR, `deploy-ops.md` rollback, `background-jobs.md` retries |
| Privacy / data subject rights (GDPR; SOC 2 P-series) | Export, delete, consent, retention, minimization | **already partially covered**: `compliance-privacy.md` (DSAR export/delete, consent, retention jobs, data inventory), `audit-log.md` retention |
| Data classification & retention (ISO A.5.12-A.5.14) | Inventory, labels, retention schedules | `compliance-privacy.md` data-inventory table + retention jobs |

## Gap-assessment workflow

1. **Pick the target framework** (one at a time — SOC 2 Type I/II, ISO 27001, GDPR
   readiness). Confirm with the user *why* (customer demand, deal blocker, market entry);
   this scopes effort and routes strategy questions to `company-operating-system.md`.
2. **Walk the mapping table** control by control against project truth: read the actual
   repo, CI config, infra state, and policies — never assume a mapped module is deployed.
3. **Classify each control**:
   - **met-by-evidence** — a control exists *and* produces retained artifacts
     (receipts, audit events, CI runs, signed commits);
   - **met-by-policy** — a written rule exists but nothing captures proof it runs;
   - **gap** — neither. Met-by-policy is a half-state: auditors sample evidence,
     so plan the promotion to met-by-evidence.
4. **Output a controls register** (below) with a named owner per control. Unowned
   controls are gaps regardless of implementation state.
5. **Engineer the gaps** through the normal owning modules (this module routes;
   it does not duplicate their content), re-classify, and keep the register current.

## Controls register output

```markdown
## Controls register: [framework] — [date]
| Control | Framework ref | State | Evidence source | Owner | Gap action |
|---|---|---|---|---|---|
| Audit trail on member changes | CC7.2 | met-by-evidence | audit_events table + retention job | [name] | — |
| SSH hardening on edge nodes | A.8.20 | met-by-policy | runbook only | [name] | capture config scan in CI |
| DR restore testing | A1.3 | gap | — | [name] | scheduled restore test + dated record |
```

State the register's limits in the document itself: it is an engineering readiness
view, not an audit opinion.

## Evidence-collection discipline

The repo's receipt/validator pattern **is** compliance evidence when retained:

- **Completion receipts** (`validate-agentic-completion.py`) prove change verification.
- **Plan artifacts** (`.engineer/plan.json`) prove authorized, reviewed change intent.
- **Audit events** (`audit-log.md`) prove operational monitoring of sensitive actions.
- **Incident receipts** (`validate-agent-incident.py`) prove response capability.
- **Admission receipts** (`skill-supply-chain.md`, `mcp-security.md`) prove vendor/tool
  review.
- **Signed commits + verified-deploy gate runs** prove change provenance.

Discipline:

- Retain evidence for the audit window (SOC 2 Type II samples across the whole period —
  evidence deleted at 30 days cannot support a 12-month audit).
- Evidence is generated by the control running, never reconstructed after the fact;
  backfilled artifacts are misrepresentation, not evidence.
- Access-separate evidence stores from the identities they attest (same principle as
  backup separation in `infra-security.md`).
- Redact secrets and minimize PII in retained artifacts — evidence must not become
  a new data-protection liability (`observability.md` § privacy in logs).

## Hard boundary

engineer **maps and engineers controls**. It does not:

- claim or certify compliance status ("we are SOC 2 compliant" requires an auditor's
  opinion; "GDPR compliant" is a legal conclusion) — outputs say "controls mapped /
  gaps identified" instead;
- decide certification scope, trust-service-criteria selection, or audit timing —
  that is a governance decision routed to `company-operating-system.md` and its
  accountable owners;
- interpret legal requirements for a jurisdiction or fact pattern — qualified counsel
  owns that (`compliance-privacy.md` carries the same rule);
- select or engage auditors, or negotiate findings — human decision with counsel.

When a user asks "are we compliant?", answer with the register: what is met by
evidence, what is met by policy, what is a gap, and who owns each — then route the
certification question to governance and counsel.

## Related

- `compliance-privacy.md` — GDPR engineering controls (export/delete, consent, retention)
- `audit-log.md` — append-only evidence trail for sensitive actions
- `infra-security.md` — infrastructure controls the frameworks sample
- `company-operating-system.md` — governance, accountable owners, legal boundary
- `agent-incident-response.md` / `skill-supply-chain.md` — incident and vendor receipts
- `git-signing-deploy.md` / `enforcement.md` — change-management provenance and CI gates
