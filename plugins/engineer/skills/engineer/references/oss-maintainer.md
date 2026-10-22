# Open-source GitHub maintainer operations

**Last verified:** 2026-07-17 · **Review cadence:** 3 months

Use this module for public repositories, contributor workflows, governance, triage, releases, community health, project succession, and OSS supply-chain posture. Compose with `git-signing-deploy.md`, `skill-supply-chain.md`, `enforcement.md`, and `output-quality.md`.

## Start with the project profile

Record current maturity (`experimental`, `supported`, `critical`, `deprecated`), release artifact types, package registries, contributor count, maintainer/bus factor, security impact, support promise, and available GitHub plan/features. Apply controls proportionally. A solo experimental library and a widely deployed security component should not claim the same service level or require the same review quorum.

Never use OpenSSF Scorecard or an OSPS checklist as a vanity score. Pin an assessment to a named baseline version, retain evidence and exceptions, and prioritize exploitable release-path gaps over cosmetic completeness.

For authorized repository work, run `scripts/apply-oss-baseline.py --visibility public --apply --output <receipt>` after the audit, then replay the receipt with `scripts/validate-oss-application.py <receipt> --root <target>`. It may create only missing deterministic contribution intake, issue forms, PR contract, and a repository-aware Dependabot configuration derived from documented manifests and workflows. Detection is bounded, skips symlinks/generated trees, uses native multi-directory entries, records incomplete scans as receipt limitations, and never overwrites existing configuration. Filename-identifiable ecosystems are automatic; overlapping Terraform/OpenTofu `.tf` layouts require a tool-specific marker or an explicit project choice. The validator re-derives generated dependency policy, exact intended and observed file hashes, conflicts, unresolved project decisions and final decision from disk; manifest drift invalidates old evidence. License choice, private security contact, conduct enforcement, support promises, governance roles, registries, cooldown and grouping remain accountable project decisions; GitHub settings remain external mutations. Local replay proves final-state agreement, not prior absence, process identity or external host state.

## Private-context leak gate (binding)

