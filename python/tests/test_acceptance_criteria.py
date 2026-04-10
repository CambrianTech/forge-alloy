"""TDD spec for ForgeAlloy.acceptanceCriteria — the part spec.

In the assembly-line metaphor every part has a spec sheet that travels
with it down the line. The alloy IS the part spec — it carries the
recipe (stages), the source, the integrity attestation, AND the gate
the part must clear before the shipping department releases it.

`acceptanceCriteria` is that gate, declared by the recipe author and
self-contained in the alloy file. Sentinel-ai forges and assays; it
NEVER reads acceptanceCriteria. Continuum (the shipping department)
reads BOTH the assayed scores and the alloy's acceptanceCriteria, and
decides ship vs rework. The same alloy gives the same gate verdict on
any forge run by anyone, anywhere — that's the portability the spec
guarantees.

Schema:
    acceptanceCriteria: {
        benchmarks: {
            <benchmark_name>: { min: float, anchorDelta?: float, anchorBenchmark?: str }
        },
        hardware?: { maxVramGb?: float, deviceTier?: str },
        integrity?: { modelHashRequired?: bool, samplesPathRequired?: bool }
    }

  benchmarks.<name>.min            — absolute pass@1 floor (0..1)
  benchmarks.<name>.anchorDelta    — §4.1.3.4 discipline gate: the
                                     forged score must be within Δ of
                                     the base anchor measured in the
                                     SAME eval pipeline. Negative means
                                     forged ≥ anchor + delta (i.e. -3
                                     means forged must be ≥ anchor−3).
  hardware.maxVramGb               — must fit in this VRAM after quant
  integrity.modelHashRequired      — modelHash must be present + valid

Tests:
  1. AcceptanceCriteria class importable from forge_alloy
  2. ForgeAlloy.acceptanceCriteria field exists, defaults to None
  3. Round-trip via model_dump_json + from_file preserves the field
  4. Pydantic validates min as 0..1 float
  5. Pydantic validates each benchmark entry is a BenchmarkAcceptance
  6. Backwards compat: existing alloys without acceptanceCriteria load
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _minimal_alloy_dict() -> dict:
    return {
        "name": "test-alloy",
        "version": "0.1.0",
        "source": {"baseModel": "Test/Base", "architecture": "qwen3_moe"},
        "stages": [
            {"type": "prune", "level": 0.3, "strategy": "entropy"},
        ],
    }


# ── AcceptanceCriteria class importable ─────────────────────────────────────


def test_acceptance_criteria_class_importable():
    from forge_alloy.types import AcceptanceCriteria, BenchmarkAcceptance
    assert AcceptanceCriteria is not None
    assert BenchmarkAcceptance is not None


def test_benchmark_acceptance_validates_min_as_fraction():
    from forge_alloy.types import BenchmarkAcceptance
    ok = BenchmarkAcceptance(min=0.55)
    assert ok.min == 0.55
    # Optional anchorDelta
    with_delta = BenchmarkAcceptance(min=0.78, anchorDelta=-3.0, anchorBenchmark="humaneval_plus")
    assert with_delta.anchor_delta == -3.0
    assert with_delta.anchor_benchmark == "humaneval_plus"


def test_benchmark_acceptance_rejects_out_of_range_min():
    from forge_alloy.types import BenchmarkAcceptance
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        BenchmarkAcceptance(min=1.5)
    with pytest.raises(ValidationError):
        BenchmarkAcceptance(min=-0.1)


# ── ForgeAlloy.acceptanceCriteria field ─────────────────────────────────────


def test_forge_alloy_has_acceptance_criteria_field():
    from forge_alloy.types import ForgeAlloy
    alloy = ForgeAlloy.model_validate(_minimal_alloy_dict())
    # Default is None — the field is optional, backwards compat
    assert alloy.acceptance_criteria is None


def test_forge_alloy_accepts_acceptance_criteria_in_payload():
    from forge_alloy.types import ForgeAlloy
    payload = _minimal_alloy_dict()
    payload["acceptanceCriteria"] = {
        "benchmarks": {
            "humaneval_plus": {"min": 0.78, "anchorDelta": -3.0, "anchorBenchmark": "humaneval_plus"},
            "ifeval": {"min": 0.55},
            "mmlu_pro": {"min": 0.42},
        },
        "hardware": {"maxVramGb": 24.0},
        "integrity": {"modelHashRequired": True},
    }
    alloy = ForgeAlloy.model_validate(payload)
    assert alloy.acceptance_criteria is not None
    bench = alloy.acceptance_criteria.benchmarks
    assert bench["humaneval_plus"].min == 0.78
    assert bench["humaneval_plus"].anchor_delta == -3.0
    assert bench["ifeval"].min == 0.55
    assert alloy.acceptance_criteria.hardware.max_vram_gb == 24.0
    assert alloy.acceptance_criteria.integrity.model_hash_required is True


def test_forge_alloy_round_trip_preserves_acceptance_criteria(tmp_path):
    from forge_alloy.types import ForgeAlloy
    payload = _minimal_alloy_dict()
    payload["acceptanceCriteria"] = {
        "benchmarks": {
            "ifeval": {"min": 0.55},
            "mmlu_pro": {"min": 0.42},
        },
        "hardware": {"maxVramGb": 24.0},
    }
    alloy = ForgeAlloy.model_validate(payload)

    out = tmp_path / "rt.alloy.json"
    alloy.to_file(out)
    text = out.read_text()
    # The serialized JSON MUST use the camelCase alias the spec ships under
    assert "acceptanceCriteria" in text
    assert "maxVramGb" in text

    reloaded = ForgeAlloy.from_file(out)
    assert reloaded.acceptance_criteria is not None
    assert reloaded.acceptance_criteria.benchmarks["ifeval"].min == 0.55
    assert reloaded.acceptance_criteria.benchmarks["mmlu_pro"].min == 0.42
    assert reloaded.acceptance_criteria.hardware.max_vram_gb == 24.0


def test_forge_alloy_backwards_compat_alloys_without_criteria_load():
    """Every existing published continuum-ai/* alloy must keep loading
    after this field is added — it's optional with default None."""
    from forge_alloy.types import ForgeAlloy
    alloy = ForgeAlloy.model_validate(_minimal_alloy_dict())
    assert alloy.acceptance_criteria is None
    # And serializes cleanly without the field
    text = alloy.model_dump_json(by_alias=True, exclude_none=True)
    assert "acceptanceCriteria" not in text


# ── The §4.1.3.4 anchor delta semantic check ────────────────────────────────


def test_anchor_delta_carries_negative_threshold_for_4_1_3_4_gate():
    """anchorDelta = -3.0 means 'forged score must be within 3 points
    BELOW the base anchor measured in the same eval pipeline'. Negative
    is the correct sign convention because the forged score is allowed
    to drop slightly relative to the base — the §4.1.3.4 discipline is
    'how much drop is OK', not 'how much must we exceed'."""
    from forge_alloy.types import BenchmarkAcceptance
    crit = BenchmarkAcceptance(min=0.78, anchorDelta=-3.0, anchorBenchmark="humaneval_plus")
    assert crit.anchor_delta == -3.0
    assert crit.anchor_delta < 0
