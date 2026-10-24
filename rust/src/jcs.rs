//! RFC 8785 JSON Canonicalization Scheme (JCS): the one bytes rule an alloy signs and a
//! continuum package is named by (its ContentId is the sha256 of its manifest's JCS bytes).
//!
//! - object members sorted by their names' UTF-16 code units, at every depth;
//! - numbers as ECMAScript `Number.prototype.toString` renders the IEEE-754 double;
//! - strings with only `"` `\` and C0 controls escaped (`\b \f \n \r \t`, else `\u00xx`);
//! - no insignificant whitespace.
//!
//! An integer beyond ±2^53 has no exact double, so it is refused rather than rounded. The
//! shared vectors in `test-vectors/jcs.json` pin this against Python, TypeScript and the
//! browser verifier.

use std::fmt;

use serde_json::{Number, Value};

/// The largest integer every JCS implementation holds exactly (2^53).
const SAFE_INTEGER: u64 = 1 << 53;

/// A value with no canonical form.
#[derive(Debug, Clone, PartialEq)]
pub enum CanonicalError {
    /// An integer no IEEE-754 double holds exactly.
    UnsafeInteger(Number),
    /// A number with no finite double.
    NotFinite(Number),
}

impl fmt::Display for CanonicalError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnsafeInteger(n) => write!(
                f,
                "integer {n} is outside ±2^53; RFC 8785 numbers are IEEE-754 doubles"
            ),
            Self::NotFinite(n) => write!(f, "number {n} has no finite double"),
        }
    }
}

impl std::error::Error for CanonicalError {}

/// The RFC 8785 bytes of `value`.
pub fn canonicalize(value: &Value) -> Result<Vec<u8>, CanonicalError> {
    let mut out = Vec::with_capacity(256);
    write(&mut out, value)?;
    Ok(out)
}

fn write(out: &mut Vec<u8>, value: &Value) -> Result<(), CanonicalError> {
    match value {
        Value::Null => out.extend_from_slice(b"null"),
        Value::Bool(true) => out.extend_from_slice(b"true"),
        Value::Bool(false) => out.extend_from_slice(b"false"),
        Value::Number(n) => write_number(out, n)?,
        Value::String(s) => write_str(out, s),
        Value::Array(items) => {
            out.push(b'[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(b',');
                }
                write(out, item)?;
            }
            out.push(b']');
        }
        Value::Object(map) => {
            let mut entries: Vec<(&String, &Value)> = map.iter().collect();
            entries.sort_unstable_by(|a, b| a.0.encode_utf16().cmp(b.0.encode_utf16()));
            out.push(b'{');
            for (i, (k, v)) in entries.into_iter().enumerate() {
                if i > 0 {
                    out.push(b',');
                }
                write_str(out, k);
                out.push(b':');
                write(out, v)?;
            }
            out.push(b'}');
        }
    }
    Ok(())
}

fn write_number(out: &mut Vec<u8>, n: &Number) -> Result<(), CanonicalError> {
    if let Some(u) = n.as_u64() {
        if u > SAFE_INTEGER {
            return Err(CanonicalError::UnsafeInteger(n.clone()));
        }
        out.extend_from_slice(u.to_string().as_bytes());
        return Ok(());
    }
    if let Some(i) = n.as_i64() {
        if i.unsigned_abs() > SAFE_INTEGER {
            return Err(CanonicalError::UnsafeInteger(n.clone()));
        }
        out.extend_from_slice(i.to_string().as_bytes());
        return Ok(());
    }
    match n.as_f64() {
        Some(x) if x.is_finite() => write_double(out, x, n),
        _ => Err(CanonicalError::NotFinite(n.clone())),
    }
}

