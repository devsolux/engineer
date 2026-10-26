# Verification ledger — 2026-10-26 Rust modules

Verification of the Rust language modules added after 1.2.0 (`rust-idioms.md`,
`rust-systems.md`, `rust-review.md`, `rust-port.md`), the drop-in lint configuration
(`templates/rust/lints.toml`, `templates/rust/clippy.toml`) and the Rust signals in
`engineer-scan.sh`, on the committed 1.2.0 tree (4e7ed57) on macOS 27.0.0 (arm64) with
Python 3.11.17, rustc/cargo 1.99.1 and clippy 0.1.99 (Homebrew). Research notes keep their
own dates and are not re-verified here. The previous ledgers are
[verification-2026-10-22.md](verification-2026-10-22.md) and
[verification-2026-10-22-modules.md](verification-2026-10-22-modules.md).

Method: every externally checkable claim in the four modules (rule identifiers, item numbers,
pattern and anti-pattern names, lint names, configuration keys, version thresholds) was checked
against the primary source named below on 2026-10-26, and each rule cites the source it
condenses. The module text is an original synthesis written for this package; no source text
is reproduced. Lint behaviour was verified by execution, not by documentation.

## Sources checked

| Area | Finding | Primary source |
|---|---|---|
| Rust API Guidelines | The checklist lists 54 items in eleven sections; every `C-*` code cited in the modules (C-CASE, C-CONV, C-GETTER, C-ITER, C-ITER-TY, C-FEATURE, C-WORD-ORDER, C-COMMON-TRAITS, C-CONV-TRAITS, C-COLLECT, C-SERDE, C-SEND-SYNC, C-GOOD-ERR, C-EVOCATIVE, C-CRATE-DOC, C-EXAMPLE, C-QUESTION-MARK, C-FAILURE, C-LINK, C-HIDDEN, C-METHOD, C-NO-OUT, C-OVERLOAD, C-DEREF, C-CTOR, C-OBJECT, C-NEWTYPE, C-CUSTOM-TYPE, C-BITFLAG, C-BUILDER, C-VALIDATE, C-DTOR-FAIL, C-DTOR-BLOCK, C-DEBUG, C-SEALED, C-STRUCT-PRIVATE, C-NEWTYPE-HIDE, C-STRUCT-BOUNDS) exists with the meaning the modules give it | https://rust-lang.github.io/api-guidelines/checklist.html |
| Effective Rust | Items 1-35 and their titles match the citations (items 1, 3, 4, 6-13, 15-18, 20-25, 27-30, 34, 35 are cited); online edition by David Drysdale, O'Reilly 2024, CC BY-NC-ND 4.0, which is why the modules cite item numbers and paraphrase instead of quoting | https://www.lurklurk.org/effective-rust/ |
| Rust Design Patterns | Cited idioms (borrowed types for arguments, `format!` concatenation, `mem::take` / `mem::replace`, temporary mutability, pass variables to closure, return consumed argument on error), patterns (RAII guards, builder, prefer small crates, contain unsafety in small modules, FFI object-based APIs and type consolidation into wrappers) and anti-patterns (clone to satisfy the borrow checker, `#[deny(warnings)]`, Deref polymorphism) are all present in the book's table of contents | https://github.com/rust-unofficial/patterns (`src/SUMMARY.md`, `main`); https://rust-unofficial.github.io/patterns/ |
| Pragmatic Rust Guidelines | Version 2026.6 (generated 2026-09-25). Every `M-*` identifier cited in the modules was read in the single-page view: Universal (M-UPSTREAM-GUIDELINES, M-STATIC-VERIFICATION, M-LINT-OVERRIDE-EXPECT, M-PUBLIC-DEBUG, M-PUBLIC-DISPLAY, M-SMALLER-CRATES, M-WEASEL-WORDS, M-SHORT-NAMES, M-REGULAR-FN, M-DOCUMENTED-MAGIC, M-LOG-STRUCTURED), Libraries (M-TYPES-SEND, M-DONT-LEAK-TYPES, M-FOREIGN-REEXPORTS, M-IMPL-ASREF, M-IMPL-IO, M-SIMPLE-ABSTRACTIONS, M-AVOID-WRAPPERS, M-DI-HIERARCHY, M-ERRORS-CANONICAL-STRUCTS, M-FROM-ERROR, M-INIT-BUILDER, M-SERVICES-CLONE, M-ESSENTIAL-FN-INHERENT, M-BALANCED-MODULES, M-NO-PRELUDE, M-PARAMETER-CONSISTENCY, M-COLLECTION-TRAITS, M-ASYNC-FN, M-MOCKABLE-SYSCALLS, M-TEST-UTIL, M-INTEGRATION-TESTS, M-STRONG-TYPES, M-STRONG-TYPES-GUARD, M-BUILD-RESULT, M-NO-GLOB-REEXPORTS, M-AVOID-STATICS, M-LOG-NOT-PRINT, M-SYS-CRATES, M-FEATURES-ADDITIVE), Macros (M-MACRO-LAST-RESORT, M-EXAMPLE-OVER-PROC, M-MACROS-DONT-LIE), Applications (M-MIMALLOC-APPS, M-APP-ERROR), FFI (M-FFI-TRANSLATES), Correctness (M-UNSAFE, M-UNSAFE-IMPLIES-UB, M-UNSOUND, M-PANIC-IS-STOP, M-PANIC-ON-BUG, M-PANIC-CONTINUATION, M-PANIC-MESSAGE), Performance (M-HOTPATH, M-YIELD-POINTS, M-MEM-REUSE, M-BOX-DST, M-SHRINK-TO-FIT, M-FAST-HASHER, M-INITIAL-CAPACITY), Project (M-CARGO-WORKSPACE, M-CRATES-FLAT-FOLDER, M-LATEST-EDITION, M-MSRV), Documentation (M-FIRST-DOC-SENTENCE, M-MODULE-DOCS, M-CANONICAL-DOCS, M-DOC-INLINE), AI (M-SINGLE-ITEM-PATH, M-NO-META-DESIGN-DOCUMENTATION, M-TAUTOLOGICAL-TESTS, M-RUST-SHAPED) | https://microsoft.github.io/rust-guidelines/ (`print.html`, first 100,000 characters; the Macros chapter text after M-MACRO-VERSION-PIN was not read) |
| Google Rust Style Guide | Rules cited: library versus application binding, prefer unique ownership over `Rc` / `Arc`, no clone as a substitute for borrowing, `&[T]` / `&str` / `&T` parameters, `impl IntoIterator` for iterating library code, enum over `bool`, `Option` / `Result` / `panic!` split, newtypes and named fields, traits only for generic programming or `Ext` extension, `PartialOrd` preferred until a total order is clear, the getter and setter naming table, `is_empty()` with `len()`, never reaching into a poisoned mutex, `SAFETY:` comments, `#[non_exhaustive]`, `#[must_use]`, no code before `main()`, `const` only when it stays `const`, operator overloading only for mathematical meaning, explicit types on `.into()` / `.parse()` / chains, `if let` over check-then-unwrap, `expect` over `unwrap`, assertion context, no `catch_unwind` in first-party code, `format!` over `+`, import granularity, trait imports inside functions, module-qualified free functions, leaf and non-leaf module layout | https://google.github.io/styleguide/rustguide.html |
| Cargo `[lints]` | Levels `forbid` / `deny` / `warn` / `allow`; `priority` is a signed integer, lower values are applied first and overridden by higher ones, the shorthand form is priority 0; `[lints.rust]` and `[lints.clippy]` are selected by the `tool::` prefix; lints apply to the current package only; "Respected as of 1.74"; `[workspace.lints]` in the root with `[lints] workspace = true` in each member | https://doc.rust-lang.org/cargo/reference/manifest.html#the-lints-section; https://doc.rust-lang.org/cargo/reference/workspaces.html#the-lints-table |
| Clippy configuration | `max-fn-params-bools` (default 3; `0` lints any function with a `bool` parameter via `fn_params_excessive_bools`), `max-struct-bools` (3), `allow-unwrap-in-tests`, `allow-expect-in-tests`, `allow-print-in-tests`, `allow-dbg-in-tests` (all default `false`), `msrv` defaults to `rust-version`; `clippy.toml` / `.clippy.toml` is searched from `CLIPPY_CONF_DIR`, else `CARGO_MANIFEST_DIR`, else the current directory, walking up parent directories; the configuration file is documented as unstable | https://doc.rust-lang.org/clippy/lint_configuration.html; https://doc.rust-lang.org/clippy/configuration.html |
| Rust 1.81.0 | `#[expect(lint)]` stabilized as a lint level that warns when the lint does not fire; `reason = "…"` on lint attributes is shown in compiler output; the new sort implementations panic on a detected `Ord` violation; `core::error::Error` | https://blog.rust-lang.org/2024/09/05/Rust-1.81.0/ |

