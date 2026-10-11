---
description: Compile a product requirement into a traceable goal, acceptance, plan, tests, and evidence contract
---

# /engineer-prd

Load `references/prd-to-evidence.md`, then the relevant domain modules. Convert `$ARGUMENTS`
into a PRD whose requirement IDs map to acceptance criteria, plan steps, tests or evals, and
named evidence. Resolve decision-changing unknowns before implementation. For agentic work,
emit and validate `templates/agentic/execution-contract.sample.json`.
