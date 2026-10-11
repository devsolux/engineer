# Agent incident response research - 2026-07

## Decision

engineer needs a dedicated post-compromise path. Preventive security, red-team catalogs, feature kill
switches, and skill admission did not prove evidence preservation, complete containment, persistence
hunting, clean recovery, or defensible closure after an agent crossed a trust boundary.

## Primary-source findings

- NIST SP 800-61 Rev. 3 (April 2025) integrates preparation, detection, response, recovery, and
  improvement across the CSF 2.0 functions rather than treating response as a detached linear task.
- CISA's federal playbook preserves evidence before eradication, plans for multiple persistence
  mechanisms, restores from clean gold sources, monitors for re-entry, and returns to analysis when
  new activity appears.
- GitHub's incident guidance makes containment proportional, prioritizes credential revocation,
  rotates possibly exposed secrets, and audits persistence. Bulk revocation can itself be disruptive.
- OWASP's 2026 agentic taxonomy highlights propagation through agents, tools, workflows, durable
  state, and poisoned memory. General host cleanup is therefore insufficient for an agent system.

## engineer adaptation

The receipt adds agent-specific evidence and persistence surfaces: prompt/context provenance, tool
arguments, skills and instruction files, MCP, hooks, browser profiles, schedules, RAG and durable
memory, checkpoints, delegated agents, and downstream side effects. It requires revocation before
rotation, rejects contaminated-state reuse, binds recovery to an immutable digest, and keeps
illustrative fixtures from claiming closure.

## Limits

The validator proves receipt consistency and local artifact hashes, not absence of compromise.
Organization-specific legal, privacy, insurer, vendor, and law-enforcement duties still require the
appropriate humans. Defensive tests must remain isolated and synthetic.

## Sources

- https://csrc.nist.gov/pubs/sp/800/61/r3/final
- https://www.cisa.gov/sites/default/files/2024-08/Federal_Government_Cybersecurity_Incident_and_Vulnerability_Response_Playbooks_508C.pdf
- https://docs.github.com/en/code-security/tutorials/secure-your-organization/respond-to-a-security-incident
- https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