## Executed locally

| Check | Result |
|---|---|
| `bash scripts/test-rust-lints.sh` (clippy 0.1.99, `cargo clippy --offline --all-targets` on the assembled check crate) | All 28 `warn`-level lints in `templates/rust/lints.toml` are covered by a tagged violation; exactly the 29 tagged diagnostics fired (`elided_lifetimes_in_paths` fires for the `rust_2018_idioms` group, and the truncating cast fires both `as_conversions` and `cast_possible_truncation`); no untagged diagnostic fired, so the `expect_used`, `must_use_candidate`, `module_name_repetitions`, `module_inception` and `enum_glob_use` allowances and the `allow-*-in-tests` keys hold |
| Observed while building the fixture | rustc reports the `unsafe_op_in_unsafe_fn` lint at warning level under diagnostic code `E0133` with no `#[warn(...)]` note; the test maps that code explicitly. `clippy::rc_buffer` did not fire on an `Rc<String>` field, an `Arc<String>` field, or an `Rc<Vec<u8>>` return with clippy 0.1.99, so it is not in the template; the `Box<str>` / `Arc<str>` advice stays a review rule (M-BOX-DST) |
| `bash scripts/test-scan.sh` | 21 checks passed, including the 13 Rust checks: pass / warn / fail fixtures, `--strict` escalation of RS-UNWRAP, RS-UNSAFE-SAFETY and RS-DEBUG-LEFTOVER, RS-DENY-WARNINGS and RS-LINTS on the fail fixture, auto-enable from `Cargo.toml` without `--rust`, and no report for the `unwrap()` inside a `#[cfg(test)] mod tests` |

