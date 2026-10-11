# Skill-evaluation batch publication research - 2026-07

**Scope**: safe local publication of paired explicit and implicit evaluation jobs.

## Observed failure

Engineer previously wrote and validated one job at a time. When a later implicit arm failed canonical
compilation, earlier files remained in the output directory. Those files were valid individually but
did not prove that the requested comparison batch was complete.

## Primary-source findings

- Python's `tempfile` module creates unpredictable temporary names securely and supports choosing the
  destination directory. This avoids the race in deprecated predictable-name construction.
- Python documents successful `os.replace` on the same filesystem as atomic. The guarantee covers one
  rename, not a set of files.
- A multi-file batch therefore needs an application-level commit marker. Publish validated jobs first,
  then atomically publish a manifest that binds their hashes and exact requested coverage.

Sources:

- [Python tempfile documentation](https://docs.python.org/3/library/tempfile.html)
- [Python os.replace documentation](https://docs.python.org/3/library/os.html#os.replace)

## Engineer decision

Preparation takes an exclusive lock per output directory. Every job is written to a secure temporary
file and canonically compiled before publication. Existing identical jobs support safe replay;
non-identical collisions stop the batch. The manifest is validated and replaced last.

The validator treats host, scenario, and activation mode as a Cartesian product. It rejects missing,
duplicate, extra, drifted, or path-escaping jobs and replays the canonical compiler. A directory without
a valid `manifest.json` is incomplete, even if some jobs are valid on their own.

This design does not claim a filesystem-wide transaction. A crash can leave loose files, but it cannot
leave a new valid commit marker for a partial batch. Provider execution, authorization, activation
quality, and task behavior remain separate evidence.
