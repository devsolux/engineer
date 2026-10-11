# Prompt template: bug fix

```
engineer fix - [symptom]

Goal: [expected behavior]
Repro: [steps or error message]
Diagnose: trace to first causal divergence before patching (root-cause-engineering.md)
Scope: minimal diff at the causal site; no silent symptom patch
Do NOT: refactor surrounding code; mask the symptom (retry/guard/timeout) without a declared mitigation
Verify: [specific test or manual step]
Report: "root-cause fixed" vs "mitigated" (mitigation needs owner + expiry + tracked follow-up)
```
