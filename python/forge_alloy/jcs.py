"""RFC 8785 JSON Canonicalization Scheme (JCS): the one bytes rule forge-alloy signs and
continuum packages are named by.

- object members sorted by their names' UTF-16 code units, at every depth;
- numbers as ECMAScript ``Number.prototype.toString`` renders the IEEE-754 double;
- strings with only ``"`` ``\\`` and C0 controls escaped (``\\b \\f \\n \\r \\t``, else ``\\u00xx``);
- no insignificant whitespace.

An integer beyond +/-2**53 has no exact double; it is refused rather than rounded, so a
Python signer never commits to bytes a JavaScript verifier would compute differently.
The shared vectors in ``test-vectors/jcs.json`` pin this against Rust, TypeScript and the
browser verifier.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

SAFE_INTEGER = 2**53

_ESCAPES = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


class CanonicalError(ValueError):
    """A value with no RFC 8785 form."""


def canonicalize(value: Any) -> bytes:
    """The RFC 8785 bytes of a JSON value (dict, list, str, int, float, bool, None)."""
    out: list[str] = []
    _write(out, value)
    return "".join(out).encode("utf-8")


def canonicalize_text(text: str | bytes) -> bytes:
    """Parse JSON text and return its RFC 8785 bytes."""
    return canonicalize(json.loads(text))


def content_id(value: Any) -> str:
    """``sha256:<64 hex>`` of the value's RFC 8785 bytes: a continuum package ContentId when
    the value is a package manifest."""
    return "sha256:" + hashlib.sha256(canonicalize(value)).hexdigest()


def _write(out: list[str], v: Any) -> None:
    if v is None:
        out.append("null")
    elif v is True:
        out.append("true")
    elif v is False:
        out.append("false")
    elif isinstance(v, int):
        if abs(v) > SAFE_INTEGER:
            raise CanonicalError(f"integer {v} is outside +/-2**53; RFC 8785 numbers are IEEE-754 doubles")
        out.append(str(v))
    elif isinstance(v, float):
        out.append(number_to_string(v))
    elif isinstance(v, str):
        _write_str(out, v)
    elif isinstance(v, (list, tuple)):
        out.append("[")
        for i, item in enumerate(v):
            if i:
                out.append(",")
            _write(out, item)
        out.append("]")
    elif isinstance(v, dict):
        out.append("{")
        for i, k in enumerate(sorted(v, key=_utf16_key)):
            if not isinstance(k, str):
                raise CanonicalError(f"object member name {k!r} is not a string")
            if i:
                out.append(",")
            _write_str(out, k)
            out.append(":")
            _write(out, v[k])
        out.append("}")
    else:
        raise CanonicalError(f"{type(v).__name__} is not a JSON value")


def _utf16_key(name: Any) -> bytes:
    return str(name).encode("utf-16-be", "surrogatepass")


def _write_str(out: list[str], s: str) -> None:
    out.append('"')
    for ch in s:
        esc = _ESCAPES.get(ch)
        if esc is not None:
            out.append(esc)
        elif ch < " ":
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')


def number_to_string(x: float) -> str:
    """ECMAScript Number::toString(x) for a finite double (ECMA-262 Number::toString)."""
    if not math.isfinite(x):
        raise CanonicalError(f"{x} has no JSON form")
    if x == 0:
        return "0"  # both zeros
    sign = "-" if x < 0 else ""
    # repr() is the shortest round-tripping digit string (closest on a tie), as in ECMAScript.
    r = repr(abs(x))
    mantissa, _, exp = r.partition("e")
    whole, _, frac = mantissa.partition(".")
    digits = whole + frac
    point = len(whole) + (int(exp) if exp else 0)
    stripped = digits.lstrip("0")
    point -= len(digits) - len(stripped)
    digits = stripped.rstrip("0")
    k, n = len(digits), point  # value = 0.d1..dk * 10**n
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        body = digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + ("+" if e >= 0 else "-") + str(abs(e))
    return sign + body
