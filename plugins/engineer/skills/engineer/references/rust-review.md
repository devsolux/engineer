# Rust review: priorities, rule citations, report

**Last verified**: 2026-10-26 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `rust-idioms.md` / `rust-systems.md` | The rules this review applies; load the section a finding needs |
| `rust.md` | Axum service review: handler path, timeouts, shutdown, error leakage |
| `code-quality.md` | Cross-language pre-ship review checklist |
| `refactoring.md` | Turning accepted findings into behavior-preserving change |
| `security-audit.md` | "Find vulnerabilities" is a different pipeline with its own verdicts |
| `epistemic-honesty.md` | Observed vs inferred labels on every finding |

Use when the user asks to review, audit, critique, grade, or "check" Rust code, a crate, a
module, a `.rs` file, a diff, or a pull request, or asks how to make Rust more idiomatic. The
output is a review, not a rewrite: the reader decides what to fix. Rewrite only on request, and
then through `engineer refactor` with `refactoring.md`.

## Contents
- [Scope first](#scope-first)
- [Tools first](#tools-first)
- [Priority order](#priority-order)
- [Report](#report)
- [Finding rules](#finding-rules)
- [Offer enforcement](#offer-enforcement)

## Scope first

- **Read exactly what was pointed at**: a file, a module, a crate, or a diff. For a diff,
  review the changed lines and whatever they break, not the whole file.
- **Library or application**: a `lib.rs`, `pub` items used by other crates, or a publishable
  `Cargo.toml` means the library rules apply strictly; otherwise the simplicity rules apply
  (concrete types, one app error, no speculative generality). State the assumption at the top.
- **Edition, `rust-version`, `[lints]`** from `Cargo.toml`, so no finding recommends a feature
  the project cannot use (`#[expect]` needs Rust 1.81; `[lints]` needs Cargo 1.74).
- **Deliberate quirks**: a documented workaround, or a `// SAFETY:` / `// NOTE:` explaining an
  oddity, is intent. It lands under Consider with the trade-off, never under Must fix.

## Tools first

When a toolchain is available, run from the crate root and fold the results in; they take the
mechanical issues so attention goes to design:

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -W clippy::pedantic
cargo test
bash scripts/engineer-scan.sh --rust        # RS-* grep tier (rust-systems.md → Enforcement)
```

Do not paste raw clippy output: group repeats into one finding and skip pedantic lints that do
not matter for this code. No toolchain → say so in the report header and review by reading;
findings are then `inferred`, not `observed`.

## Priority order

Work top to bottom. The first two tiers are where real bugs live.

| Tier | Look for | Rule source |
|---|---|---|
| 1 Correctness, soundness | `unsafe` without `// SAFETY:`; `transmute` to cast enums or extend lifetimes; `unsafe impl Send` / `Sync` to silence the compiler; a safe fn that reaches UB through safe calls | M-UNSOUND, M-UNSAFE, clippy `undocumented_unsafe_blocks` |
| | Reachable panics: `unwrap`, `expect`, indexing, wrapping `as` casts, overflow on paths outside input can reach | M-PANIC-IS-STOP, clippy `unwrap_used`, `cast_*` |
| | Trait contracts: hand-written `Ord` with derived `PartialEq`; `Hash` disagreeing with `Eq` (corrupts `BTreeMap`, `HashMap`, `sort`, `dedup`) | C-COMMON-TRAITS, std contract |
| | Lock hazards: guard across `.await` or returned to callers; user closures under a lock; poison recovered with `into_inner` | clippy `await_holding_lock`, Google |
| | Destructors that fail, panic, or block | C-DTOR-FAIL, C-DTOR-BLOCK |
| 2 Error handling | `()`, `String`, `Box<dyn Error>`, or `anyhow::Error` as a library's public error; an error enum without `Display` + `std::error::Error` | C-GOOD-ERR, M-ERRORS-CANONICAL-STRUCTS |
| | Lost information: `map_err(\|_\| …)`, no `source()`, messages without the path, line, or value | EfR 4, M-FROM-ERROR |
| | Panics for expected failures; `catch_unwind` as control flow | M-PANIC-ON-BUG, M-PANIC-CONTINUATION |
| 3 API design (strict for libraries) | `&String` / `&Vec<T>` / `&Box<T>` params; `bool` params; take-then-clone; public fields; `Rc` / `RefCell` / `Arc` in signatures; leaked third-party types | C-CUSTOM-TYPE, M-AVOID-WRAPPERS, M-DONT-LEAK-TYPES, clippy `ptr_arg` |
| | Missing `Debug`, `Display` on errors, `Default` beside `new()`, `FromStr` instead of `from_str` | C-DEBUG, M-PUBLIC-DISPLAY, clippy `new_without_default`, `should_implement_trait` |
| | `get_` getters; `as_` / `to_` / `into_` mismatching cost; `Manager` / `Service` / `Util` names; missing `#[non_exhaustive]` or sealing | C-GETTER, C-CONV, M-WEASEL-WORDS, C-SEALED |
| 4 Idiom, clarity | Borrow-checker clones; check-then-unwrap; `+` strings; loops that should be iterators or the reverse; `HashMap` order leaking into output or tests; `#![deny(warnings)]`; `#[allow]` without reason; glob imports | anti-patterns, EfR 3 / 9 / 23, M-LINT-OVERRIDE-EXPECT |
| 5 Docs, tests | Undocumented `pub` items; docs restating the name; missing `# Errors` / `# Panics` / `# Safety`; examples with `unwrap()`; untested logic or tautological tests | C-FAILURE, C-QUESTION-MARK, M-TAUTOLOGICAL-TESTS |

For a service crate add the `rust.md` ship gate: no `unwrap` in the handler path, timeouts on
every I/O, graceful shutdown, errors that do not leak internals.

## Report

The `engineer audit` shape, specialized:

~~~markdown
## engineer audit: <what was reviewed> (Rust review)
**Modules**: rust-review, rust-idioms[, rust-systems, rust]
**Scope**: <library | application> · edition <2021|2024> · rust-version <x.y> · lints table <yes|no>
**Tools**: <fmt, clippy, test, scan run> | <not available: reviewed by reading>
**Score**: <pass | fail> - <one paragraph: what the code does, overall verdict, the single most
important fix>

### Must fix
1. <Short title> (`src/file.rs:42`) (observed)
   **Rule**: <rule and source, e.g. "error types implement std::error::Error (C-GOOD-ERR)">
   **Problem**: <what is wrong and the concrete consequence>
   **Fix**:
   ```rust
   <the smallest change, only the lines that change>
   ```

### Should fix
2. …

### Consider
3. …

### Enforcement gaps
- <rule>: `templates/rust/lints.toml` lint `<name>` / `engineer-scan --rust` `RS-*` would catch it

### Passed
- <two to four specific things the code already does well>
~~~

- **Must fix**: a bug, a soundness hole, a reachable panic, or an API mistake that becomes a
  breaking change once published.
- **Should fix**: works, but violates a rule with a real cost (worse errors, harder testing,
  a confusing API).
- **Consider**: style, naming, polish, and respected quirks.

## Finding rules

- **Location** as `file:line` for every finding (`whole file` only for something without a
  single location, such as missing tests).
- **Rule with source** a reader can look up: a `C-*` code, an Effective Rust item number, an
  `M-*` code, a clippy lint name, or "Google Rust Style Guide" (`rust-idioms.md` → Sources).
- **Fix as code**, kept to the lines that change. Never rewrite whole functions in a review.
- **Group repeats**: one finding for "eight `unwrap()` calls on parse results" with the lines.
- **Confidence label** on each finding: `observed` (tool output or read code) or `inferred`
  (a consequence reasoned from it). Never state an inference as observed.
- **Proportionate**: five to ten findings is plenty for a short file; never pad, never hide a
  real bug among style nits.
- **Passed is required**: it tells the author what to keep and makes the rest credible.

## Offer enforcement

A project without a `[lints]` table ends the report with the enforcement step: paste
`templates/rust/lints.toml` into `Cargo.toml` and copy `templates/rust/clippy.toml` beside it,
run `cargo clippy --all-targets --all-features -- -D warnings` in CI (`enforcement-rules.md`),
and name two or three findings from this review that the table would have caught. For the full
CI and pre-commit setup route to `engineer enforce`.

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
