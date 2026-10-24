"""RFC 8785 (JCS) against the shared vectors every implementation must
reproduce byte for byte (test-vectors/jcs.json): Rust, TypeScript, the browser
verifier and continuum-pack read the same file or pin the same ids."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from forge_alloy.jcs import CanonicalError, canonicalize, canonicalize_text, content_id, number_to_string  # noqa: E402

VECTORS = json.loads((REPO_ROOT / "test-vectors" / "jcs.json").read_text(encoding="utf-8"))


# what this catches: drift from ECMAScript number rendering (RFC 8785 Appendix B:
# exponent thresholds, shortest digits on near-ties, subnormals, -0).
@pytest.mark.parametrize("vector", VECTORS["numbers"], ids=lambda v: v["bits"])
def test_number_vectors(vector):
    x = struct.unpack(">d", bytes.fromhex(vector["bits"]))[0]
    assert number_to_string(x) == vector["expected"]
    assert canonicalize(x).decode() == vector["expected"]


# what this catches: UTF-16 member order (not Python's code-point order), escapes,
# whitespace and number re-rendering on the shared documents.
@pytest.mark.parametrize("vector", VECTORS["documents"], ids=lambda v: v["name"])
def test_document_vectors(vector):
    assert canonicalize_text(vector["input"]).decode("utf-8") == vector["expected"]


# what this catches: a ContentId computed differently from continuum-pack's (one
# vector is its recorded TINY_V1 manifest; one the same value reordered).
@pytest.mark.parametrize("vector", VECTORS["contentIds"], ids=lambda v: v["name"])
def test_content_id_vectors(vector):
    assert content_id(json.loads(vector["input"])) == vector["contentId"]


# what this catches: Python's unbounded int committing to bytes a JavaScript
# verifier could never reproduce; refused instead of rounded.
@pytest.mark.parametrize("text", VECTORS["unsafeIntegers"])
def test_unsafe_integers_are_refused(text):
    with pytest.raises(CanonicalError):
        canonicalize_text(text)
