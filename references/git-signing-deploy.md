# Git commit signing and verified deploys

**Last verified:** 2026-07-15 · **Review cadence:** 3 months

Use this module whenever commit provenance, GitHub's Verified badge, co-authors, branch protection, rulesets, or deploy authorization matters.

## Trust model

Keep these claims separate:

1. `git verify-commit <sha>` proves that the commit object has a cryptographically valid signature for a locally trusted key.
2. GitHub's `commit.verification` proves that GitHub recognizes and verifies that signature for the commit shown on GitHub. Inspect both `verified` and `reason`; a local “Good signature” can still be `verified: false` with `reason: unknown_key`.
3. A verified signature does not prove review, CI success, dependency safety, author intent, or deployment approval. Those require independent controls.

Never describe a commit as GitHub Verified from local output alone.

## Author and co-author semantics

- `Co-authored-by:` trailers provide attribution. They do not add a second signature to the commit object and do not prove the co-author reviewed or approved the exact diff.
- One commit has one embedded commit signature. If every contributor must approve, use protected reviews or CODEOWNERS in addition to signing.
- Under vigilant mode, GitHub can label a signed commit “Partially verified” when a co-author has not signed. GitHub's required-signed-commits rule can still accept partially verified commits, so do not treat that rule as unanimous co-author approval.

## Diagnostic flow

```bash
git verify-commit HEAD
git log -1 --show-signature
gh api repos/OWNER/REPO/commits/SHA \
  --jq '.commit.verification | {verified,reason,signature,payload,verified_at}'
```

Common GitHub reasons include `unknown_key`, `unverified_email`, `bad_email`, `invalid`, `unsigned`, and `valid`. For SSH signing, register the public key with GitHub as a **signing key**, not only as an authentication key. Keep the private key outside the repository.

After repairing account/key association, create a new signed commit and verify that exact pushed SHA through the API. Do not assume historical commits are relabeled.

## Repository enforcement

For protected release branches, prefer a GitHub ruleset or branch protection rule with **Require signed commits**. Also require pull requests, approvals/CODEOWNERS where appropriate, status checks, conversation resolution, and protection from force pushes and deletions.

Native repository enforcement is the primary trust boundary because a workflow stored in the candidate commit can itself be modified. Pin third-party Actions by immutable SHA and give workflows least privilege.

## Deployment enforcement

Production deploys must use an immutable source SHA and fail closed unless GitHub reports:

```text
.commit.verification.verified == true
```

Use `templates/github/verified-deploy-gate.yml` as defense in depth. Make it a required status before the deploy job, and place production behind a protected GitHub Environment or equivalent platform approval. Re-check the exact deployment SHA; never substitute a moving branch head.

Required evidence for a verified-source deployment:

- immutable deployment SHA;
- GitHub verification boolean and reason for that SHA;
- required checks and review state;
- environment approval/deployment record;
- artifact provenance or digest when the build and deploy stages are separate.

## Sources

- [GitHub: About commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification)
- [GitHub: Displaying verification statuses for all commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/displaying-verification-statuses-for-all-of-your-commits)
- [GitHub: Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub REST: commits](https://docs.github.com/en/rest/commits/commits)
- [GitHub: Deployments and environments](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments)
