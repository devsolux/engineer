//! Fixture: compiles, but carries a panic path, an undocumented unsafe block, and a debug leftover.

/// Parses a port number, panicking on bad input.
pub fn parse_port(text: &str) -> u16 {
    let port: u16 = text.trim().parse().unwrap();
    dbg!(port)
}

/// Reads the first byte through an unsafe block that has no safety comment.
pub fn first_byte(bytes: &[u8]) -> u8 {
    unsafe { *bytes.get_unchecked(0) }
}

#[cfg(test)]
mod tests {
    #[test]
    fn unwrap_in_tests_is_fine() {
        let v: Option<u8> = "1".parse().ok();
        assert_eq!(v.unwrap(), 1, "value {v:?}");
    }
}
