#![deny(warnings)]
//! Fixture: denies warnings in source, so a new toolchain breaks the build; no lints table.

/// Adds two numbers.
pub fn add(a: u8, b: u8) -> u8 {
    a.wrapping_add(b)
}
