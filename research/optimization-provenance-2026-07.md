# Cryptographic provenance for optimization evidence

**Date:** 2026-07-15

## Gap

The earlier receipt design binds every reported result to a captured trial artifact, but `captured_run`
and runner names are still claims made inside that artifact. A local actor can fabricate both,
recompute the digest, and present the result as genuine capture.

## Evidence

- SLSA v1.2 says verification must check the provenance signature, subject digest, trusted
  builder identity, predicate type, source repository, build type, and external parameters.
- The in-toto Statement v1 binds an attestation to immutable subjects by digest and identifies
  the predicate type unambiguously.
- GitHub artifact attestations bind a workflow identity, repository, revision, event, and
  artifact digest through an OIDC-backed Sigstore certificate. GitHub's verifier supports exact
  repository, workflow, workflow digest, source digest, source ref, predicate, and self-hosted
  runner policy.
- GitHub warns that most predicate contents are workflow-controlled. Certificate identity and
  verified timestamps carry stronger protection, so policy should pin the signer workflow and
  keep that workflow free of caller-controlled paths or commands.
- Offline verification needs the artifact, attestation bundle, and a recently exported trusted
  root. Both auxiliary files must be digest-bound because stale or substituted trust material
  changes the verification claim.

## engineer decision

1. A captured run may remain `reject` without an attestation so evidence can be produced before
   signing. It cannot become `promote` until cryptographic verification runs.
2. GitHub Sigstore promotion pins the exact repository, signer workflow, signer revision, source
   revision, source ref, SLSA predicate, bundle, trusted root, and hosted-runner policy.
   Repository, workflow, ref, predicate, issuer, and runner trust come from a separately supplied
   protected policy, not from the evidence producer's receipt.
3. `validate-optimization-run.py --verify-attestation` invokes the installed GitHub CLI with all
   policy flags, requires a successful JSON result, and independently confirms that a verified
   SLSA statement contains the captured evidence SHA-256 subject.
4. The verifier is opt-in so ordinary fixture and reject-path validation stays offline and
   dependency-free. Omitting the flag cannot accidentally promote a captured run.
5. The optional workflow template uses fixed repository paths and an immutable action revision.
   It first requires a captured-but-rejected receipt with no attestation, then signs only the
   exact trial artifact. It accepts no dispatch inputs.

## Applicability and limitations

GitHub artifact attestations for private or internal repositories require an eligible GitHub
Enterprise Cloud plan. Other private environments should use an equivalent trusted verifier;
engineer does not downgrade a missing cryptographic root into a successful promotion. The current
executable adapter is GitHub-specific, while the contract principles are vendor-neutral.

Verification trusts the installed `gh` binary, the supplied trusted-root snapshot, GitHub's
OIDC/Sigstore infrastructure, the pinned workflow, and the hosted runner. An attacker who can
change the trusted workflow or its pinned source revision is inside that trust base. Attestation
proves origin and integrity, not that graders, tasks, or conclusions were correct; the existing
semantic gates remain mandatory.

## Primary sources

- SLSA v1.2, *Verifying artifacts*: https://slsa.dev/spec/v1.2/verifying-artifacts
- SLSA v1.2, *Provenance*: https://slsa.dev/spec/v1.2/provenance
- in-toto, *Statement v1*: https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md
- GitHub CLI, `gh attestation verify`: https://cli.github.com/manual/gh_attestation_verify
- GitHub, *Verifying attestations offline*: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline
- GitHub, *Using artifact attestations*: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
