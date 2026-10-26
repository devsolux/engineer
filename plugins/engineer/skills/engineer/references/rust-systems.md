# Rust: concurrency, unsafe, crates, docs, tests, performance, enforcement

**Last verified**: 2026-10-26 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `rust-idioms.md` | Ownership, naming, types, traits, errors, everyday idioms |
| `rust.md` | Axum / Tokio / SQLx services: handlers, timeouts, shutdown |
| `rust-review.md` | Tier-1 soundness and lock findings cite these sections |
| `enforcement-rules.md` | CI rules; `templates/rust/` drop-in lint config |
| `oss-maintainer.md` / `skill-supply-chain.md` | Dependency and supply-chain policy |
| `observability.md` | Tracing, health checks, structured logs |

Second half of the Rust language rules: load with `rust-idioms.md` when the work touches async,
`unsafe`, FFI, workspace layout, dependencies, features, semver, rustdoc, tests, performance,
or lint enforcement. Rule codes as in `rust-idioms.md` (`C-*`, `M-*`, "EfR n").

## Contents
- [Concurrency and async](#concurrency-and-async)
- [Unsafe and FFI](#unsafe-and-ffi)
- [Crates, modules, dependencies](#crates-modules-dependencies)
- [Documentation](#documentation)
- [Tests](#tests)
- [Performance](#performance)
- [Enforcement](#enforcement)
- [Checklist](#checklist)
- [Sources](#sources)

## Concurrency and async

- Public types and the futures they return are `Send` (M-TYPES-SEND), pinned at compile time
  so a refactor cannot regress it:

  ```rust
  const _: () = { const fn assert_send<T: Send>() {} assert_send::<Client>(); };
  ```
  An `Rc` or a `RefCell` borrow held across `.await` makes the future `!Send`.
- Message passing over shared state (EfR 17). When sharing: data with linked invariants under
  one lock, lock scopes a few lines long, no user closures under a lock, never a `MutexGuard`
  returned from a public method or held across `.await` (clippy `await_holding_lock`).
- `async fn` over `fn -> impl Future` (M-ASYNC-FN), except in traits or when setup must run
  outside the async block on a hot path.
- Long CPU-bound work inside async yields (`tokio::task::yield_now().await` every tens of
  microseconds) or moves to `spawn_blocking` (M-YIELD-POINTS).
- Libraries spawn no raw threads and assume no runtime: take an executor, a spawn function, or
  `impl AsyncRead` / `impl Read` from the caller (M-IMPL-IO, M-MOCKABLE-SYSCALLS).

## Unsafe and FFI

- `unsafe` for one of three reasons (M-UNSAFE, EfR 16): a novel abstraction safe code cannot
  express, a measured performance need, or FFI and platform calls. std and well-reviewed
  crates already contain the audited `unsafe`; reach for them first.
- Every `unsafe` block or impl has a `// SAFETY:` comment stating why the invariants hold, one
  operation per block (clippy `undocumented_unsafe_blocks`, `multiple_unsafe_ops_per_block`);
  every `unsafe fn` has `# Safety` docs listing what the caller upholds (clippy
  `missing_safety_doc`); `unsafe_op_in_unsafe_fn` is on.
- Keep `unsafe` in the smallest module that can uphold its invariant and wrap it in a safe API
  (contain-unsafety pattern): the module boundary is the soundness boundary. A safe function
  that can cause undefined behavior through safe calls is unsound, and unsound code never ships
  (M-UNSOUND). `unsafe` marks UB risk, not danger: `delete_database()` is a safe function
  (M-UNSAFE-IMPLIES-UB).
- No `transmute` to cast enums or extend lifetimes; no `unsafe impl Send` to silence the compiler.
- Test `unsafe` under Miri and with adversarial inputs (EfR 30).
- FFI (EfR 34-35, M-FFI-TRANSLATES, M-SYS-CRATES; object-based-API and type-consolidation
  patterns): `#[repr(C)]` on shared structs, sized integers, `CString` / `CStr`, allocate and
  free on the same side, RAII wrappers whose `Drop` frees C-owned pointers, null → `Result`,
  panics stopped at the boundary with `catch_unwind`; `bindgen` in a `foo-sys` crate, business
  logic in a safe core crate.

## Crates, modules, dependencies

- Small single-purpose crates in a flat `crates/` workspace (M-SMALLER-CRATES,
  M-CRATES-FLAT-FOLDER; prefer-small-crates pattern); never a crate inside another's `src/`.
  Share versions and lints through `[workspace.dependencies]` and `[workspace.lints]` (M-CARGO-WORKSPACE).
- Modules: a leaf is named after its primary item (`Foo` in `foo.rs`); non-leaf modules hold
  only `mod` declarations and re-exports (Google); essential items at the crate root, the rest
  grouped by use case (`account`, `network`), not by kind (`traits`, `errors`); sizes balanced (M-BALANCED-MODULES).
- Every dependency costs compile time, binary size, and supply-chain exposure, `build.rs` and
  proc macros included (EfR 25). Ranges (`"1"`, `"1.4"`), never `"*"` or a needless `"="`;
  commit `Cargo.lock` for binaries; audit with `cargo tree --duplicates`, `cargo deny`,
  `cargo audit`, `cargo udeps`.
- Features are additive and bare-named (M-FEATURES-ADDITIVE, C-FEATURE); none removes or
  changes a public item; no feature-gated fields or trait methods; mocks behind `test-util` (M-TEST-UTIL).
- Semver (EfR 21): breaking = removing or renaming public items, adding a variant to an enum
  that is not `#[non_exhaustive]`, adding a field to a publicly constructible struct, adding a
  trait bound, making a trait non-object-safe. Deprecate in a minor before removing in a major.
  Latest stable edition for new crates (M-LATEST-EDITION); MSRV set deliberately (M-MSRV).
- No code before `main()`, no mutable statics (M-AVOID-STATICS), no unstable features on stable.

## Documentation

- `///` on every public item, `//!` at every public module and the crate root (C-CRATE-DOC,
  EfR 27, M-MODULE-DOCS). The first sentence is one line of about fifteen words; it becomes
  the listing summary (M-FIRST-DOC-SENTENCE).
- Sections in order, as applicable: `# Examples`, `# Errors`, `# Panics`, `# Safety`
  (M-CANONICAL-DOCS, C-FAILURE). Examples use `?` with `fn main` hidden behind `# ` lines,
  never `unwrap()`, because users copy them verbatim (C-EXAMPLE, C-QUESTION-MARK).
- Document what the signature cannot say: preconditions, side effects, ownership transfer,
  complexity, why. Never restate the name (`/// Removes an element.` on `remove_element`).
  Link items with `` [`Type`] `` (C-LINK); hide impls users never trigger with `#[doc(hidden)]`
  (C-HIDDEN); `#[doc(inline)]` on `pub use` (M-DOC-INLINE).
- `//` comments explain why, not what: `// SAFETY:`, `// TODO(issue-123):`, a non-obvious
  value, a workaround with a link. No design journals or rule-compliance tables in code
  (M-NO-META-DESIGN-DOCUMENTATION); document the end state.

## Tests

- Unit tests in `#[cfg(test)] mod tests { use super::*; … }` for private internals;
  integration tests in `tests/` for anything reachable through the public API, preferred when
  either would do (M-INTEGRATION-TESTS); doc examples are tests too.
- Test observable behavior and properties (round-trips, monotonicity, idempotence), not
  restated constants or mirrored branches (M-TAUTOLOGICAL-TESTS). A failing test precedes a bug fix.
- I/O, time, randomness, and network are mockable: `new_mocked() -> (Self, MockCtrl)` behind
  `test-util`, never a `Default` that performs I/O (M-MOCKABLE-SYSCALLS).
- Parsers of untrusted input get `cargo fuzz`; benchmarks use `criterion` or `divan` with
  `std::hint::black_box`; `unsafe` runs under Miri (EfR 30).
- Assertions carry context: `assert_eq!(got, want, "input {input:?}")`.

## Performance

Design for usability first; optimize after measuring (EfR 20, M-HOTPATH). Then, in order:
`Vec::with_capacity` or `collect()` over push loops (M-INITIAL-CAPACITY); caller-owned buffers
in hot APIs (`fn read_into(&mut self, buf: &mut Vec<u8>)`, M-MEM-REUSE); `Box<[T]>`,
`Box<str>`, `Arc<str>` for long-lived immutable sequences (M-BOX-DST); `shrink_to_fit` on
long-lived collections built without a reservation (M-SHRINK-TO-FIT); a faster hasher only for
trusted keys (M-FAST-HASHER); batch work over per-item locking; applications may set a
`#[global_allocator]` such as `mimalloc` (M-MIMALLOC-APPS). `Copy` for small plain types, never large ones.

## Enforcement

**Lint table once, in `Cargo.toml`**: `[lints.rust]` / `[lints.clippy]`, or `[workspace.lints]`
in the root with `[lints] workspace = true` in every member (Cargo 1.74+). Groups carry
`priority = -1` so individual entries win; every level is `warn` and CI makes it binding with
`cargo clippy --all-targets --all-features -- -D warnings`. Drop-in: `templates/rust/lints.toml`
and `templates/rust/clippy.toml` (clippy reads `clippy.toml` from `CLIPPY_CONF_DIR`, else the
manifest directory, else the working directory, walking up). The suppression lints
`allow_attributes` and `allow_attributes_without_reason` need `rust-version = "1.81"` or later.
`scripts/test-rust-lints.sh` proves every lint in the table fires on a check crate.

**Grep tier** - `bash scripts/engineer-scan.sh --rust` (auto-enabled when a `Cargo.toml` is found):

| ID | Signal | Default → `--strict` |
|---|---|---|
| RS-LINTS | no `[lints]` / `[workspace.lints]` table in any `Cargo.toml` | warn |
| RS-DENY-WARNINGS | `#![deny(warnings)]` in source | fail |
| RS-UNWRAP | `.unwrap()` outside a `#[cfg(test)] mod`, `tests/`, `benches/`, `examples/` | warn → fail |
| RS-UNSAFE-SAFETY | `unsafe {` or `unsafe impl` without `// SAFETY:` within three lines above | warn → fail |
| RS-DEBUG-LEFTOVER | `dbg!`, `todo!`, `unimplemented!` outside tests | warn → fail |

The scan is heuristic; clippy with the lint table is the enforcement (`enforcement-rules.md`).

## Checklist

- Every `unsafe` block has `// SAFETY:`; every `unsafe fn` has `# Safety`; no `transmute`
  tricks, no `unsafe impl Send` to silence the compiler.
- Public types and futures are `Send`; no guard across `.await`; CPU work yields or blocks off-runtime.
- Public items documented: one-line summary plus `# Errors` / `# Panics` where relevant;
  examples use `?`.
- Features additive and bare; dependencies ranged, locked for binaries, audited.
- Tests cover behavior, mock I/O behind `test-util`, fuzz parsers, run Miri over `unsafe`.
- The `[lints]` table exists and clippy is clean under `-D warnings`.

## Sources

Checked 2026-10-26 (ledger: `docs/verification-2026-10-26-rust.md`): the primary sources listed
in `rust-idioms.md`; Cargo reference, `[lints]` section and workspace `lints` table
(https://doc.rust-lang.org/cargo/reference/manifest.html,
https://doc.rust-lang.org/cargo/reference/workspaces.html); Clippy configuration and lint
configuration (https://doc.rust-lang.org/clippy/configuration.html,
https://doc.rust-lang.org/clippy/lint_configuration.html); lint behaviour executed locally with
clippy 0.1.99 through `scripts/test-rust-lints.sh`.

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
