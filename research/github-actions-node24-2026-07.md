# GitHub Actions Node 24 migration — July 2026

## Decision

Engineer's executable workflows and consumer templates use current Node 24-based
first-party actions pinned to immutable, GitHub-verified commit SHAs:

| Action | Release | Immutable commit |
|---|---:|---|
| `actions/checkout` | `v7.0.0` | `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0` |
| `actions/setup-python` | `v6.3.0` | `ece7cb06caefa5fff74198d8649806c4678c61a1` |
| `actions/setup-node` | `v7.0.0` | `820762786026740c76f36085b0efc47a31fe5020` |

The release tags, exact commits, commit verification, and each commit's
`action.yml` (`runs.using: node24`) were checked through GitHub's API on
2026-07-15. A signed tag alone is not the executable identity: the workflow
still pins the resolved commit.

## Runtime policy

- GitHub deprecated the Node 20 action runtime and scheduled Node 24 as the
  default beginning 2026-06-16. Node 20 itself reached end of life on
  2026-03-24.
- Consumer JavaScript templates target Node 24 LTS. Action runtime and the
  application's selected Node version are separate decisions; both are explicit.
- Node 24 setup actions document runner 2.327.1 or newer; self-hosted fleets
  must be upgraded before rollout and follow newer action-specific requirements.
- `setup-node` can infer npm caching. Elevated or dependency-sensitive jobs
  disable it with `package-manager-cache: false` unless explicitly reviewed.
  Consumer CI opts into `cache: npm` only for unprivileged install/test jobs.
- Automated pin tests reject stale or mutable first-party action references.
  Future updates require release, exact-commit, runtime, runner, and CI evidence.

## Sources

- [GitHub: deprecation of Node 20 on Actions runners](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)
- [actions/checkout](https://github.com/actions/checkout)
- [actions/setup-python](https://github.com/actions/setup-python)
- [actions/setup-node](https://github.com/actions/setup-node)
- [Node.js release schedule](https://nodejs.org/en/about/previous-releases)