## Gates

On the final tree, in this order: `make fixtures` (skill-eval chain rebound to the edited
`SKILL.md` and eval bank), `make build`, `make lint` (282 files), `make check` (validate-repo
and the 220-scenario eval bank), `make test JOBS=4` (56 of 56 offline suites passed in
1 min 32 s, including `test-rust-lints.sh` and `test-scan.sh`), `make verify-build` (generated
`plugins/engineer` matches the canonical source). Per-verb load budgets stay within their
ceilings with `SKILL.md` at 356 lines; the `visual` verb sits exactly at its 800-line ceiling.

## Not executed

- `cargo fmt` and `cargo doc` were not run on the check crate (the lint test runs clippy only).
- The four new evals (217-220) are static routing scenarios; no live model run.
- No host install or `make host-validate`; the plugin manifests did not change.
- The Pragmatic Rust Guidelines single-file agent text (`agents/all.txt`) was not fetched; the
  print view was used, and no module cites an identifier beyond the part that was read.

## Release gates for 1.3.0

1.3.0 packages the Rust modules, lint template, scanner tier and evals recorded above (4163a0f),
which is everything merged on `main` after the `v1.2.0` tag. Same machine; Claude Code 2.1.282 and
Codex CLI 0.163.0-alpha.11.

| Check | Result |
|---|---|
| `python3 scripts/report-module-currency.py` | 120 of 120 modules current as of 2026-10-26; nothing redated |
| `make fixtures` | Rebound the skill-eval chain from version 1.2.0 to 1.3.0 with the new bundle and `SKILL.md` digests; grader-verified |
| `make build` → `make lint` | Plugin manifests and the bundled skill at 1.3.0; lint passed (282 files) |
| `make host-validate` | `claude plugin validate --strict` passed for the marketplace and the plugin on Claude Code 2.1.282 |
| `python3 scripts/scan-doc-supply-chain.py` | Passed |
| `bash scripts/check-oss-leaks.sh` on the staged changeset | Clean (24 files; the private-marker layer was off, so only the generic layer ran) |
| `make release-check JOBS=4` | Static gates passed (220 static eval scenarios); 56/56 isolated offline suites passed; no bundle drift |

Not executed before the release commit: publishing (push, `v1.3.0` tag, GitHub release),
`make package` (it runs inside `make github-release`), the install-from-GitHub check, and any live
model run. CI results for the Rust commit and the release commit are recorded under Publication.

## Publication of 1.3.0

| Check | Result |
|---|---|
| `git push origin main` | `main` pushed to `origin` as a fast-forward, 4163a0f..c45425d |
| GitHub Actions | Run 40382698617 on 4163a0f (the Rust commit) and run 40383502978 on c45425d (the release commit) each passed all four lanes before the tag was created |
| `make github-release` | Release "Engineer 1.3.0" published 2026-10-26T19:09:43Z, marked Latest, not a draft or prerelease, with `engineer-1.3.0-plugin.zip` and its SHA-256 sidecar |
| `git ls-remote --tags origin` | `v1.3.0` → c45425d; `v1.2.0` → 157992b; `v1.1.0` → 2713d00; `v1.0.0` → 5ac51a3 |
| Release assets | The uploaded ZIP (1,194,262 bytes, digest `ebbad38f655c87e85a26504afcc61bf31aa2642216f78d2744daeeb2a3863806`) and the sidecar (92 bytes) equal the locally packaged files; the digests were read from the release API asset records rather than by downloading the assets again |

Not executed: installing 1.3.0 from GitHub into throwaway Claude Code and Codex profiles to
confirm both hosts resolve `engineer@devsolux-engineer` at the new version (release procedure
step 6), and any live model run. Existing host installs stay at their earlier version until updated.
