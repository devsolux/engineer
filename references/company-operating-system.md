# Company operating-system engineering

**Last verified**: 2026-07-16 · **Review cadence**: 3 months
**Related**: `product-business-engineering.md`, `system-assurance.md`, `product-analytics.md`, `audit-log.md`, `compliance-privacy.md`

Use this module when software, data, automation, or AI touches how a company is governed, led, staffed, financed, marketed, sold, secured, or held accountable. Engineer models the whole company so it can build the right system. It does not replace executives, the board, HR, finance, or qualified counsel.

## Boundary

| Question | Owner |
|---|---|
| What market, company strategy, organization, executive hire, capital allocation, or risk appetite should we choose? | the private strategy skill, accountable executives, board |
| What does applicable law require in this jurisdiction and fact pattern? | Qualified counsel or regulated professional |
| How does an accepted policy become permissions, workflow, data, controls, evidence, and reliable software? | Engineer |
| Does the implementation expose a policy contradiction, missing owner, unsafe incentive, or unworkable control? | Engineer must challenge and escalate |

Never encode a generic role description as company truth. Stage, ownership form, jurisdiction, industry, workforce model, financing, risk, and named delegations determine the real authority map.

For function-level reference depth (finance, legal, people, risk, leadership frameworks and benchmarks), load the matching **business-knowledge reference skill** domain module; the knowledge grounds the build while the owners above keep every decision.

## Company truth model

Before building a management system, establish:

- purpose, customers, business model, stage, legal entities, jurisdictions, and material stakeholders;
- board-reserved matters, executive accountabilities, delegations, approval thresholds, and conflicts;
- operating model, teams, decision rights, meeting cadence, escalation paths, and continuity owners;
- goals, budgets, forecasts, constraints, risk appetite, obligations, policies, and source-of-truth systems;
- employee and contractor lifecycle, worker voice, accommodations, safety, investigations, and protected reporting;
- product, customer, vendor, cash, revenue, data, security, compliance, and incident lifecycles.

Treat a title as a routing hint, not proof of authority. Record accountable owner, decision right, consulted roles, evidence, deadline, reviewer, and appeal or escalation route for consequential decisions.

## Executive and function interfaces

| Function | Accountable outcomes | Engineer implementation surfaces |
|---|---|---|
| Board / owners | strategy oversight, executive accountability, material risk, conflicts, succession | board pack inputs, reserved-matter workflow, conflict register, immutable decisions, attestations |
| CEO | integrated company performance, priorities, culture, resource proposals | outcome tree, constraint view, decision log, cross-functional commitments, exception queue |
| COO / operations | operating cadence, service delivery, capacity, quality, continuity | workflow states, SLAs, capacity model, runbooks, controls, incident and improvement loops |
| CTO / CIO | technology strategy execution, architecture, delivery, reliability, data and technical risk | portfolio-to-architecture trace, DORA and reliability evidence, tech-risk register, lifecycle and cost controls |
| CISO / security | risk governance, protection, detection, response, recovery, supply chain | NIST-aligned roles, policies, asset/risk evidence, exceptions, incidents, third-party controls |
| CFO / finance | cash, controls, accounting integrity, forecast, capital and unit economics | close workflow, segregation of duties, budget/actuals, forecast versions, approval policy, audit trail |
| CMO / marketing | market learning, demand, brand, truthful claims, channel economics | claim substantiation, campaign taxonomy, consent, attribution, experiments, pipeline and retained-revenue reconciliation |
| CRO / sales / success | predictable revenue, customer fit, commercial policy, retention and expansion | lifecycle states, territories, quotes, approvals, CRM/product/billing reconciliation, renewal and loss reasons |
| CPO / product | customer outcomes, portfolio choices, discovery, value and product risk | opportunity evidence, outcome roadmap, acceptance IDs, release cohorts, kill gates, feedback provenance |
| CHRO / people | fair workforce systems, capability, performance, relations, safety, succession | role and skill model, structured lifecycle workflow, access separation, case handling, aggregate workforce metrics |
| General counsel / legal ops / DPO | legal risk, contracts, entity/IP/records/privacy obligations and advice | matter and contract lifecycle, obligation register, retention/legal hold, consent/rights workflow, privilege boundaries |
| Procurement / vendor management | value, resilience, third-party risk and obligations | due diligence, approvals, contract-to-control trace, inventory, renewal/exit workflow, concentration alerts |
| Support / service | customer recovery, issue learning, promise integrity | case taxonomy, severity/SLA, entitlement-safe access, escalation, root-cause and product feedback loops |

