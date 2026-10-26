# Rust: idiomatic code, API design, and errors

**Last verified**: 2026-10-26 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `rust-systems.md` | Concurrency, unsafe and FFI, crates, docs, tests, performance, enforcement |
| `rust.md` | Axum / Tokio / SQLx service layout, handlers, ship gate |
| `rust-review.md` | Reviewing existing Rust: priority order, report format |
| `rust-port.md` | Porting C / C++ / Python / Go / JS / TS to Rust |
| `coding-principles.md` / `refactoring.md` | Craft, SOLID, behavior-preserving change |
| `enforcement-rules.md` | clippy and CI rules; `templates/rust/` drop-in lint config |

Scope: any `.rs` file, `Cargo.toml`, crate API, error type, or clippy question, whether or not
the user asks for "idiomatic" code. **Library code** (anything with external users) follows the
API rules strictly. **Application code** prefers concrete types, one app-level error, and `Vec`
returns over speculative generality. Rule codes: `C-*` Rust API Guidelines, `M-*` Pragmatic
Rust Guidelines, "EfR n" Effective Rust item n ([Sources](#sources)).

## Contents
- [Mindset](#mindset)
- [Before handing back code](#before-handing-back-code)
- [Ownership and borrowing](#ownership-and-borrowing)
- [Naming](#naming)
- [Types that carry the domain](#types-that-carry-the-domain)
- [Standard traits and conversions](#standard-traits-and-conversions)
- [Constructors, builders, visibility](#constructors-builders-visibility)
- [Traits, generics, macros](#traits-generics-macros)
- [Errors and panics](#errors-and-panics)
- [Everyday idioms](#everyday-idioms)
- [Checklist](#checklist)
- [Sources](#sources)

## Mindset

- **Rust-shaped code** (M-RUST-SHAPED): errors are `Result`, resources are ownership plus
  `Drop`, polymorphism is traits and enums, absence is `Option`. Inheritance imitations
  (`Deref` to a "base" struct, the Deref-polymorphism anti-pattern), `Manager` / `Factory` /
  `Helper` types (M-WEASEL-WORDS), and `throw_if_null` helpers are ports, not Rust.
- **Invalid states unrepresentable**: enums instead of `bool` flags and "must be X if Y"
  comments, newtypes for units and IDs (C-NEWTYPE, EfR 6), fallible constructors that validate
  once (C-VALIDATE, M-STRONG-TYPES-GUARD). The compiler enforces what a comment only requests.
- **Library ≠ application** (Google style guide; M-APP-ERROR): API-design rules bind libraries;
  applications take simplicity and directness.
- **Tools own the mechanical**: rustfmt owns layout, clippy owns idiom (EfR 29), the compiler
  owns memory safety. Spend review attention on design.

## Before handing back code

```bash
cargo fmt
cargo clippy --all-targets --all-features -- -D warnings
cargo test
cargo doc --no-deps        # libraries: broken links, missing docs
```

- Fix the lint. When it is genuinely wrong for one item, `#[expect(clippy::name, reason = "…")]`
  on the narrowest item (M-LINT-OVERRIDE-EXPECT; `expect` and `reason` are stable since Rust
  1.81): it warns again once the lint stops firing, so suppressions expire. `#[allow]` only in
  generated code or macro output.
- Never `#![deny(warnings)]` in source (Rust Design Patterns anti-pattern): a new toolchain adds
  a warning and the build breaks. CI passes `-D warnings` instead.
- Lints live once in `Cargo.toml`, not in scattered crate attributes; a project without a
  `[lints]` table gets `templates/rust/` (`rust-systems.md` → Enforcement).

## Ownership and borrowing

- **Prefer unique ownership** (Google; EfR 8). `Rc` / `Arc` only when shared ownership is the
  design, `RefCell` / `Mutex` only when interior mutability is. They move checks from compile
  time to run time, so use them on purpose.
- **Never clone to end a borrow** (the clone-to-satisfy-the-borrow-checker anti-pattern): the
  copy silently diverges. Try, in order:
  1. a named `let` to extend a temporary, or a block to shorten a borrow;
  2. typed intermediates so the failing step is visible;
  3. `mem::take` (needs `Default`), `mem::replace`, or `Option::take` to move out of `&mut self`;
  4. split the struct so disjoint fields borrow separately (the compiler tracks disjoint
     borrows inside one function, not across method calls, EfR 15);
  5. a deliberate clone of small immutable data, with a comment when it is not obvious;
  6. indices into an owning `Vec`, or `Rc<RefCell<_>>` with `Weak` back-pointers, last. No
     self-referential structs.
- **Accept the most general borrowed type**: `&str` not `&String`, `&[T]` not `&Vec<T>`, `&T`
  not `&Box<T>`, `Option<&T>` not `&Option<T>` (borrowed-types idiom; clippy `ptr_arg`,
  `borrowed_box`). `impl AsRef<Path>` / `AsRef<str>` / `AsRef<[u8]>` on parameters that only
  read (M-IMPL-ASREF), never on fields: store `PathBuf` and `String`. Library code that only
  iterates takes `impl IntoIterator<Item = T>`; application code may take `&[T]`.
- **Take ownership only to store or consume, and then by value**: no `&T` plus an internal
  `.clone()`. Read → `&T`; mutate in place → `&mut T`. Return tuples or structs, never `&mut`
  out-parameters (C-NO-OUT); reusing a caller buffer as `Read::read` does is the exception.
- **Own data in structs.** A `&'a T` field forces a lifetime onto every container; `String` /
  `Vec<u8>` is rarely the bottleneck. A type that carries a lifetime names it (`'src`, `'conn`).
- **Freeze after setup** (temporary-mutability idiom): build with `let mut`, rebind `let data = data;`.
- **No `Rc`, `Arc`, `Box`, `RefCell` in public signatures** (M-AVOID-WRAPPERS): take `&T`,
  `&mut T`, or `T`. A shared service is `Clone` over an internal `Arc<Inner>` (M-SERVICES-CLONE).

## Naming

| Item | Convention | Source |
|---|---|---|
| Types, traits, variants | `UpperCamelCase`; acronyms as one word (`Uuid`, `HttpClient`) | C-CASE |
| Functions, modules, locals | `snake_case`; constants `SCREAMING_SNAKE_CASE` | C-CASE |
| Getters | `len()`, `name()`, `name_mut()`; bare `get` only for one obvious value (`Cell::get`); `_unchecked` siblings for unsafe variants | C-GETTER |
| Setters, access | `set_foo(T)`, `take_foo()`, `replace_foo(T)`, `with_foo(\|f\| …)` | Google |
| Conversions | `as_` free borrow→borrow, `to_` costly, `into_` consumes; `as_mut_slice`, not `as_slice_mut` | C-CONV, C-WORD-ORDER |
| Constructors | `new`, `with_capacity` / `new_with_foo`, `try_new` (fallible), `from_foo` (pair with `From`); I/O uses domain verbs `open`, `connect` | C-CTOR, Google |
| Iterators | `iter` / `iter_mut` / `into_iter` return `Iter` / `IterMut` / `IntoIter`; `keys()` returns `Keys` | C-ITER, C-ITER-TY |
| Errors | verb-object-error: `ParseBoolError`, not `BoolParseError` | C-WORD-ORDER |
| Type params, lifetimes | short, from the bound (`R: Read`, `W: Write`); descriptive lifetimes on types | Google |
| Features | bare: `std`, `serde`, `alloc`; never `use-std`, `no-std` | C-FEATURE |

No `Service` / `Manager` / `Factory` / `Helper` / `Util` suffixes (M-WEASEL-WORDS); do not
repeat the module name in the type (`foo::Id`, not `foo::FooId`); avoid abbreviations an
outsider would not know (M-SHORT-NAMES). `len()` implies `is_empty()` (clippy `len_without_is_empty`).

## Types that carry the domain

- **Newtypes** for semantic distinctions (C-NEWTYPE, EfR 6): `Miles(f64)` and `Kilometers(f64)`
  cannot be mixed, aliases can. `#[repr(transparent)]` when layout matters; derive or forward
  the traits you need. An invariant newtype (`Month`) validates in `TryFrom` / `FromStr` /
  `try_new` and never offers an infallible `From` from the raw type (M-STRONG-TYPES-GUARD).
- **No `bool` parameters in public or shared signatures** (C-CUSTOM-TYPE; clippy
  `fn_params_excessive_bools` with `max-fn-params-bools = 0`): `report(true)` is unreadable and
  cannot grow a third mode. A two-variant enum (`Verbosity::Summary | Full`) or two methods.
  Only a private helper with its call sites a few lines away is exempt; when refactoring, an
  existing `bool` parameter is a smell to remove, not a detail to preserve.
- **Named fields over tuples** except single-field newtypes and very local code (Google).
- **`Option` for absence, never sentinels** (`-1`, `""`); data-carrying enums instead of
  "field X is only meaningful when Y is set" (EfR 1).
- **Strongest std type** (M-STRONG-TYPES): `PathBuf` / `&Path`, `Duration`, `NonZeroU32`
  internally (plain integers at API boundaries). **Independent flags** use `bitflags`
  (C-BITFLAG); an enum models exactly one choice.

## Standard traits and conversions

Downstream crates cannot add std traits to your types (orphan rule), so implement them eagerly
(C-COMMON-TRAITS, EfR 10): `Debug` on every public type (C-DEBUG, M-PUBLIC-DEBUG; hand-write it
to redact secrets), `Clone` (not for unique resources or key material), `Copy` only for small
bitwise-copyable types, `PartialEq` / `Eq`, `PartialOrd` / `Ord` (ship `Ord` whenever a total
order exists; Google prefers `PartialOrd` only while the order is unclear), `Hash` consistent
with `Eq`, `Default`. `Display` for anything humans read (M-PUBLIC-DISPLAY). `#[must_use]` on
pure functions and on error and lazy types.

- Implement `From` / `TryFrom`, never `Into` / `TryInto` directly (C-CONV-TRAITS); `from` /
  `into` over `as`, which allows lossy casts silently (clippy `as_conversions`, `cast_*`).
- `FromStr` instead of an ad-hoc `from_str` (clippy `should_implement_trait`); `FromIterator`
  and `Extend` on collections (C-COLLECT); `IntoIterator` for owned and borrowed forms
  (M-COLLECTION-TRAITS); `Deref` only on smart pointers and owning collections (C-DEREF);
  operators only for their mathematical meaning (C-OVERLOAD); `Send` + `Sync` where possible
  (C-SEND-SYNC, M-TYPES-SEND); `serde` impls behind a feature named `serde` (C-SERDE).
- No derivable bounds on struct definitions (C-STRUCT-BOUNDS): `#[derive(Clone)] struct
  Good<T>`, not `struct Bad<T: Clone + Debug>`. Bounds belong on the `impl` blocks that need them.
- A hand-written `Ord` comes with hand-written `PartialEq`, `PartialOrd`, and `Hash` that compare
  the same fields; a derived `PartialEq` beside a custom `Ord` breaks the std contract, and
  since Rust 1.81 the sorts panic on a detected violation. Document which fields equality ignores.

## Constructors, builders, visibility

- Provide `new()` even when `Default` exists and make them agree (clippy `new_without_default`);
  options structs with public fields implement `Default` so callers write `..Default::default()`.
- Up to two optional parameters: inherent constructors (`new`, `with_a`). Beyond that, or when
  construction validates or has side effects: `Foo::builder()` → `FooBuilder`, setters named after
  fields (`timeout(d)`, not `set_timeout`) and infallible, `build() -> Result<Foo, Error>` does
  all validation including cross-field checks (C-BUILDER, EfR 7, M-INIT-BUILDER, M-BUILD-RESULT).
  Non-consuming setters (`&mut self -> &mut Self`) unless `build` must move a value out.
- Four or more loose arguments group into semantic types: `Deposit::new(account, amount)`.
- **Private by default** (C-STRUCT-PRIVATE, EfR 22). Widen `pub(crate)` → `pub(super)` → `pub`;
  widening later is non-breaking, narrowing is. Every `pub` item is a semver promise.
- `#[non_exhaustive]` on public enums and public-field structs that cross crate boundaries unless
  the set is a stable ontology (Google); match the handled variants plus a wildcard arm.
- Seal traits you do not want implemented downstream, and say so in the docs (C-SEALED):

  ```rust
  pub trait Codec: private::Sealed { /* … */ }
  mod private { pub trait Sealed {} impl Sealed for super::Json {} }
  ```
- Implementation iterator types hide behind `impl Iterator<Item = T>` (internal) or a newtype
  (stable public API) (C-ITER-TY, C-NEWTYPE-HIDE).
- One path per public item (M-SINGLE-ITEM-PATH); re-export individually, never `pub use foo::*`
  (M-NO-GLOB-REEXPORTS); no preludes (M-NO-PRELUDE). Do not leak third-party types into the
  public API (M-DONT-LEAK-TYPES); when one must appear, re-export it so callers can name the
  matching version (EfR 24, M-FOREIGN-REEXPORTS). `const fn` only if it will stay `const`.

## Traits, generics, macros

- Define a trait only for generic programming (`T: Trait`, `impl Trait`, `dyn Trait`) or as an
  extension trait (`FooExt`), never to organize code (Google). Essential functionality is
  inherent; trait impls forward to it so callers need no import (M-ESSENTIAL-FN-INHERENT).
- Prefer, in order: concrete types; generics; `dyn Trait` wrapped in your own struct
  (`struct DynStore(Arc<dyn Store>)`) (M-DI-HIERARCHY, EfR 12). Generics give static dispatch
  and inlining; trait objects give heterogeneous collections and smaller binaries. Service-level
  types do not visibly nest generics (`Service<Backend>` yes, `Service<Backend<Store>>` no)
  (M-SIMPLE-ABSTRACTIONS).
- Decide object safety early (C-OBJECT); exclude generic or `Self`-returning methods with
  `where Self: Sized`. Keep required methods minimal and default the rest, as `Iterator` does
  from `next` (EfR 13).
- A clear receiver makes a method; a computation without one is a free function, not
  `Database::check(params)` (C-METHOD, M-REGULAR-FN). Associated functions construct.
- Closures: the most general bound that works (`FnOnce` → `FnMut` → `Fn`), `Fn*` bounds over
  `fn` pointers, closure parameter last, at most one. Parameter order consistent across the
  crate: call-specific first, ubiquitous context last (M-PARAMETER-CONSISTENCY).
- Macros are a last resort (M-MACRO-LAST-RESORT, EfR 28): `macro_rules!` before proc macros
  (M-EXAMPLE-OVER-PROC), input resembles output (C-EVOCATIVE), and a macro never changes an
  item's kind or a function's signature (M-MACROS-DONT-LIE).

## Errors and panics

| Situation | Mechanism | Source |
|---|---|---|
| Absence is normal (`first()`, `checked_add`) | `Option<T>` | Google |
| Caller may need to know what went wrong | `Result<T, E>` | Google, EfR 4 |
| Bug or violated invariant inside your code | `panic!` / `assert!` / `expect("why")` | M-PANIC-ON-BUG |

- **Panic means stop** (M-PANIC-IS-STOP, EfR 18): never for bad input; `catch_unwind` is not
  control flow (M-PANIC-CONTINUATION: it does nothing under `panic = "abort"` and can leave
  state inconsistent); a library never catches a panic and continues. A panicking convenience
  pairs with a fallible sibling (`get` / `get_unchecked`, `new` / `try_new`) documented under `# Panics`.
- **Every intentional panic carries the relevant values** (M-PANIC-MESSAGE):
  `assert!(buf.len() >= HEADER, "buffer too small: {} bytes", buf.len())`;
  `expect("config is loaded before workers start")` over `unwrap()` (clippy `unwrap_used`
  warns, `expect_used` is allowed). Do not restate the condition as the message.
- **Pattern-match, never check-then-unwrap**: `let Some(v) = opt else { return … };`, not
  `if opt.is_some() { opt.unwrap() }` (Google).
- **Lock poisoning is fatal**: `.lock().expect("lock poisoned")`; never recover with `into_inner` (Google).
- **Library error types** (C-GOOD-ERR, EfR 4, M-ERRORS-CANONICAL-STRUCTS): implement
  `std::error::Error` (so `Debug` + `Display`), are `Send + Sync + 'static`, implement `source()`
  for wrapped causes. Never `()`, `String`, `Box<dyn Error>`, or `anyhow::Error` in a public
  `Result`. `Display` is lowercase, concise, no trailing punctuation: `"invalid header length"`.
  `From<Upstream>` so `?` converts; `map_err` only for foreign errors or added context
  (M-FROM-ERROR). Two sound shapes: an enum with one variant per cause (`thiserror` derives it)
  or a struct per situation with a private `kind` plus `is_xxx()` accessors; never one
  crate-wide enum of every failure, never details callers cannot act on. A fallible function
  that consumes its argument returns it inside the error so the caller can retry without
  cloning (`FromUtf8Error::into_bytes`; return-consumed-argument idiom).
- **Application errors**: `anyhow` or `eyre` with `.context("opening config")`, one app-level
  type, `main` may return `Result<(), anyhow::Error>` (M-APP-ERROR). Service edges map to HTTP
  through `AppError: IntoResponse` (`rust.md`).
- **Destructors never fail, panic, or block** (C-DTOR-FAIL, C-DTOR-BLOCK): `close(self) ->
  Result<()>` for fallible teardown; `Drop` is best-effort.
- **Document failure modes** (C-FAILURE): `# Errors` for any `Result`, `# Panics` for any
  reachable panic, `# Safety` for every `unsafe fn` (clippy `missing_errors_doc`,
  `missing_panics_doc`, `missing_safety_doc`).

## Everyday idioms

- **Iterators over hand loops** when the pipeline is short and reads top-down (EfR 9):
  `.filter().map().collect()`, `.any()`, `.sum()`, `.fold()`; fallible steps collect into
  `Result<Vec<_>, E>` then `?`. Keep a `for` loop when the body is large, does several jobs, or
  needs awkward early returns. No long chains in a `for` header; prefer `for` to `.for_each()` (Google).
- **`Option` / `Result` combinators** (`map`, `and_then`, `ok_or_else`, `as_deref`) when they
  are clearer than `match`, and `match` when they are not (EfR 3).
- **`format!` / `write!`** with inline args (`format!("{name}: {count}")`) for concatenation,
  never `+` or `str::replace` (format idiom; clippy `string_add`); `write!` into an existing
  buffer on hot paths.
- **Explicit types where inference obscures intent**: `.into()`, `.parse()`, `.collect()`,
  complex chains; `let x: Vec<u32> = …` over a turbofish (Google).
- **Drop guards** for cleanup that must run on early return or unwind (RAII-guard pattern,
  EfR 11), bound to a name: `let _guard = …`; `let _ = …` drops immediately.
- **Closures that capture mixed ownership** rebind in a block, then `move`:
  `let job = { let cfg = cfg.clone(); move || run(cfg, data) };` (pass-variables-to-closure idiom).
- **Imports** (Google): one `use` per module path with `{Bar, Baz}`; types and traits imported
  and used unqualified; free functions qualified by module (`mem::take`, `fs::read`); a trait
  imported inside the function that needs it. No glob imports (EfR 23; clippy
  `wildcard_imports`) except `use super::*` in test modules and `use Enum::*` inside a function
  that matches on it.
- **Magic numbers** become named `const`s whose doc says where the value comes from and what
  changing it affects (M-DOCUMENTED-MAGIC).
- **Logging** through `tracing` or `log`, structured, never `println!` / `dbg!` in library or
  service code (M-LOG-NOT-PRINT, M-LOG-STRUCTURED; clippy `print_stdout`, `dbg_macro`); a CLI's
  own stdout output is the exception.

## Checklist

Before returning Rust code (systems items: `rust-systems.md` → Checklist):

- `cargo fmt`, `cargo clippy --all-targets --all-features -- -D warnings`, `cargo test` clean.
- No `unwrap()` outside tests and `main`; every `expect`, `assert`, `panic` has a message with values.
- Public functions take `&str`, `&[T]`, `impl AsRef<_>`, or `impl IntoIterator`, not `&String` / `&Vec<T>`.
- Every public type derives `Debug` and the applicable common traits; error types implement
  `Error + Display + Send + Sync + 'static`.
- No `bool` parameters in public signatures; no hand-written `Ord` without matching `PartialEq` and `Hash`.
- No `.clone()` whose only job is to satisfy the borrow checker.
- No glob imports, preludes, glob re-exports, or leaked third-party types.
- Application code stayed simple; library code followed the API rules.

## Sources

Primary sources checked 2026-10-26 (ledger: `docs/verification-2026-10-26-rust.md`): Rust API
Guidelines checklist (`C-*`, https://rust-lang.github.io/api-guidelines/checklist.html);
Effective Rust, items 1-35 (https://www.lurklurk.org/effective-rust/); Rust Design Patterns
idioms, patterns, and anti-patterns (https://rust-unofficial.github.io/patterns/); Pragmatic
Rust Guidelines 2026.6 (`M-*`, https://microsoft.github.io/rust-guidelines/); Google Rust Style
Guide (https://google.github.io/styleguide/rustguide.html); Rust 1.81 release notes
(`#[expect]`, `reason`). Clippy and Cargo references: `rust-systems.md` → Sources.

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
