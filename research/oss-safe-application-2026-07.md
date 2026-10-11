# Safe automatic OSS repository application - July 2026

## Finding

Engineer's previous OSS path detected and audited public repositories but had no
executable local remediation step. That made "automatically apply safe baselines"
a policy claim rather than a reproducible capability.

GitHub recognizes repository-local community health files in the root, `.github`,
or `docs`, while issue forms must live under `.github/ISSUE_TEMPLATE` and contain
valid names/descriptions. A repository-local issue-template directory also masks
account-level default issue templates, so adding it must be a complete intentional
intake surface rather than one isolated form.

The OSPS 2026.02.19 baseline requires contribution guidance and, at higher maturity,
a real private vulnerability-reporting path. It does not justify fabricating a
security address, support promise, governance role, conduct enforcer, or license.
GitHub likewise tells maintainers to choose a code of conduct they can enforce.

## Implemented boundary

The offline applicator:

- requires confirmed public visibility and an explicit `--apply` mutation flag;
- atomically creates only missing deterministic files: contribution guidance,
  complete bug/feature issue intake, PR evidence contract, and a repository-aware
  Dependabot configuration for supported manifests and GitHub Actions;
- hashes every intended file and records the replayable outcome
  `planned_create`, `present_canonical`, `existing_conflict`, or
  `blocked_symlink`; it does not claim whether canonical content was newly
  created or already present;
- never overwrites project-owned content and treats symlink destinations as a
  conflict;
- leaves README facts, license selection, security contact/supported versions,
  conduct enforcement, support commitments, and governance roles as named project
  decisions;
- performs no GitHub setting, access, release, package, or vulnerability-reporting
  mutation.

This is intentionally not a generic "make my repo compliant" generator. Generated
policy promises without an accountable operator are worse than an explicit gap.
After application, Engineer re-runs the local audit and separately verifies effective
host state through GitHub evidence.

## Receipt replay

Schema v1 repeated intended hashes but had no independent consumer. Schema v2 records
the exact canonical template-set digest plus separate intended and observed hashes.
`validate-oss-application.py` re-derives the applicable templates from the target,
hashes canonical templates and current files, confines every relative path, replays
symlink/conflict status, reconstructs unresolved project decisions, and derives the
final decision. Forged paths, hashes, operation coverage, authority claims, decisions,
mode, or later target drift fail.

This follows the useful part of provenance verification: match the claimed subject to
the artifact digest rather than trusting a producer field. It is not signed provenance.
A local replay does not establish who ran the applicator, prove that a file was absent
before the run, or attest GitHub settings. Strong process identity would require a
trusted builder and verifier policy, which would be disproportionate for ordinary local
community-file scaffolding.

## Repository-aware dependency updates

GitHub requires each Dependabot update entry to name a supported ecosystem and one
`directory` or `directories` scope. The baseline now detects allowlisted manifests
without parsing project code: npm covers npm, pnpm and Yarn; uv remains distinct from
pip; and supported Go, Rust, Ruby, PHP, Java, .NET, Elixir, Dart, Bun, Deno,
Terraform, Docker, Compose, devcontainer and GitHub Actions layouts map to their
documented ecosystem values. Multiple directories for one ecosystem use the native
`directories` form.

Detection is deterministic and deliberately bounded to four repository levels and
128 ecosystem-directory matches. It skips symlinked files and common generated or
vendored trees. Crossing a bound is recorded as a receipt limitation rather than
silently claiming complete coverage. Existing Dependabot configuration is never
overwritten. Alternate `.yaml` spelling and recognized Renovate configuration
are treated as project-owned updater policy, so Engineer requests review instead
of creating a competing bot configuration. A manifest addition, removal, or relocation changes the generated
content hash, so an older application receipt fails replay. The default stays weekly
with five open PRs; grouping, cooldown, private registries and update policy remain
project decisions because they affect review load, freshness, credentials, and risk.

The expanded catalog adds only conventional, filename-identifiable manifests from
GitHub's current support contract and first-party file fetchers: Bazel, Conda,
.NET SDK, Elm, Git submodules, Helm, Julia, Nix flakes, pre-commit, Rust
toolchains, sbt, Swift, and vcpkg. Compound contracts stay compound: Nix requires
both flake files, Julia requires a project manifest, and .NET SDK requires `global.json`.
OpenTofu-specific `.tofu` or Terragrunt files map to `opentofu`; Terraform requires
both `.tf` input and `.terraform.lock.hcl`. A bare `.tf` tree can belong to either
tool, so Engineer records the ambiguity and omits that directory rather than choosing
an updater from filename probability.

## Sources

- [GitHub community profiles](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories)
- [GitHub default community health files and issue-template precedence](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [GitHub code of conduct adoption and enforcement responsibility](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/adding-a-code-of-conduct-to-your-project)
- [GitHub Dependabot-supported package managers](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)
- [GitHub Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
- [Dependabot Core file fetchers](https://github.com/dependabot/dependabot-core)
- [GitHub Actions secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [OpenSSF OSPS Baseline 2026.02.19](https://baseline.openssf.org/versions/2026-02-19.html)
- [SLSA artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts)
- [Python file-descriptor and no-follow controls](https://docs.python.org/3/library/os.html)