Small companies may combine roles. Preserve separation of duties for conflicting actions even when one person holds several titles; require an independent approver or board-level exception where risk warrants it.

## Human-relations and leadership controls

- Optimize for psychological safety **and** accountability: safe questions, dissent, error reporting, clear expectations, dependable follow-through, meaningful work, and visible impact.
- Give workers more than one safe reporting path. Restrict case access, prohibit retaliation, preserve evidence, separate allegation from finding, and require impartial human investigation.
- Do not automate hiring, promotion, discipline, compensation, termination, accommodation, or investigation outcomes from opaque scores. Provide notice, relevant evidence, correction, human review, and appeal appropriate to consequence and law.
- Collect the minimum workforce data. Separate medical, accommodation, grievance, compensation, performance, and investigation access. Aggregate leadership reporting and suppress unsafe small cohorts.
- Make objectives, decision rights, performance criteria, feedback cadence, development, and escalation explicit. Activity surveillance and message volume are not performance.
- Treat reorganizations, layoffs, return-to-office policy, executive compensation, succession, and collective workforce matters as accountable human decisions with jurisdiction-specific review.

## Control and decision architecture

For every material workflow define:

```yaml
objective: intended company and stakeholder outcome
policy_owner: accountable human role
decision_right: who may decide and within what threshold
inputs: authoritative records and freshness
states: explicit lifecycle and allowed transitions
controls: preventive, detective, corrective
separation: requester, approver, executor, reviewer
evidence: immutable facts needed to reconstruct the decision
exceptions: expiry, compensating control, approver
appeal_or_escalation: safe route and SLA
metrics: outcome, leading indicator, guardrail, data quality
review: cadence, trigger, owner, change history
```

High-risk controls need real operation evidence, not policy presence. Test unauthorized, conflicted, duplicate, late, missing-data, retaliation, override, rollback, and continuity cases. Reconcile across finance, product, CRM, HRIS, identity, support, contract, and warehouse systems.

## Management information

- Start from decisions, not a universal executive dashboard. Separate board oversight, executive outcomes, operating queues, analysis, incidents, and regulated reporting.
- Every metric has definition, population, unit, owner, source, freshness, comparison, target, uncertainty, drill path, and decision rule.
- Pair speed, volume, utilization, revenue, and productivity measures with quality, customer, worker, safety, security, cash, and long-term guardrails.
- Never expose individual-sensitive people data to broad dashboards or infer culture from chat, keystrokes, hours online, or sentiment alone.
- Surface conflicts between targets. Do not silently optimize local function metrics against company value or stakeholder safety.

## Legal and professional boundary

Engineer can build issue spotting, obligation inventories, review gates, evidence preservation, and jurisdiction-aware configuration. It must not invent a legal conclusion, employment classification, tax treatment, accounting judgment, fiduciary decision, privilege claim, filing deadline, or mandatory policy. Record jurisdiction, entity, effective date, source, counsel/owner, review date, and unresolved questions. High-consequence or disputed matters fail closed pending the accountable professional.

## Completion gate

Do not call a company system ready until:

1. authority and policy sources are named;
2. roles, conflicts, thresholds, states, exceptions, and appeals are explicit;
3. privacy, labor, accessibility, security, financial, records, and legal boundaries are assessed;
4. integrations reconcile and continuity works when a person or vendor is unavailable;
5. negative, abuse, override, rollback, and incident paths pass;
6. owners can operate the workflow and workers/customers can understand and contest consequential outcomes;
7. residual risks, professional reviews, and unverified external state are reported.

---

Research and primary sources: `research/company-leadership-operations-2026-07.md`.
