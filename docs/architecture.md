# Architecture and responsibility boundaries

```text
User task + repository instructions
                 |
                 v
Host model -> SKILL.md router -> focused command/reference workflow
                 |                              |
                 +------------------------------+
                 v
Existing host tools + deterministic repository scripts
                 |
                 v
Measured results, evidence validation, and honest completion report
```

The host owns intent interpretation, tool choice, and presentation within its
permissions. The router chooses the workflow; references supply specialist
instructions without introducing another agent. Scripts validate inputs, artifacts,
state, and bounded execution. Authorization and hard limits cannot be delegated
to prose or model output.

Packaging is a build-time transformation. Canonical source is copied into one
`skills/engineer` bundle. Generated host manifests describe discovery; Claude
command wrappers point into that bundle. No copied domain logic is maintained
independently. Both marketplace catalogs select the same generated directory.

The source archive contains research and eval expectations; the installable plugin
omits those directories. Sealed model-evaluation bundles use the existing narrower
capture allowlist so the model cannot see grading expectations. Illustrative
fixtures are never sufficient evidence for a completed real operation.

Build inputs are allowlisted; symlinks are rejected. An ownership/hash manifest
prevents overwriting modified generated files. This is local accidental-change
protection, **not a signature or an authenticity trust root**. Review and pin the
Git revision when distributing through a marketplace.

Installation, execution, verification, and publication are distinct operations.
Offline gates do not install a plugin, and successful installation does not prove
activation, authorization, security, or workflow quality in a host.
