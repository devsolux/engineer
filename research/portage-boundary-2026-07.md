# Portage integration boundary — 2026-07

Portage is a private Rust CLI for portable, git-grounded job packets between Claude, Codex, Gemini,
Cursor, and OpenCode. Its canonical ownership is snapshot/pack/delta/doctor/provider launch hints.

engineer should compose with it, not absorb it:

| Portage owns | engineer owns |
|---|---|
| provider discovery and path hints | effective host capability and authority negotiation |
| HANDOFF.md / pack.json job packet | requirements, architecture, implementation and acceptance |
| git snapshot and delta | artifact validation and completion evidence |
| launch hints | permission, sandbox, browser and orchestration policy |

Required hardening at the boundary: packet text is untrusted; allowlist schema fields; confine paths;
never dereference session hints; scan for secrets before sharing; verify git and hashes after receipt;
refresh delta after tree changes; and re-detect the target host. Future Portage-native signed/hash-bound
artifacts could strengthen transport integrity, but engineer must not claim they exist in schema v1.
