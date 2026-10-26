//! Lint check crate: one deliberate violation per lint in `templates/rust/lints.toml`.
//!
//! Every violation line carries a `LINT:` tag naming the lint that must fire. The test
//! asserts that exactly the tagged set fires and nothing else, so an `allow` that stops
//! working or a lint that stops firing both fail the suite.

use std::collections::*; // LINT: clippy::wildcard_imports
use std::fmt;
use std::rc::Rc;

/// Error type for the fixture.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error {
    /// The input was zero.
    Zero,
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("input was zero")
    }
}

impl std::error::Error for Error {}

/// A public type without a `Debug` implementation.
pub struct NoDebug(pub u8); // LINT: missing_debug_implementations

pub fn undocumented() {} // LINT: missing_docs

mod private {
    pub fn not_reexported() -> u8 { 1 } // LINT: unreachable_pub
}

/// Calls into the private module so nothing is dead.
pub fn call_private() -> u8 {
    private::not_reexported()
}

/// Writes a marker through a formatter whose lifetime is elided.
///
/// # Errors
///
/// Returns the formatter's error when the write fails.
pub fn elided(f: &mut fmt::Formatter) -> fmt::Result { // LINT: elided_lifetimes_in_paths
    f.write_str("x")
}

/// Dereferences a raw pointer inside an unsafe function without an unsafe block.
///
/// # Safety
///
/// `p` must point to a readable `u8`.
pub unsafe fn deref_in_unsafe_fn(p: *const u8) -> u8 {
    *p // LINT: unsafe_op_in_unsafe_fn
}

/// Unwraps an option.
///
/// # Panics
///
/// Panics when `o` is `None`.
pub fn unwrap_it(o: Option<u8>) -> u8 {
    o.unwrap() // LINT: clippy::unwrap_used
}

/// Expects with a reason, which the policy permits (nothing may fire here).
///
/// # Panics
///
/// Panics when `o` is `None`.
pub fn expect_it(o: Option<u8>) -> u8 {
    o.expect("fixture value is always present")
}

/// Asserts inside a function that returns `Result`.
///
/// # Errors
///
/// Returns [`Error::Zero`] when `x` is zero.
///
/// # Panics
///
/// Panics when `x` is greater than ten.
pub fn result_panics(x: u8) -> Result<u8, Error> {
    assert!(x <= 10, "x out of range: {x}"); // LINT: clippy::panic_in_result_fn
    if x == 0 { Err(Error::Zero) } else { Ok(x) }
}

/// Returns an error for zero but does not document it.
pub fn no_errors_doc(x: u8) -> Result<u8, Error> { // LINT: clippy::missing_errors_doc
    if x == 0 { Err(Error::Zero) } else { Ok(x) }
}

/// Panics for zero but does not document it.
pub fn no_panics_doc(x: u8) -> u8 { // LINT: clippy::missing_panics_doc
    assert!(x != 0, "x must be non-zero");
    x
}

#[allow(dead_code, reason = "fixture: allow instead of expect")] // LINT: clippy::allow_attributes
fn allowed_with_reason() {}

#[allow(dead_code)] // LINT: clippy::allow_attributes_without_reason
fn allowed_without_reason() {}

/// Builds a string through an unsafe block that has no safety comment.
pub fn no_safety_comment() -> String {
    unsafe { String::from_utf8_unchecked(vec![104]) } // LINT: clippy::undocumented_unsafe_blocks
}

/// Performs two unsafe operations in one block.
pub fn two_unsafe_ops() -> (String, String) {
    // SAFETY: both byte vectors hold one lowercase letter, which is valid UTF-8.
    unsafe { (String::from_utf8_unchecked(vec![104]), String::from_utf8_unchecked(vec![105])) } // LINT: clippy::multiple_unsafe_ops_per_block
}

/// Takes a boolean parameter.
pub fn report(verbose: bool) -> u8 { // LINT: clippy::fn_params_excessive_bools
    u8::from(verbose)
}

/// Carries too many boolean fields.
#[derive(Debug, Default, Clone, Copy)]
pub struct Flags { // LINT: clippy::struct_excessive_bools
    /// First flag.
    pub alpha: bool,
    /// Second flag.
    pub beta: bool,
    /// Third flag.
    pub gamma: bool,
    /// Fourth flag.
    pub delta: bool,
}

/// Clones a reference-counted pointer through method syntax.
pub fn clone_rc(r: &Rc<u8>) -> Rc<u8> {
    r.clone() // LINT: clippy::clone_on_ref_ptr
}

/// Clones a value that is never used again.
pub fn redundant() -> String {
    let s = String::from("a");
    s.clone() // LINT: clippy::redundant_clone
}

/// Concatenates with the plus operator.
pub fn concat(a: String, b: &str) -> String {
    a + b // LINT: clippy::string_add
}

/// Returns an ordered map built through the glob import.
pub fn map() -> BTreeMap<u8, u8> {
    BTreeMap::new()
}

/// Leaves a debug macro behind.
pub fn debug(x: u8) -> u8 {
    dbg!(x) // LINT: clippy::dbg_macro
}

/// Leaves a todo behind.
///
/// # Panics
///
/// Always panics.
pub fn later() {
    todo!() // LINT: clippy::todo
}

/// Leaves an unimplemented behind.
///
/// # Panics
///
/// Always panics.
pub fn not_yet() {
    unimplemented!() // LINT: clippy::unimplemented
}

/// Prints to stdout from library code.
pub fn shout() {
    println!("hi"); // LINT: clippy::print_stdout
}

/// Prints to stderr from library code.
pub fn complain() {
    eprintln!("hi"); // LINT: clippy::print_stderr
}

/// Exits the process from library code.
pub fn bail() -> ! {
    std::process::exit(1) // LINT: clippy::exit
}

/// Leaks a value on purpose.
pub fn leak() {
    std::mem::forget(String::from("x")); // LINT: clippy::mem_forget
}

/// Truncates with a cast.
pub fn truncate(x: u32) -> u8 {
    x as u8 // LINT: clippy::as_conversions
            // LINT: clippy::cast_possible_truncation
}

/// Drops a sign with a cast.
pub fn unsign(x: i32) -> u32 {
    x as u32 // LINT: clippy::cast_sign_loss
}

#[cfg(test)]
mod tests {
    #[test]
    fn unwrap_and_print_are_allowed_in_tests() {
        let v: Option<u8> = "1".parse().ok();
        println!("{v:?}");
        assert_eq!(v.unwrap(), 1, "value {v:?}");
    }
}
