# Architecture brief: fixture-notes-service (run-001)

Illustrative fixture for the Engineer security-audit verb. Every name, path,
principal, and host below is synthetic; the service does not exist.

## Principals

- anonymous: an unauthenticated HTTP caller.
- member: an authenticated user holding a session cookie issued by `src/api/auth.py`.
- owner: the member who created a note; ownership is a column on the note row.
- operator: a human running `src/cli/admin.py` from a shell on the host.

## Authority

Members may create, read, update, and delete their own notes and attachments.
Operators may export any note and rotate the session signing key. Nothing grants
one member access to another owner's notes.

## Protected resources

- Note bodies and attachments (per-owner confidentiality).
- The session signing key loaded from the environment at start-up.
- The attachment worker's outbound network position.

## Stack

A Python 3 HTTP service under `src/api/` over a single SQLite file accessed through
`src/notes/repository.py`, a background attachment worker in
`src/notes/attachments.py`, and an operator CLI under `src/cli/`. Tests live under
`tests/`. The only middleware is the project's own `src/api/middleware.py`.

## Entry surfaces

- `http-api`: JSON routes in `src/api/routes.py` (note CRUD, attachment creation,
  search, export).
- `admin-cli`: `src/cli/admin.py` subcommands `export` and `rotate-key`.

## Trust boundaries

- anonymous-to-member: the session cookie check in `src/api/middleware.py`.
- member-to-owner: the ownership check expected in `src/notes/repository.py`.

## Starting paths

1. `src/api/routes.py`: `get_note_handler`, `create_attachment_handler`,
   `export_note_handler`.
2. `src/notes/repository.py`: `get_note`.
3. `src/notes/attachments.py`: `fetch_remote_attachment`.
4. `src/notes/export.py`: `export_path`.

## Prior-run gaps

No prior run exists. Every cell of the coverage ledger starts planned.
