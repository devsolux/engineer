---
description: Design and run authorized, isolated defensive security evaluations for an AI agent
---

# /engineer-red-team

Load `references/agent-red-teaming.md`, `references/ai-security.md`, and
`references/ai-evals.md`. Confirm `$ARGUMENTS` is an owned or explicitly authorized target.
Use isolated fixtures, synthetic data, inert canaries, disabled destructive actions, and denied
or simulated egress. Cover the relevant threat categories, pair adversarial cases with benign
controls, grade end state and tool arguments, record cleanup and residual risk, and promote every
confirmed weakness into regression coverage. Do not test live third-party or production targets.
