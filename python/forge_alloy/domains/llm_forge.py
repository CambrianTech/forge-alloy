"""llm-forge — the ML model forging domain extension.

This domain owns the entire vocabulary for forging ML models: prune,
train, lora, expert-prune, expert-activation-profile, compensation-lora,
context-extend, modality, quant, eval, publish, package, deploy, deliver,
source-config. It also owns the §4.1.3.4 falsifiability anchor structures
(PriorMetricBaseline) and the §4.1.3.4.1 calibration-corpus discipline
gate structures (CalibrationCorpusRef).

Relationship to forge_alloy.types (the universal core):
    The bd4349d checkpoint commit on this branch bolted ML-specific
    fields directly into types.py — that was the wrong layer. The
    correct architecture is: types.py is a domain-agnostic envelope
    (Merkle chain of custody, integrity attestation, source/target,
    publication metadata), and EVERY ML-specific concept lives here in
    llm_forge.py.

    Today, this module RE-EXPORTS the ML types from types.py to satisfy
    the LlmForgeDomain.stage_types() contract while consumers (sentinel-ai,
    Continuum's Factory widget) still import from forge_alloy directly.
    The full extraction (moving the actual class definitions out of
    types.py and into this file) is a follow-up commit that lands as
    a pure refactor — every cached alloy still validates because the
    re-exported names are identical.

    The dependency direction is strict: extensions → core, never
    core → extensions. types.py NEVER imports from forge_alloy.domains.
    This is enforced by test_universal_core_does_not_import_llm_forge
    in test_domain_extension_layout.py.

Reproducibility contract: this domain extension MUST stay frozen against
the published continuum-ai/* alloy catalog. New ML methodology arrives
as NEW stage types or NEW alloy field discriminators registered here,
NEVER as edits to existing type definitions. The 17 published artifacts
all validate against the current contract; any change that breaks even
one of them is wrong.
"""

from __future__ import annotations

from .base import DomainExtension

# Re-export from the universal core's current location. The class
# definitions live in forge_alloy/types.py today (the bd4349d checkpoint
# state); this module re-exports them so the public API surface is
# stable while the universal-core extraction lands as a separate
# refactor commit. Consumers can import from EITHER:
#     from forge_alloy import ExpertPruneStage          (legacy public API)
#     from forge_alloy.domains.llm_forge import ExpertPruneStage   (new path)
# Both resolve to the same class object today.
from ..types import (
    # Stage types (transform, input, output, bookend)
    SourceConfigStage,
    PruneStage,
    TrainStage,
    LoRAStage,
    CompactStage,
    QuantStage,
    PackageStage,
    EvalStage,
    PublishStage,
    DeployStage,
    ExpertPruneStage,
    ExpertActivationProfileStage,
    CompensationLoRAStage,
    ContextExtendStage,
    ModalityStage,
    # Result types
    BenchmarkResult,
    BenchmarkDef,
    HardwareProfile,
    GenerationSample,
    AlloyResults,
    # § 4.1.3.4 falsifiability + discipline gate structures
    PriorMetricBaseline,
    CalibrationCorpusRef,
    # Hardware tier
    AlloyHardware,
)


class LlmForgeDomain(DomainExtension):
    """The llm-forge domain extension. Registered against id 'llm-forge'."""

    id = "llm-forge"

    def stage_types(self) -> dict[str, type]:
        """Stage types this domain owns. Used by the universal core's
        discriminated stage union when an alloy declares this domain in
        its domains[] field."""
        return {
            "source-config":             SourceConfigStage,
            "prune":                     PruneStage,
            "train":                     TrainStage,
            "lora":                      LoRAStage,
            "compact":                   CompactStage,
            "quant":                     QuantStage,
            "package":                   PackageStage,
            "eval":                      EvalStage,
            "publish":                   PublishStage,
            "deploy":                    DeployStage,
            "expert-prune":              ExpertPruneStage,
            "expert-activation-profile": ExpertActivationProfileStage,
            "compensation-lora":         CompensationLoRAStage,
            "context-extend":            ContextExtendStage,
            "modality":                  ModalityStage,
            # 'deliver' is a legacy alias used by older alloys for what is
            # now called 'publish' — both resolve to PublishStage so the
            # legacy alloys keep validating without a separate stage class.
            "deliver":                   PublishStage,
        }

    def root_extensions(self) -> dict[str, type]:
        """Root-extension fields this domain adds to the alloy root.

        These are the §4.1.3.4 / §4.1.3.4.1 structures from the
        methodology paper:

            calibrationCorpora    list[CalibrationCorpusRef]
                                  hash-pinned calibration corpora used by
                                  any expert-activation-profile or
                                  compensation-lora stage in this alloy
            priorMetricBaselines  list[PriorMetricBaseline]
                                  superseded forge attempts preserved as
                                  falsifiability anchors (the §4.1.3.4
                                  negative-baseline pattern)
        """
        return {
            "calibrationCorpora":   CalibrationCorpusRef,
            "priorMetricBaselines": PriorMetricBaseline,
        }


__all__ = [
    "LlmForgeDomain",
    # Stage types (re-exported for callers that import from this module)
    "SourceConfigStage",
    "PruneStage",
    "TrainStage",
    "LoRAStage",
    "CompactStage",
    "QuantStage",
    "PackageStage",
    "EvalStage",
    "PublishStage",
    "DeployStage",
    "ExpertPruneStage",
    "ExpertActivationProfileStage",
    "CompensationLoRAStage",
    "ContextExtendStage",
    "ModalityStage",
    # Result types
    "BenchmarkResult",
    "BenchmarkDef",
    "HardwareProfile",
    "GenerationSample",
    "AlloyResults",
    "AlloyHardware",
    # § 4.1.3.4 structures
    "PriorMetricBaseline",
    "CalibrationCorpusRef",
]
