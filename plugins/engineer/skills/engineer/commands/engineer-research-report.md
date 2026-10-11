---
description: Build markdown report from deep-research JSON results.
---

# /engineer-research-report

Load engineer `SKILL.md` + **`references/deep-research.md`**.

Mode: **Phase 3 REPORT**.

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
: "${ENGINEER:?Set ENGINEER to the resolved skill directory}"
python3 "$ENGINEER/scripts/research-report.py" \
  --topic-dir ./{topic_slug} \
  --toc-fields github_stars,license,recommendation_tier
```

Optional HITL: which fields appear in TOC.

## Output

`{topic_slug}/report.md` — then hand off to `engineer plan` if implementing a pick.
