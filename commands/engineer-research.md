---
description: Deep research outline — items + fields for stack/library/competitor decisions.
---

# /engineer-research

Load engineer `SKILL.md` + **`references/deep-research.md`**.

Mode: **Phase 1 OUTLINE only** — produce `{topic_slug}/outline.yaml` + `fields.yaml`.  
No deep agent fan-out until user runs `/engineer-research-deep`.

User's research topic follows this invocation.

## Steps

1. Infer engineering preset if clear (`library-eval` | `stack-selection` | `competitor-tech` | `security-landscape`) from `templates/research/`.
2. Draft items + fields from model knowledge; HITL confirm.
3. Web-supplement with one background search agent (prompt template in deep-research.md).
4. Write outline + fields under `./{topic_slug}/`.
5. Stop and show paths; next: `/engineer-research-deep`.

## Output

```
{topic_slug}/
  outline.yaml
  fields.yaml
```
