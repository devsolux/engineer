# Evidence publication safety research

**As of**: 2026-07-16

## Decision

Engineer distinguishes immutable evidence creation, validated append, and replaceable human reports.
They are different state transitions and must not share a write helper merely because each ends in a
file.

Immutable receipts use exclusive creation. Python documents `tempfile.mkstemp()` as race-free when
the platform correctly implements `O_EXCL`, and warns that checking a generated name before opening
it creates a security window. MITRE classifies link following and time-of-check/time-of-use races as
composable weaknesses that can redirect writes. Engineer therefore creates a final receipt once with
`O_CREAT | O_EXCL` and `O_NOFOLLOW` when available. Existing files and final symlinks fail.

An MCP transcript package is published only into a newly created directory. Each member is created
exclusively, and the manifest remains the deterministic package receipt. This is not a filesystem
transaction across the directory; an interrupted compiler can leave an incomplete directory, which
must never be treated as a valid package without its replayed manifest.

Telemetry is intentionally append-only and uses a separate contract. A sibling lock file is opened
without following its final name, then `flock(LOCK_EX)` is held across validation, duplicate
detection, append, `fsync`, and post-validation. The recorder compares the opened ledger's device and
inode with the named file before writing. A failed post-validation truncates only the bytes from that
locked append. This is cooperative Unix advisory locking, not protection from a writer that ignores
the lock or from a hostile parent directory outside the declared trust root.

A human research report is regenerable output and may use deliberate replacement after its own
confinement checks. It is not silently converted into immutable evidence behavior.

## Primary sources

- Python 3.14 `tempfile`: secure temporary creation, `mkstemp()`, and the deprecated name-check pattern: https://docs.python.org/3/library/tempfile.html
- Python 3.14 `os`: `os.open`, `O_EXCL`, and platform-dependent no-follow flags: https://docs.python.org/3/library/os.html
- Python 3.14 `fcntl`: advisory `flock`, `LOCK_EX`, and `LOCK_UN`: https://docs.python.org/3/library/fcntl.html
- MITRE CWE-61, UNIX symlink following: https://cwe.mitre.org/data/definitions/61.html
- MITRE CWE-367, TOCTOU race conditions: https://cwe.mitre.org/data/definitions/367.html