/// ECMAScript Number::toString(x) for a finite double.
fn write_double(out: &mut Vec<u8>, x: f64, num: &Number) -> Result<(), CanonicalError> {
    if x == 0.0 {
        out.push(b'0'); // both zeros
        return Ok(());
    }
    if x < 0.0 {
        out.push(b'-');
    }
    // serde_json renders a double with ryu: the shortest digits that round-trip, the closest
    // on a tie, which are the digits ECMAScript chooses. Only the layout differs ("1e23",
    // "0.001", "100.0"), so take digits and decimal point from it and lay them out per ES.
    let text = num.to_string();
    let not_finite = || CanonicalError::NotFinite(num.clone());
    let unsigned = text.trim_start_matches('-');
    let (mantissa, exp) = match unsigned.split_once(['e', 'E']) {
        Some((m, e)) => (m, e.parse::<i32>().map_err(|_| not_finite())?),
        None => (unsigned, 0),
    };
    let (whole, frac) = match mantissa.split_once('.') {
        Some(parts) => parts,
        None => (mantissa, ""),
    };
    let all: Vec<u8> = whole.bytes().chain(frac.bytes()).collect();
    let lead = all.iter().take_while(|b| **b == b'0').count();
    let digits = &all[lead..];
    let digits = &digits[..digits.len() - digits.iter().rev().take_while(|b| **b == b'0').count()];
    if digits.is_empty() {
        return Err(not_finite());
    }
    let k = digits.len() as i32;
    // value = 0.d1d2..dk × 10^n
    let n = whole.len() as i32 + exp - lead as i32;
    if k <= n && n <= 21 {
        out.extend_from_slice(digits);
        out.extend(std::iter::repeat_n(b'0', (n - k) as usize));
    } else if 0 < n && n <= 21 {
        let (int, frac) = digits.split_at(n as usize);
        out.extend_from_slice(int);
        out.push(b'.');
        out.extend_from_slice(frac);
    } else if -6 < n && n <= 0 {
        out.extend_from_slice(b"0.");
        out.extend(std::iter::repeat_n(b'0', (-n) as usize));
        out.extend_from_slice(digits);
    } else {
        let e = n - 1;
        let (first, rest) = digits.split_at(1);
        out.extend_from_slice(first);
        if !rest.is_empty() {
            out.push(b'.');
            out.extend_from_slice(rest);
        }
        out.push(b'e');
        out.push(if e >= 0 { b'+' } else { b'-' });
        out.extend_from_slice(e.unsigned_abs().to_string().as_bytes());
    }
    Ok(())
}

fn write_str(out: &mut Vec<u8>, s: &str) {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    out.push(b'"');
    for &b in s.as_bytes() {
        match b {
            b'"' => out.extend_from_slice(b"\\\""),
            b'\\' => out.extend_from_slice(b"\\\\"),
            b'\n' => out.extend_from_slice(b"\\n"),
            b'\r' => out.extend_from_slice(b"\\r"),
            b'\t' => out.extend_from_slice(b"\\t"),
            0x08 => out.extend_from_slice(b"\\b"),
            0x0c => out.extend_from_slice(b"\\f"),
            0x00..=0x1f => {
                out.extend_from_slice(b"\\u00");
                out.push(HEX[usize::from(b >> 4)]);
                out.push(HEX[usize::from(b & 0x0f)]);
            }
            _ => out.push(b),
        }
    }
    out.push(b'"');
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    const VECTORS: &str = include_str!("../../test-vectors/jcs.json");

    fn vectors() -> Value {
        serde_json::from_str(VECTORS).unwrap()
    }

    fn items<'a>(v: &'a Value, key: &str) -> &'a Vec<Value> {
        v[key].as_array().unwrap()
    }

    // what this catches: any drift from ECMAScript number rendering on the shared RFC 8785
    // Appendix B vectors (exponent thresholds, shortest digits on near-ties, subnormals, -0).
    #[test]
    fn shared_number_vectors() {
        let v = vectors();
        for t in items(&v, "numbers") {
            let bits = u64::from_str_radix(t["bits"].as_str().unwrap(), 16).unwrap();
            let got = canonicalize(&Value::from(f64::from_bits(bits))).unwrap();
            assert_eq!(std::str::from_utf8(&got).unwrap(), t["expected"], "bits {bits:016x}");
        }
    }

    // what this catches: UTF-16 member order, escapes, whitespace and number re-rendering on
    // the shared documents (RFC 8785 §3.2.2 and §3.2.3 among them); needs serde_json's
    // float_roundtrip so 333333333.33333329 parses to the nearest double.
    #[test]
    fn shared_document_vectors() {
        let v = vectors();
        for t in items(&v, "documents") {
            let parsed: Value = serde_json::from_str(t["input"].as_str().unwrap()).unwrap();
            let got = canonicalize(&parsed).unwrap();
            assert_eq!(std::str::from_utf8(&got).unwrap(), t["expected"], "{}", t["name"]);
        }
    }

    // what this catches: an integer no double holds is refused, never rounded into bytes a
    // JavaScript verifier would compute differently; 2^53 itself passes.
    #[test]
    fn shared_unsafe_integers_are_refused() {
        let v = vectors();
        for t in items(&v, "unsafeIntegers") {
            let parsed: Value = serde_json::from_str(t.as_str().unwrap()).unwrap();
            assert!(
                matches!(canonicalize(&parsed), Err(CanonicalError::UnsafeInteger(_))),
                "{t}"
            );
        }
        assert_eq!(canonicalize(&json!(9_007_199_254_740_992u64)).unwrap(), b"9007199254740992");
    }
}
