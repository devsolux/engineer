# Rust port: same behavior, Rust-shaped code

**Last verified**: 2026-10-26 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `rust-idioms.md` | Style and API rules for the Rust you produce |
| `rust.md` | When Rust is the right target at all; service layout |
| `decision-engineering.md` | Whether to port: measured need, not preference |
| `refactoring.md` | Behavior-preservation discipline and atomic steps |
| `system-assurance.md` | Characterization tests when the original has none |
| `api-data-flows.md` | Contracts when the port sits behind another service |

Use when the user asks to port, translate, convert, migrate, or rewrite C, C++, Python, Go,
JavaScript, or TypeScript in Rust ("rewrite this in Rust", "what would this look like in Rust",
"move this module to Rust"). The goal is the Rust a Rust developer would write to solve the same
problem, with the same observable behavior. A line-by-line transliteration compiles, keeps every
problem the original had, and adds the borrow checker on top. **Port the behavior, not the structure.**

Before porting, confirm the premise (`rust.md` → When to use Rust): a working module is
rewritten only for a measured latency, cost, correctness, or safety need, or because the user
has decided. Say which applies.

## Contents
- [1 Understand the original](#1-understand-the-original)
- [2 Port the tests first](#2-port-the-tests-first)
- [3 Design the API, then implement](#3-design-the-api-then-implement)
- [4 Keep the port proportionate](#4-keep-the-port-proportionate)
- [5 Verify](#5-verify)
- [6 Porting notes](#6-porting-notes)
- [Anti-patterns](#anti-patterns)

## 1 Understand the original

1. **Read the code, its tests, and its callers** when available.
2. **List the observable behavior**: every public function, its inputs, outputs, and every way
   it fails. Include the quiet parts, which is where ports go wrong: result ordering, tie
   breaking, empty input, whitespace and case handling, integer limits, what is an error versus
   a valid edge case.
3. **Mark what is incidental** to the source language and does not carry over: manual memory
   management, out-parameters, `NULL` returns, global state, fixed-size buffers, a class that
   only groups functions, `isinstance` checks.
4. **Bugs and ambiguities stay**: keep the behavior, flag it in the notes, let the user decide.
   A port is not the place to fix things silently.

## 2 Port the tests first

Translate the original tests into Rust before the implementation, one Rust test per original
test with a name that maps back, so coverage is checkable. The tests define "same behavior". If
the original has none, write characterization tests from the behavior list in step 1
(`system-assurance.md`), run them against the original where possible, and keep them.

## 3 Design the API, then implement

Decide public types and signatures from the behavior list, not from the original's shape, then
implement against the ported tests following `rust-idioms.md`.

### From C and C++

| Original | Rust |
|---|---|
| `malloc` / `free`, `new` / `delete`, `create` / `destroy` pairs | Owned types (`String`, `Vec`, `Box`) dropped automatically; `Drop` for anything else |
| `NULL` meaning absent | `Option<T>` |
| Error codes, `ERR_*` defines, `errno` | `Result<T, E>` with an error enum, one variant per code, implementing `Display` and `std::error::Error` |
| Out-parameters (`int *err_line`, `long *out`) | Return values: data in the `Ok` value or the error variant |
| Flag bitmasks (`FLAG_A \| FLAG_B`) | An options struct with named fields and `Default`, or `bitflags`; never a raw `u32` |
| `char *` plus length, `strcmp`, `strcasecmp` | `&str` / `String`, `==`, `eq_ignore_ascii_case` |
| Pointer plus count, index loops | Slices and iterators |
| Fixed-size buffers and truncation | Growable types; drop the limit unless the limit is behavior |
| `#define` constants and macros | `const`, enums, functions |
| Global or static mutable state | A struct the caller owns |
| `strtol` and friends | `str::parse` with the matching integer type; parse failures map to the error enum |

No `unsafe` or raw pointers unless the port must talk to C through FFI, and then confined as
`rust-systems.md` → Unsafe and FFI describes.

### From Python

| Original | Rust |
|---|---|
| Exception hierarchy | One error enum (or one per area), a variant per exception class, data attributes as variant fields |
| `None` as a value | `Option<T>` |
| Strings used as a closed set (`kind in ("build", "test")`) | An enum with `FromStr` and `Display` for the text form |
| Dicts or classes used as records | Structs with named fields |
| `dict` iteration (insertion order is guaranteed) | `Vec` or an ordered map when order is observable; a plain `HashMap` silently reorders output |
| Duck typing, `isinstance` | Traits or enums |
| Unbounded `int` | A sized integer chosen on purpose; `checked_*` where input can be large |
| `sorted(..., key=...)` | `sort_by_key` / `sort_by` (both stable, like Python's) |
| `splitlines()`, `strip()`, `isalnum()` | `lines()`, `trim()`, `char::is_alphanumeric`; check `\r\n`, Unicode, and empty strings against the original |
| `try` / `except` around a parse | `?` with a mapped error, or `match` on the `Result` |

### From Go, JavaScript, TypeScript

- Go `(value, error)` → `Result`; `nil` → `Option`; interfaces → traits; goroutines and channels
  → threads with `std::sync::mpsc` or async tasks, whichever the original needs.
- JavaScript / TypeScript `null` and `undefined` → `Option`; thrown errors → `Result`; plain
  objects → structs; numbers → a sized integer or `f64` chosen on purpose; union types → enums;
  `Map` order → `Vec` or an ordered map when observable.

## 4 Keep the port proportionate

Matching the original on every possible input is usually the wrong goal; match it on the inputs
it actually receives and use the standard library for the rest.

- **Do not reimplement the source runtime**: `str::lines`, `str::trim`, `str::parse`, `char`
  methods, not hand-written copies of Python's `splitlines`, `strip`, `int()`, `repr()` or C's
  locale-dependent `isspace`, `strtol`. Where Rust differs only on exotic input (Unicode digits,
  non-ASCII whitespace, unbounded integers), list the difference in the notes; write a shim
  only when the user says those inputs occur.
- **Do not grow the API**: port the public surface plus the standard trait impls Rust callers
  expect (`Debug`, `Clone`, `Display`, `Error`, `FromStr`, `Default`, `IntoIterator` for
  collections). No builders, `Index`, `FromIterator`, `Extend`, or custom iterator types unless
  the original's callers need them.
- **Keep the algorithm unless it is wrong**: swap one only for a real problem (quadratic on
  realistic input) and say so in the notes.
- **Check the size**: code lines excluding tests, comments, docs. A C / C++ port lands near the
  original; a Python / JavaScript port lands at two to three times, because types, error enums,
  and trait impls are explicit. Much more means one of the three habits above.
- **Differential testing**: a few dozen realistic and edge-case inputs through both
  implementations answer the question; a fuzzing harness over millions mostly finds exotic
  divergences that belong in the notes.

## 5 Verify

```bash
cargo build
cargo test
cargo clippy --all-targets --all-features -- -D warnings
bash scripts/engineer-scan.sh --rust
```

Every ported test passes. When the original's tests can run too, run both on the same inputs
and compare. A port whose verification was not run is reported as unverified, never as done
(`implementation-completeness.md`).

## 6 Porting notes

Beside the code, a short `PORTING.md` a reviewer can check in minutes:

| Section | Content |
|---|---|
| API mapping | Each original function or type → its Rust equivalent |
| Test mapping | Each original test → the Rust test that covers it |
| Deliberate differences | Anything that now behaves differently and why: a vanished out-of-memory error, a dropped buffer limit, exotic-input differences in the standard library |
| Preserved quirks | Odd behavior kept on purpose, so nobody "fixes" it by accident |
| Verification | Commands run and their result, or a plain statement that they were not run |

## Anti-patterns

| ID | Pattern | Remediation |
|---|---|---|
| AP-PORT-TRANSLITERATE | C in Rust syntax: raw pointers, out-parameters, error codes | Behavior list → Rust-shaped API (step 3 tables) |
| AP-PORT-DYNAMIC | `Box<dyn Any>`, stringly-typed records, `HashMap<String, Value>` to mimic dynamic typing | Structs and enums from the behavior list |
| AP-PORT-HASHMAP-ORDER | `HashMap` where insertion order was observable | `Vec` or an ordered map; test the order |
| AP-PORT-SILENT-FIX | Fixing the original's bug without a note | Keep the behavior, flag it, let the user decide |
| AP-PORT-RUNTIME-CLONE | Hand-written copies of Python / C runtime functions | Standard library plus a notes entry for exotic input |
| AP-PORT-UNSAFE | `unsafe` to mirror pointer code with no FFI | Owned types, slices, `Option` |
| AP-PORT-UNVERIFIED | "Ported" without running the ported tests | Step 5 commands, or an explicit unverified label |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