Finding classes: **SECRET**, **DROPPER**, **WORM**, and **INVISIBLE_UNICODE** (CRITICAL, never
downgraded); **PATH**, **INFRA**, **PERSONAL**, **MARKER** (MAJOR). INFRA covers private IPs,
internal hostnames, SSH targets, and — since 2026-08 — cloud identifiers that map a deployment
topology: AWS ARNs/account ids/ECR/RDS/S3 hosts, GCP service accounts and `run.app`/`gs://`,
Vercel `prj_`/`team_` ids and `*.vercel.app` previews, Cloudflare/Fly/Railway/Render/Netlify/
Azure/Supabase hosts and 32-hex account/zone ids. Provider tokens (AWS temporary keys,
`sb_secret_`, `fo1_`, `nfp_`, `dop_v1_`, Azure storage keys, GCP key ids) are SECRET; credential
dot-dirs under the home directory (aws, kube, gcloud, azure, docker credential folders) are PATH. Documented
placeholders (`example`, `my-app`, `<project>`, AWS's sample account) never match. Real
identifiers belong in local config or a private markers file, not in a public tree.

Public repositories leak by accretion: a hardcoded corpus path in a test, a private venture name in a fixture, a working note with a real deal term. On 2026-07-17 an unmachined pull request initially shipped personal corpus paths and private repo/venture names into a public repo; a manual sanitize pass caught it only after review. This gate makes that check deterministic and mandatory.

Before any commit or push to a public repository, run the changeset through `scripts/check-oss-leaks.sh` (staged diff by default; `--all` for the full tree; `--ref <range>` for commit ranges). Finding classes: SECRET (CRITICAL: private-key blocks, credential-shaped assignments, known token prefixes, connection strings with embedded passwords, JWT shapes, credential-named env lines), PATH (personal home paths, ssh/aws dot-dirs), INFRA (private IPv4 ranges, internal hostname suffixes, ssh destinations), PERSONAL (emails beyond the repo's git identity, phone shapes), and MARKER (operator-specific names). CRITICAL always fails; MAJOR fails unless `--warn-only`; `--allow <ere>` admits reviewed public-identity exceptions such as a maintainer handle or attribution email.

The gate also catches obfuscated code-execution droppers from poisoned starter templates (class DROPPER, CRITICAL): a deobfuscation stage (base64, hex, `String.fromCharCode`, `\x`/`\u` escape runs, string-reversal, custom-alphabet or XOR) feeding a dynamic-execution sink (`eval`, `new Function`, `vm`, dynamic `import`, `child_process`, Python `exec`/`compile`, PowerShell encoded-command execution), fetch-then-exec shapes, decode-of-env/argv reaching a sink, and base64 blobs parked under env-var keys in committed env files. A finding needs the sink and an encoder/fetcher to co-occur, so a lone base64 blob, lone `eval`, or lone config never matches. This is a live starter-template supply-chain pattern, found in public repos on 2026-07-17. The gate adds an INVISIBLE_UNICODE class (CRITICAL) for zero-width, bidi, PUA, tag, and supplementary variation-selector codepoints - the GlassWorm (2025-10) class that hides executable text from human review and token scanners.

**Known Tier-1 limitation (deliberate, documented).** `check-oss-leaks.sh` is a *same-file* regex gate. The 2026-07-17 anchor incident's real payload was *cross-file* - a base64 URL parked in a committed `.env` under an env-var key, decoded and executed by a *separate* vite/vitest config. A single-file pattern cannot bridge that split, and the gate does not fake cross-file detection with a brittle heuristic: ENVB64 flags the `.env` carrier in isolation, and the config-side decode-to-sink is caught only when both stages share a file. Closing the config-to-`.env` gap is the job of Tier 2 - AST/dataflow taint that follows a decode source to an exec sink across files (Semgrep Pro / CodeQL), named as the future closure in `references/malware-detection.md` (dropper taxonomy, method-tiering, and false-positive doctrine) and `references/enforcement.md` (CI tiers). State the boundary; do not claim the regex closed it.

The operator-specific layer never ships with any repository, this one included. Generic detection lives in the script; private names live in a local marker file (`$ENGINEER_PRIVATE_MARKERS`, else `~/.config/engineer/private-markers.txt`) with `[names]`, `[business]`, and `[paths]` sections, plus a `[public]` section listing repos known to be public. A missing marker file downgrades to the generic layer with one warning. The marker file is itself a map of private names: create it `chmod 600`; the scanner warns when it is group- or world-readable.

Content rules the scan enforces:

- Personal configuration belongs in local config files outside the repo; code reads defaults from config or environment with None/empty fallbacks, never from a hardcoded operator value.
- Test fixtures use neutral placeholders (a `/Users/example` style path, an `example.com` address), never a real home directory, account, or contact.
- Docs describe source types and configuration shapes, not the operator's machine layout.

Public-repo detection: `gh repo view --json visibility` when `gh` is available and authenticated; otherwise membership in the marker file's `[public]` section. `--public-only` auto-skips repos not known public, which makes the gate safe in unconditional pre-commit hooks. `--gitleaks` adds the gitleaks binary as an optional secrets accelerator when installed; the deterministic layer runs either way.

## Community contract

The default branch should make these discoverable:

- `README`: purpose, status, supported use, install/quickstart, compatibility, security link, support boundary and license.
- `LICENSE`: an intentional SPDX-recognized license; do not infer permission from a public repository.
- `CONTRIBUTING`: environment, tests, style, review path, DCO/CLA choice, provenance and generated/AI-assisted contribution policy.
- `CODE_OF_CONDUCT`: scope, enforcement contacts and response process; do not publish a policy with no accountable recipient.
- `SECURITY`: supported versions, private reporting channel, expected acknowledgement range, disclosure coordination and safe-harbor language reviewed for the project.
- `SUPPORT`: where questions, bugs, discussions and paid support belong; state what maintainers do not promise.
- `GOVERNANCE` when more than one decision-maker or downstream dependency exists: roles, decision/appeal process, release authority, inactivity and succession.

Use structured issue forms for reproducible bugs and scoped features, a security chooser that points away from public issues, and a PR template that asks for intent, linked issue, risk, tests, compatibility, docs and release-note impact. Templates improve inputs; they do not authorize closing valid reports that use another format.

## Access and merge policy

- Grant the least repository role needed; review inactive collaborators and machine accounts.
- Maintain at least two independent recovery-capable maintainers for critical projects where feasible; disclose the bus-factor risk when not feasible.
- Put `CODEOWNERS` in `.github/`, protect `.github/` or `CODEOWNERS` itself, and remember one listed owner approval can satisfy GitHub's code-owner rule unless additional review rules say otherwise.
- Protect default and release branches with rulesets: pull requests, required checks, conversation resolution, signed commits, last-push approval where supported, stale-review dismissal for material changes, and no force-push/deletion.
- Keep bypass actors minimal, named and auditable. Emergency bypass requires an incident record and retrospective review.
- A solo maintainer cannot manufacture independent review. Require reproducible CI/evidence and be explicit about that limitation rather than adding a meaningless self-approval ritual.

## Workflow and contribution trust

Fork and issue content, branch names, contributor-controlled files, generated patches and bot/agent output are untrusted. Workflows must use top-level read-only permissions, job-scoped writes, SHA-pinned third-party Actions, `persist-credentials: false` when checkout credentials are unnecessary, and no secrets or privileged writes in untrusted PR execution. Treat `pull_request_target` as a privileged boundary; never execute the fork's code in that context.

Human and AI-assisted contributions have the same acceptance contract: attributable author responsibility, license/provenance compatibility, focused diff, understandable rationale, passing evidence and review. Do not accept polished prose as proof, and do not reject solely from an unreliable "AI-generated" score. Apply `unmachined` to project-owned public copy and UI; evaluate external contributions on concrete quality and policy violations.

## Vulnerability operations

- Publish `SECURITY.md` and enable private vulnerability reporting for eligible public repositories.
- Triage privately, preserve reporter credit preference, establish affected versions, develop and validate the fix in the advisory/private fork, request a CVE when appropriate, and coordinate disclosure with a patched release.
- Do not ask for exploit details in a public issue. Do not promise a response SLA the maintainer team cannot sustain.
- Enable the dependency graph, Dependabot alerts/security updates, secret scanning/push protection and CodeQL/dependency review where available and proportionate. Document unavailable paid features rather than claiming coverage.
- Define supported branches and backport policy; publishing a fix only on `main` is not remediation for supported release lines.

## Release integrity

Release only from a reviewed protected ref and an isolated least-privilege workflow. Bind source commit, tag, build instructions, artifact digests, dependency lock state and publication identity. Prefer immutable GitHub releases: assemble a draft and all assets, verify them, then publish once. Generate artifact attestations and an SBOM for distributable binaries/packages when supported; consumers must verify provenance and digest, not merely a badge.

Use signed/verified source commits and tags as provenance inputs, not proof of code review or correctness. Never move a published version tag or replace an asset under the same version. Revoke and publish a new version if a release is bad.

## Sustainable triage and governance

- Labels describe type, status, impact and contributor readiness; avoid a taxonomy that maintainers cannot keep current.
- Keep decisions in one authoritative issue/discussion/ADR and link duplicates.
- Triage by security, data loss, release regression, accessibility and supported-user impact before popularity.
- Automate reminders and deduplication cautiously. Never auto-close a reproducible unanswered issue merely because the reporter did not post activity.
- Credit reporters and contributors; `Co-authored-by` is attribution, not cryptographic approval.
- Publish deprecation, archive, transfer and succession procedures. An archived project needs a final status, security/support boundary and migration path.

## Maintainer health signals

Use trends for decisions, not individual performance: untriaged issue age by severity, review wait and stale-PR age, CI flake rate, release cadence versus promise, supported-version vulnerability age, contributor conversion/return rate, maintainer concentration and unanswered support load. Pair numbers with capacity and project status. Fast closure, raw commit count and Scorecard score are not outcome metrics.

## Sources

- [OpenSSF OSPS Baseline 2026.02.19](https://baseline.openssf.org/)
- [OpenSSF Scorecard checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md)
- [GitHub: repository security quickstart](https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository)
- [GitHub: CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub: issue and pull-request templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates)
- [GitHub: repository security advisories](https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/repository-security-advisories)
- [GitHub: immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [GitHub: artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
