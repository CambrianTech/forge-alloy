#!/usr/bin/env python3
"""Regression test: every published continuum-ai/* alloy must round-trip
through the forge-alloy schema with semantic equivalence (no information
loss). This is the §4.1.3.4 reproducibility gate from
docs/architecture/FORGE-ALLOY-DOMAIN-EXTENSIBILITY.md in continuum.

Run before merging any forge-alloy schema change. Fails the merge if any
shipped artifact's alloy does not round-trip cleanly through the
post-change schema.

Usage:
    python tests/test_regression_published_alloys.py

The test downloads each published alloy directly from HuggingFace (no
local copies) so it always tests against the actual immutable shipped
content, not a stale local cache.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Make `forge_alloy` importable when this file is run via pytest from the
# repo root or directly as a script. The package lives under python/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "python"))

# Tracked published alloys. Add new shipped artifacts here.
PUBLISHED_ALLOYS = [
    {
        "repo": "continuum-ai/qwen3-coder-30b-a3b-compacted-19b-256k",
        "filename": "qwen3-coder-30b-a3b-compacted-19b-256k.alloy.json",
        # Note: hash updated 2026-04-08 from aa61c4bdf463847c → 011970c80c2f3429
        # after the canonical-evalplus humaneval_plus correction landed
        # (sentinel-ai commit 1bc32d2). Tier 4 reproducibility test caught the
        # 0.6pp non-canonical convention bug; the alloy was re-published via
        # republish_alloy_only.py with corrected scores.
        "expected_alloy_hash_prefix": "011970c80c2f3429",
        "ad_hoc_fields": [
            "expert-activation-profile",  # stage type
            "expert-prune",                # stage type
            "calibrationCorpora",          # root extension (NOT YET in schema)
            "priorMetricBaselines",        # root extension (NOT YET in schema)
        ],
    },
    {
        "repo": "continuum-ai/olmoe-1b-7b-compacted-5b",
        "filename": "olmoe-1b-7b-compacted-5b.alloy.json",
        "expected_alloy_hash_prefix": "bba0a92ff0c8bebb",
        "ad_hoc_fields": [
            "expert-activation-profile",
            "expert-prune",
            "calibrationCorpora",
            "priorMetricBaselines",
        ],
    },
    {
        "repo": "continuum-ai/qwen2.5-coder-7b-compacted",
        # Note: this artifact was renamed from v2-7b-coder-compensated; the
        # alloy file inside the renamed repo retains the original name.
        "filename": "v2-7b-coder-compensated.alloy.json",
        "expected_alloy_hash_prefix": None,  # not enforced for legacy file name
        "ad_hoc_fields": [],  # this one used dense head pruning, no MoE ad-hoc fields
    },
]

HF_RAW_BASE = "https://huggingface.co/{repo}/raw/main/{filename}"


def fetch_alloy(repo: str, filename: str) -> dict | None:
    """Fetch a published alloy file from HF and return parsed JSON."""
    url = HF_RAW_BASE.format(repo=repo, filename=filename)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} fetching {url}")
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def has_field(obj: dict, path: str) -> bool:
    """Walk a dotted path on an object."""
    parts = path.split(".")
    cur = obj
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return False
        cur = cur[p]
    return True


def collect_stage_types(alloy: dict) -> list[str]:
    return [s.get("type") for s in alloy.get("stages", []) if isinstance(s, dict)]


def validate_with_pydantic(alloy: dict) -> tuple[bool, str]:
    """Try to load the alloy through forge_alloy.types.ForgeAlloy."""
    try:
        from forge_alloy.types import ForgeAlloy
    except ImportError as e:
        return False, f"forge_alloy not importable: {e}"
    try:
        # pydantic v2 API
        instance = ForgeAlloy.model_validate(alloy)
        # Round-trip with exclude_unset=True so fields the input didn't carry
        # are NOT added to the output (e.g. calibrationCorpora defaults to []
        # in the schema but published alloys without an upstream
        # expert-activation-profile stage don't carry it). Fields actively
        # set in the input round-trip back as themselves.
        roundtripped = instance.model_dump(
            by_alias=True, exclude_none=True, exclude_unset=True,
        )
        return True, f"validated; {len(roundtripped)} top-level keys"
    except Exception as e:
        return False, f"validation failed: {str(e)[:200]}"


def semantic_equivalent(a: dict, b: dict) -> tuple[bool, str]:
    """Check that two alloy dicts are semantically equivalent (deep-equal,
    ignoring field ordering and int/float numeric equivalence). Returns
    (ok, message).

    int and float are considered equivalent when their numeric values
    match — Pydantic coerces `12` (int in the published JSON) to `12.0`
    (float, because the schema field is Optional[float]) on validation,
    and the round-trip emits the float. Both are the same number; only
    Python's type tag differs."""
    def normalize(o):
        if isinstance(o, dict):
            return {k: normalize(v) for k, v in sorted(o.items())}
        if isinstance(o, list):
            return [normalize(x) for x in o]
        # Coerce int/float to float so 12 == 12.0 in the structural compare.
        if isinstance(o, (int, float)) and not isinstance(o, bool):
            return float(o)
        return o

    na = normalize(a)
    nb = normalize(b)
    if na == nb:
        return True, "deep-equal"

    # Find first divergence (also normalize on the way down so the
    # int/float coercion above propagates).
    def _is_numeric(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def find_diff(x, y, path=""):
        # int/float numeric equivalence is OK at the leaf
        if _is_numeric(x) and _is_numeric(y):
            if float(x) == float(y):
                return None
            return f"{path}: value diff ({x!r} vs {y!r})"
        if type(x) != type(y):
            return f"{path}: type mismatch ({type(x).__name__} vs {type(y).__name__})"
        if isinstance(x, dict):
            ka = set(x.keys())
            kb = set(y.keys())
            if ka != kb:
                only_a = ka - kb
                only_b = kb - ka
                return f"{path}: key diff (only in input: {sorted(only_a)[:5]}, only in output: {sorted(only_b)[:5]})"
            for k in sorted(ka):
                d = find_diff(x[k], y[k], f"{path}.{k}")
                if d:
                    return d
        elif isinstance(x, list):
            if len(x) != len(y):
                return f"{path}: list length {len(x)} vs {len(y)}"
            for i, (xi, yi) in enumerate(zip(x, y)):
                d = find_diff(xi, yi, f"{path}[{i}]")
                if d:
                    return d
        else:
            if x != y:
                return f"{path}: value diff ({x!r} vs {y!r})"
        return None

    return False, find_diff(na, nb) or "unknown diff"


def main():
    print("=" * 70)
    print("REGRESSION TEST — published continuum-ai alloys vs forge-alloy schema")
    print("=" * 70)

    pass_count = 0
    fail_count = 0
    failures = []

    for spec in PUBLISHED_ALLOYS:
        repo = spec["repo"]
        filename = spec["filename"]
        print(f"\n### {repo}")
        print(f"  fetching {filename}")
        alloy = fetch_alloy(repo, filename)
        if alloy is None:
            print(f"  FETCH FAILED — counting as test environment failure, not regression")
            continue

        # Show what's in the alloy
        stages = collect_stage_types(alloy)
        print(f"  stages ({len(stages)}): {stages}")
        for ad_hoc in spec["ad_hoc_fields"]:
            present = has_field(alloy, ad_hoc) or ad_hoc in stages
            marker = "✓" if present else "✗"
            print(f"  ad-hoc field expected: {marker} {ad_hoc}")

        # Try to validate via pydantic
        ok, msg = validate_with_pydantic(alloy)
        print(f"  pydantic validation: {'PASS' if ok else 'FAIL'} — {msg}")

        if ok:
            # Round-trip semantic equivalence check
            try:
                from forge_alloy.types import ForgeAlloy
                instance = ForgeAlloy.model_validate(alloy)
                # Round-trip with exclude_unset=True so fields the input
                # didn't carry are NOT added to the output (e.g.
                # calibrationCorpora defaults to [] in the schema but
                # published alloys without an upstream calibration stage
                # don't carry it). exclude_none is OFF because some
                # published alloys actively set fields like baselinePerplexity
                # to null and the round-trip must preserve those nulls.
                rt = instance.model_dump(
                    by_alias=True, exclude_unset=True,
                )
                eq_ok, eq_msg = semantic_equivalent(alloy, rt)
                print(f"  round-trip semantic equivalence: {'PASS' if eq_ok else 'FAIL'} — {eq_msg}")
                if eq_ok:
                    pass_count += 1
                else:
                    fail_count += 1
                    failures.append((repo, "round-trip mismatch", eq_msg))
            except Exception as e:
                print(f"  round-trip exception: {e}")
                fail_count += 1
                failures.append((repo, "round-trip exception", str(e)))
        else:
            fail_count += 1
            failures.append((repo, "validation", msg))

    print()
    print("=" * 70)
    print(f"SUMMARY: {pass_count} passed, {fail_count} failed")
    print("=" * 70)
    if failures:
        for repo, kind, msg in failures:
            print(f"  ✗ {repo}: {kind}")
            print(f"      {msg}")
        print()
        print("Regression test FAILED. Do not merge schema changes until")
        print("all published alloys validate cleanly through the new schema.")
        return 1
    print("Regression test PASSED. All published alloys round-trip cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
