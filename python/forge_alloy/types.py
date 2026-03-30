"""ForgeAlloy type definitions — mirrors Rust source of truth."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field


class AlloySource(BaseModel):
    base_model: str = Field(alias="baseModel")
    architecture: str
    revision: Optional[str] = None
    is_moe: bool = Field(default=False, alias="isMoE")
    total_experts: Optional[int] = Field(default=None, alias="totalExperts")

    model_config = {"populate_by_name": True}


# ── Results (populated after execution) ────────────────────────────────────


class BenchmarkResult(BaseModel):
    """A single benchmark result. Metrics are open-ended — each benchmark
    reports whatever it wants (passing, total, accuracy, score, etc.)"""
    name: str
    subset: Optional[str] = None
    metrics: dict[str, Union[int, float, str, bool]] = Field(default_factory=dict)
    submitted_to_leaderboard: bool = Field(default=False, alias="submittedToLeaderboard")
    result_hash: Optional[str] = Field(default=None, alias="resultHash")

    model_config = {"populate_by_name": True}


class HardwareProfile(BaseModel):
    """Verified performance on a specific device — generates model card device grid."""
    device: str
    format: str
    size_gb: Optional[float] = Field(default=None, alias="sizeGb")
    tokens_per_sec: Optional[float] = Field(default=None, alias="tokensPerSec")
    memory_usage_gb: Optional[float] = Field(default=None, alias="memoryUsageGb")
    verified: bool = False

    model_config = {"populate_by_name": True}


class GenerationSample(BaseModel):
    """Raw model output sample — no cherry-picking, no post-processing."""
    label: str
    prompt: str
    completion: str
    baseline_completion: Optional[str] = Field(default=None, alias="baselineCompletion")

    model_config = {"populate_by_name": True}


class IntegrityAttestation(BaseModel):
    """Cryptographic attestation for verified benchmark execution."""
    model_hash: str = Field(alias="modelHash")
    alloy_hash: Optional[str] = Field(default=None, alias="alloyHash")
    environment_hash: Optional[str] = Field(default=None, alias="environmentHash")
    environment: Optional[str] = None
    signer: Optional[str] = None
    signature: Optional[str] = None
    attested_at: Optional[str] = Field(default=None, alias="attestedAt")

    model_config = {"populate_by_name": True}


class AlloyResults(BaseModel):
    """Complete results from executing an alloy pipeline.
    Empty in a recipe alloy, populated after forging."""
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    duration_minutes: Optional[float] = Field(default=None, alias="durationMinutes")
    baseline_perplexity: Optional[float] = Field(default=None, alias="baselinePerplexity")
    final_perplexity: Optional[float] = Field(default=None, alias="finalPerplexity")
    improvement_pct: Optional[float] = Field(default=None, alias="improvementPct")
    final_size_gb: Optional[float] = Field(default=None, alias="finalSizeGb")
    final_params: Optional[str] = Field(default=None, alias="finalParams")
    benchmarks: list[BenchmarkResult] = Field(default_factory=list)
    hardware_verified: list[HardwareProfile] = Field(default_factory=list, alias="hardwareVerified")
    samples: list[GenerationSample] = Field(default_factory=list)
    integrity: Optional[IntegrityAttestation] = None

    model_config = {"populate_by_name": True}


# ── Stages ──────────────────────────────────────────────────────────────────


class PruneStage(BaseModel):
    type: Literal["prune"] = "prune"
    strategy: Literal["entropy", "magnitude", "gradient", "random"]
    level: float = Field(ge=0.0, le=0.9)
    min_heads_per_layer: int = Field(default=4, alias="minHeadsPerLayer")
    min_kv_heads_per_layer: int = Field(default=2, alias="minKvHeadsPerLayer")
    analysis_steps: int = Field(default=200, alias="analysisSteps")

    model_config = {"populate_by_name": True}


class TrainStage(BaseModel):
    type: Literal["train"] = "train"
    domain: str
    dataset: Optional[str] = None
    steps: int = Field(ge=1)
    learning_rate: str = Field(alias="learningRate")
    batch_size: int = Field(default=4, ge=1, le=64, alias="batchSize")
    gradient_accumulation: int = Field(default=1, ge=1, le=16, alias="gradientAccumulation")
    scheduler: Literal["cosine", "linear", "constant", "constant_with_warmup", "polynomial"] = "cosine"
    warmup_ratio: float = Field(default=0.03, ge=0.0, le=1.0, alias="warmupRatio")
    weight_decay: float = Field(default=0.01, ge=0.0, le=1.0, alias="weightDecay")
    max_gradient_norm: float = Field(default=1.0, ge=0.0, le=10.0, alias="maxGradientNorm")
    precision: Literal["bf16", "fp16", "fp32"] = "bf16"
    sequence_length: int = Field(default=2048, ge=128, le=131072, alias="sequenceLength")
    optimizations: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class LoRAStage(BaseModel):
    type: Literal["lora"] = "lora"
    rank: int = Field(default=32, ge=1, le=256)
    alpha: Optional[int] = Field(default=None, ge=1, le=512)
    dropout: float = Field(default=0.05, ge=0.0, le=1.0)
    target_modules: list[str] = Field(default=["q_proj", "k_proj", "v_proj", "o_proj"], alias="targetModules")
    quantize: bool = True
    quantize_bits: Literal[4, 8] = Field(default=4, alias="quantizeBits")
    dataset: Optional[str] = None
    epochs: int = Field(default=3, ge=1, le=20)
    learning_rate: str = Field(default="1e-4", alias="learningRate")
    batch_size: int = Field(default=4, ge=1, le=64, alias="batchSize")
    merge_after: bool = Field(default=False, alias="mergeAfter")

    model_config = {"populate_by_name": True}


class CompactStage(BaseModel):
    type: Literal["compact"] = "compact"
    dead_threshold: float = Field(default=0.1, ge=0.0, le=1.0, alias="deadThreshold")
    dormant_threshold: float = Field(default=0.2, ge=0.0, le=1.0, alias="dormantThreshold")
    low_threshold: float = Field(default=0.3, ge=0.0, le=1.0, alias="lowThreshold")
    medium_threshold: float = Field(default=0.5, ge=0.0, le=1.0, alias="mediumThreshold")
    high_threshold: float = Field(default=0.7, ge=0.0, le=1.0, alias="highThreshold")
    target_size_gb: Optional[float] = Field(default=None, alias="targetSizeGb")
    enable_quantization: bool = Field(default=True, alias="enableQuantization")

    model_config = {"populate_by_name": True}


class QuantStage(BaseModel):
    type: Literal["quant"] = "quant"
    format: Literal["gguf", "mlx", "safetensors", "onnx"]
    quant_types: list[str] = Field(alias="quantTypes")
    device_targets: list[str] = Field(default_factory=list, alias="deviceTargets")

    model_config = {"populate_by_name": True}


class BenchmarkDef(BaseModel):
    name: str
    subset: Optional[str] = None
    n_shot: Optional[int] = Field(default=None, alias="nShot")
    submit_to_leaderboard: bool = Field(default=False, alias="submitToLeaderboard")

    model_config = {"populate_by_name": True}


class EvalStage(BaseModel):
    type: Literal["eval"] = "eval"
    benchmarks: list[BenchmarkDef]
    passing_threshold: Optional[float] = Field(default=None, alias="passingThreshold")
    compare_to_base: bool = Field(default=True, alias="compareToBase")

    model_config = {"populate_by_name": True}


class PublishStage(BaseModel):
    type: Literal["publish"] = "publish"
    org: str
    repo_name_template: str = Field(default="{base}-{domain}-forged", alias="repoNameTemplate")
    include_alloy: bool = Field(default=True, alias="includeAlloy")
    card_from_benchmarks: bool = Field(default=True, alias="cardFromBenchmarks")
    tags: list[str] = Field(default_factory=list)
    private: bool = False

    model_config = {"populate_by_name": True}


class ExpertPruneStage(BaseModel):
    type: Literal["expert-prune"] = "expert-prune"
    keep_experts: int = Field(ge=1, alias="keepExperts")
    selection_strategy: Literal["activation", "gradient", "random"] = Field(default="activation", alias="selectionStrategy")
    profile_dataset: Optional[str] = Field(default=None, alias="profileDataset")
    profile_steps: int = Field(default=100, ge=1, alias="profileSteps")

    model_config = {"populate_by_name": True}


class ContextExtendStage(BaseModel):
    type: Literal["context-extend"] = "context-extend"
    target_length: int = Field(ge=1024, alias="targetLength")
    method: Literal["yarn", "ntk", "linear", "dynamic-ntk"]
    training_dataset: Optional[str] = Field(default=None, alias="trainingDataset")
    training_steps: Optional[int] = Field(default=None, alias="trainingSteps")

    model_config = {"populate_by_name": True}


class ModalityStage(BaseModel):
    type: Literal["modality"] = "modality"
    modality: Literal["vision", "audio", "multimodal"]
    encoder_model: str = Field(alias="encoderModel")
    projection_arch: Literal["mlp", "cross-attention", "linear"] = Field(default="mlp", alias="projectionArch")
    freeze_base: bool = Field(default=True, alias="freezeBase")
    freeze_encoder: bool = Field(default=True, alias="freezeEncoder")
    training_dataset: Optional[str] = Field(default=None, alias="trainingDataset")
    training_steps: Optional[int] = Field(default=None, alias="trainingSteps")
    projection_dim: Optional[int] = Field(default=None, alias="projectionDim")

    model_config = {"populate_by_name": True}


# Discriminated union for stages
AlloyStage = (
    PruneStage | TrainStage | LoRAStage | CompactStage |
    QuantStage | EvalStage | PublishStage | ExpertPruneStage |
    ContextExtendStage | ModalityStage
)


class AlloyHardware(BaseModel):
    min_vram_gb: Optional[float] = Field(default=None, alias="minVramGb")
    recommended_vram_gb: Optional[float] = Field(default=None, alias="recommendedVramGb")
    estimated_duration_minutes: Optional[float] = Field(default=None, alias="estimatedDurationMinutes")
    supports_cpu: bool = Field(default=False, alias="supportsCPU")
    tested_on: list[str] = Field(default_factory=list, alias="testedOn")

    model_config = {"populate_by_name": True}


class OutputArtifact(BaseModel):
    type: str
    description: str = ""


class AlloyOutputs(BaseModel):
    produces: list[OutputArtifact] = Field(default_factory=list)


class ForgeAlloy(BaseModel):
    name: str
    version: str
    description: str = ""
    author: str = ""
    tags: list[str] = Field(default_factory=list)
    license: str = "apache-2.0"

    source: AlloySource
    stages: list[AlloyStage] = Field(discriminator="type")
    cycles: int = Field(default=1, ge=1)

    hardware: Optional[AlloyHardware] = None
    outputs: Optional[AlloyOutputs] = None

    # Populated after execution — benchmark scores, hardware verification, samples
    results: Optional[AlloyResults] = None

    source_alloy_id: Optional[str] = Field(default=None, alias="sourceAlloyId")
    forged_model_ids: Optional[list[str]] = Field(default=None, alias="forgedModelIds")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_file(cls, path: str | Path) -> "ForgeAlloy":
        """Load an alloy from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.model_validate(data)

    def to_file(self, path: str | Path) -> None:
        """Save alloy to a JSON file."""
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2, by_alias=True))

    def validate_alloy(self) -> list[str]:
        """Additional validation beyond Pydantic type checks."""
        errors = []
        if not self.stages:
            errors.append("At least one stage is required")
        for i, stage in enumerate(self.stages):
            if isinstance(stage, PruneStage) and (stage.level < 0 or stage.level > 0.9):
                errors.append(f"stage[{i}] prune level must be 0.0-0.9")
        return errors

    @property
    def has_results(self) -> bool:
        """Check if this alloy has been executed."""
        return self.results is not None

    @property
    def is_attested(self) -> bool:
        """Check if results have integrity attestation with a signature."""
        return (
            self.results is not None
            and self.results.integrity is not None
            and self.results.integrity.signature is not None
        )
