# OSS GitHub maintainer research — 2026-07

## Finding

Engineer needed an OSS operating model spanning community intake, governance, access, vulnerability coordination, release integrity and maintainer sustainability. Generic “add badges and templates” advice is insufficient and can increase burden without reducing risk.

## Standards and current platform evidence

- OpenSSF OSPS Baseline's current version is `2026.02.19`. It is a versioned minimum-control framework organized by project maturity.
- OpenSSF Scorecard measures observable repository practices. Some effective settings need administrator access to evaluate, so public results can be incomplete.
- GitHub recommends protecting CODEOWNERS itself; one of multiple owners can satisfy a code-owner approval rule.
- GitHub private vulnerability reporting and repository security advisories enable coordinated private fix/disclosure for public repositories.
- Immutable GitHub releases lock tags and assets and automatically receive a release attestation. The recommended publication flow is draft, attach all assets, then publish.
- Artifact attestations bind build provenance including repository, workflow and commit SHA; they do not prove artifact safety.

## Proportional design decision

Ship one progressive-disclosure reference, one evidence receipt and one eval. Do not add a project-management bot, hosted metrics collector, mandatory CLA/DCO, universal two-reviewer rule or automatic issue closer. Those depend on project governance, contributor volume, legal posture and maintainer capacity.

## Primary sources

- https://baseline.openssf.org/
- https://github.com/ossf/scorecard/blob/main/docs/checks.md
- https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/repository-security-advisories
- https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases
- https://docs.github.com/en/actions/concepts/security/artifact-attestations
