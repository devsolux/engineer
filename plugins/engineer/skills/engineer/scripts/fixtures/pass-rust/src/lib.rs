//! Fixture: an idiomatic crate that passes the Rust scan.

/// Parses a port number.
///
/// # Errors
///
/// Returns the parse error when `text` is not a number.
pub fn parse_port(text: &str) -> Result<u16, std::num::ParseIntError> {
    let port: u16 = text.trim().parse()?;
    Ok(port)
}

/// Returns the first byte as a character when it is ASCII.
pub fn first_ascii(bytes: &[u8]) -> Option<char> {
    let first = *bytes.first()?;
    if !first.is_ascii() {
        return None;
    }
    // SAFETY: a single byte below 128 is ASCII, and ASCII is always valid UTF-8.
    let text = unsafe { std::str::from_utf8_unchecked(std::slice::from_ref(&first)) };
    text.chars().next()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_port() {
        assert_eq!(parse_port(" 8080 ").unwrap(), 8080, "trimmed digits parse");
    }
}
