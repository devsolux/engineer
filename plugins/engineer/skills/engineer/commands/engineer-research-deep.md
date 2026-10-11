---
description: Parallel deep research of outline items into validated JSON results.
---

# /engineer-research-deep

Load engineer `SKILL.md` + **`references/deep-research.md`**.

Mode: **Phase 2 DEEP** — fill each outline item via web-search agents.

## Steps

1. Locate `*/outline.yaml` + sibling `fields.yaml`.
2. Resume: skip items that already have valid JSON in `results/`.
3. Batch by `execution.batch_size`; parallel agents; HITL between batches.
4. After each JSON:

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
: "${ENGINEER:?Set ENGINEER to the resolved skill directory}"
python3 "$ENGINEER/scripts/research-validate-json.py" -f fields.yaml -j results/Item.json
```

5. Load web-search modules from `references/web-search-modules/` as needed.
6. Summary: completed / failed / uncertain.

## Done when

All required fields present for completed items (validate script PASS).
