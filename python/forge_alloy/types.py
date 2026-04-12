"""ForgeAlloy type definitions — mirrors Rust source of truth."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union
from pydantic import BaseModel, Field


class AlloySource(BaseModel):
    base_model: str = Field(alias="baseModel")
    architecture: str
    revision: Optional[str] = None
    is_moe: bool = Field(default=False, alias="isMoE")
    total_experts: Optional[int] = Field(default=None, alias="totalExperts")

    model_config = {"populate_by_name": True, "extra": "allow"}


# ── Results (populated after execution) ────────────────────────────────────


class BenchmarkResult(BaseModel):
    """A single benchmark result. Carries the canonical fields the publish
    pipeline (alloy_to_card.py) and the Tier 4 reproducibility test both
    consume:

        score          The student's pass@1 / accuracy / etc.
        baseScore      The unmodified base anchor's same metric, measured on
                       the same hardware in the same eval pipeline (per the
                       § 4.1.4.1 anchor-reproduction discipline gate).
        delta          score - baseScore (preserved in the alloy so the
                       published Δ doesn't drift if either side is rounded).
        metric         The metric name (typically 'pass@1' for code benchmarks).
        samplesPath    The per-problem JSONL the student score was computed
                       from. Tier 3 hashes this against resultHash.
        baseSamplesPath The base anchor's samples JSONL.
        resultHash     sha256 of the student samples bytes (Merkle anchor).
        baseResultHash sha256 of the base samples bytes.
        calibrated     True if the score is the calibration-anchored value
                       per § 4.1.4.1 discipline.

    Plus the legacy `metrics` open-ended dict for benchmarks that report
    multiple sub-scores (e.g. lm-eval-harness MMLU sub-tasks).
    """
    name: str
    subset: Optional[str] = None
    metric: Optional[str] = None
    score: Optional[float] = None
    base_score: Optional[float] = Field(default=None, alias="baseScore")
    delta: Optional[float] = None
    calibrated: Optional[bool] = None
    samples_path: Optional[str] = Field(default=None, alias="samplesPath")
    base_samples_path: Optional[str] = Field(default=None, alias="baseSamplesPath")
    result_hash: Optional[str] = Field(default=None, alias="resultHash")
    base_result_hash: Optional[str] = Field(default=None, alias="baseResultHash")
    metrics: dict[str, Union[int, float, str, bool]] = Field(default_factory=dict)
    submitted_to_leaderboard: bool = Field(default=False, alias="submittedToLeaderboard")

    # extra="allow" so artifact-specific extras (per-benchmark notes,
    # methodology anchor URLs, etc.) round-trip cleanly. The named fields
    # above are the canonical surface that publish_model.py and
    # alloy_to_card.py read.
    model_config = {"populate_by_name": True, "extra": "allow"}


class HardwareProfile(BaseModel):
    """Verified performance on a specific device — generates model card device grid."""
    device: str
    format: Optional[str] = None
    vram_gb: Optional[float] = Field(default=None, alias="vramGb")
    size_gb: Optional[float] = Field(default=None, alias="sizeGb")
    tokens_per_sec: Optional[float] = Field(default=None, alias="tokensPerSec")
    memory_usage_gb: Optional[float] = Field(default=None, alias="memoryUsageGb")
    verified: bool = False

    model_config = {"populate_by_name": True, "extra": "allow"}


class GenerationSample(BaseModel):
    """Raw model output sample — no cherry-picking, no post-processing."""
    label: str
    prompt: str
    completion: str
    baseline_completion: Optional[str] = Field(default=None, alias="baselineCompletion")

    model_config = {"populate_by_name": True, "extra": "allow"}


class CodeAttestation(BaseModel):
    """Attestation of the code that produced results — proves the forge runner is genuine."""
    runner: str
    version: str
    binary_hash: str = Field(alias="binaryHash")
    source_hash: Optional[str] = Field(default=None, alias="sourceHash")
    commit: Optional[str] = None
    environment: Optional[str] = None
    environment_hash: Optional[str] = Field(default=None, alias="environmentHash")

    model_config = {"populate_by_name": True, "extra": "allow"}


class DatasetAttestation(BaseModel):
    """Attestation of a benchmark dataset — proves eval used unmodified data."""
    name: str
    version: Optional[str] = None
    hash: str
    source: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AttestationSignature(BaseModel):
    """Signature over attestation payload (RFC 8785 JCS canonical form).
    Verifiers MUST check publicKey against registry, not trust it directly."""
    algorithm: Literal["ES256", "ES384", "EdDSA", "ML-DSA-65", "ML-DSA-87", "SLH-DSA-128s"]
    public_key: str = Field(alias="publicKey")
    value: str
    key_id: Optional[str] = Field(default=None, alias="keyId")
    credential_id: Optional[str] = Field(default=None, alias="credentialId")
    certificate_chain: list[str] = Field(default_factory=list, alias="certificateChain")
    key_registry: Optional[str] = Field(default=None, alias="keyRegistry")

    model_config = {"populate_by_name": True, "extra": "allow"}


class IntegrityAttestation(BaseModel):
    """Cryptographic attestation modeled after FIDO2/WebAuthn.
    Self-attested only prevents accidental corruption, NOT adversarial modification.
    Only enclave tier provides tamper-proof guarantees."""
    trust_level: Literal["self-attested", "verified", "enclave"] = Field(default="self-attested", alias="trustLevel")
    code: Optional[CodeAttestation] = None
    model_hash: Optional[str] = Field(default=None, alias="modelHash")
    alloy_hash: Optional[str] = Field(default=None, alias="alloyHash")
    datasets: list[DatasetAttestation] = Field(default_factory=list)
    nonce: Optional[str] = None
    audience: Optional[str] = None
    signature: Optional[AttestationSignature] = None
    anchor: Optional["TrustAnchor"] = None
    certifications: list["AdapterAttestation"] = Field(default_factory=list)
    attested_at: Optional[str] = Field(default=None, alias="attestedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AdapterAttestation(BaseModel):
    """Third-party adapter attestation — independent certification for one chain element.
    Each approved adapter has its own keypair and signs its own results.
    Like UL certification: the adapter is an independent authority that tested
    one aspect of the model and vouches for it with its own passkey."""
    adapter: str
    version: str
    domain: str
    result: dict[str, Any] = Field(default_factory=dict)
    adapter_hash: Optional[str] = Field(default=None, alias="adapterHash")
    signature: Optional[AttestationSignature] = None
    nonce: Optional[str] = None
    source_repo: Optional[str] = Field(default=None, alias="sourceRepo")
    commit: Optional[str] = None
    attested_at: str = Field(alias="attestedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}


class TrustAnchor(BaseModel):
    """External trust anchor — immutable proof attestation existed at a point in time."""
    anchor_type: Literal["blockchain", "merkle-root", "rfc3161", "ipfs", "custom"] = Field(alias="anchorType")
    anchored_hash: str = Field(alias="anchoredHash")
    location: str
    anchored_at: Optional[str] = Field(default=None, alias="anchoredAt")
    network: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


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
    # MoE-specific param counts shipped on the morning's qwen3-coder-30b-a3b
    # and OLMoE flagships (forgedParamsB after expert pruning, activeParamsB
    # is unchanged because expert pruning doesn't change activation count).
    forged_params_b: Optional[float] = Field(default=None, alias="forgedParamsB")
    active_params_b: Optional[float] = Field(default=None, alias="activeParamsB")
    benchmarks: list[BenchmarkResult] = Field(default_factory=list)
    hardware_verified: list[HardwareProfile] = Field(default_factory=list, alias="hardwareVerified")
    samples: list[GenerationSample] = Field(default_factory=list)
    integrity: Optional[IntegrityAttestation] = None

    # extra="allow" so artifact-specific result extras (fourRunProgression,
    # lossFunctionAblation, etc. on v2-7b-coder-compensated) round-trip
    # cleanly. The schema's named fields are the canonical surface; extras
    # are recognized as artifact-specific provenance and preserved verbatim.
    model_config = {"populate_by_name": True, "extra": "allow"}


# ── Stages ──────────────────────────────────────────────────────────────────


class PruneStage(BaseModel):
    type: Literal["prune"] = "prune"
    # Strategy enum extended with activation-magnitude (the §4.1.3.1 fix metric
    # used by the v2-7B forge published as continuum-ai/qwen2.5-coder-7b-compacted)
    # and per-layer-normalized-* variants surfaced by the §4.1.3.4 work.
    strategy: Literal[
        "entropy",
        "magnitude",
        "gradient",
        "random",
        "activation-magnitude",
        "calibration-aware-activation-count",
        "per-layer-normalized-router-importance",
    ]
    level: float = Field(ge=0.0, le=0.9)
    min_heads_per_layer: int = Field(default=4, alias="minHeadsPerLayer")
    min_kv_heads_per_layer: int = Field(default=2, alias="minKvHeadsPerLayer")
    analysis_steps: int = Field(default=200, alias="analysisSteps")
    # Optional methodology metadata fields used by post-§4.1.3 forges
    per_layer_normalized: Optional[bool] = Field(default=None, alias="perLayerNormalized")
    defrag_mode: Optional[str] = Field(default=None, alias="defragMode")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class TrainStage(BaseModel):
    type: Literal["train"] = "train"
    # domain / steps / learning_rate are OPTIONAL — when omitted, the
    # family adapter's default_train_params() hook fills them in at
    # execution time. Recipe authors only need to specify these when
    # they want to override the family-default. Adapter-driven > seeder-hardcoded.
    domain: Optional[str] = None
    dataset: Optional[str] = None
    steps: Optional[int] = Field(default=None, ge=1)
    learning_rate: Optional[str] = Field(default=None, alias="learningRate")
    batch_size: int = Field(default=4, ge=1, le=64, alias="batchSize")
    gradient_accumulation: int = Field(default=1, ge=1, le=16, alias="gradientAccumulation")
    scheduler: Literal["cosine", "linear", "constant", "constant_with_warmup", "polynomial"] = "cosine"
    warmup_ratio: float = Field(default=0.03, ge=0.0, le=1.0, alias="warmupRatio")
    weight_decay: float = Field(default=0.01, ge=0.0, le=1.0, alias="weightDecay")
    max_gradient_norm: float = Field(default=1.0, ge=0.0, le=10.0, alias="maxGradientNorm")
    precision: Literal["bf16", "fp16", "fp32"] = "bf16"
    sequence_length: int = Field(default=2048, ge=128, le=131072, alias="sequenceLength")
    optimizations: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "extra": "allow"}


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

    model_config = {"populate_by_name": True, "extra": "allow"}


class CompactStage(BaseModel):
    type: Literal["compact"] = "compact"
    dead_threshold: float = Field(default=0.1, ge=0.0, le=1.0, alias="deadThreshold")
    dormant_threshold: float = Field(default=0.2, ge=0.0, le=1.0, alias="dormantThreshold")
    low_threshold: float = Field(default=0.3, ge=0.0, le=1.0, alias="lowThreshold")
    medium_threshold: float = Field(default=0.5, ge=0.0, le=1.0, alias="mediumThreshold")
    high_threshold: float = Field(default=0.7, ge=0.0, le=1.0, alias="highThreshold")
    target_size_gb: Optional[float] = Field(default=None, alias="targetSizeGb")
    enable_quantization: bool = Field(default=True, alias="enableQuantization")

    model_config = {"populate_by_name": True, "extra": "allow"}


class QuantStage(BaseModel):
    type: Literal["quant"] = "quant"
    format: Literal["gguf", "mlx", "safetensors", "onnx"]
    quant_types: list[str] = Field(alias="quantTypes")
    device_targets: list[str] = Field(default_factory=list, alias="deviceTargets")

    model_config = {"populate_by_name": True, "extra": "allow"}


class BenchmarkDef(BaseModel):
    name: str
    subset: Optional[str] = None
    n_shot: Optional[int] = Field(default=None, alias="nShot")
    submit_to_leaderboard: bool = Field(default=False, alias="submitToLeaderboard")
    samples_path: Optional[str] = Field(default=None, alias="samplesPath")
    base_samples_path: Optional[str] = Field(default=None, alias="baseSamplesPath")
    calibration_anchor: Optional[dict[str, Any]] = Field(default=None, alias="calibrationAnchor")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class EvalStage(BaseModel):
    type: Literal["eval"] = "eval"
    benchmarks: list[BenchmarkDef]
    passing_threshold: Optional[float] = Field(default=None, alias="passingThreshold")
    compare_to_base: bool = Field(default=True, alias="compareToBase")
    calibration_anchor: Optional[dict[str, Any]] = Field(default=None, alias="calibrationAnchor")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class PublishStage(BaseModel):
    type: Literal["publish"] = "publish"
    org: str
    repo_name_template: str = Field(default="{base}-{domain}-forged", alias="repoNameTemplate")
    include_alloy: bool = Field(default=True, alias="includeAlloy")
    card_from_benchmarks: bool = Field(default=True, alias="cardFromBenchmarks")
    tags: list[str] = Field(default_factory=list)
    private: bool = False
    card_hash: Optional[str] = Field(default=None, alias="cardHash")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ExpertActivationProfileStage(BaseModel):
    """§4.1.3.4 calibration-aware MoE expert importance profiling.
    Produces an importance JSON consumed by a downstream expert-prune stage."""
    type: Literal["expert-activation-profile"] = "expert-activation-profile"
    calibration_corpus: str = Field(alias="calibrationCorpus")
    metric: Literal["activation_count", "router_l2", "activation_magnitude"] = "activation_count"
    max_length: int = Field(default=2048, ge=128, alias="maxLength")
    device: Optional[str] = None
    importance_output: Optional[str] = Field(default=None, alias="importanceOutput")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class CompensationLoRAStage(BaseModel):
    """§4.1.3.3 KL-distillation-against-teacher compensation LoRA."""
    type: Literal["compensation-lora"] = "compensation-lora"
    teacher: str
    calibration_corpus: str = Field(alias="calibrationCorpus")
    loss_type: Literal["kl_logits", "mse_hidden", "both"] = Field(default="kl_logits", alias="lossType")
    kd_temperature: float = Field(default=2.0, ge=0.0, alias="kdTemperature")
    lora_rank: int = Field(default=16, ge=1, alias="loraRank")
    lora_alpha: int = Field(default=32, ge=1, alias="loraAlpha")
    target_modules: list[str] = Field(default_factory=list, alias="targetModules")
    steps: int = Field(default=500, ge=1)
    learning_rate: str = Field(default="1e-4", alias="learningRate")
    teacher_quant: Optional[Literal["8bit", "4bit", "fp16"]] = Field(default=None, alias="teacherQuant")
    student_quant: Optional[Literal["fp16", "4bit", "8bit"]] = Field(default=None, alias="studentQuant")
    merged_at_save: bool = Field(default=True, alias="mergedAtSave")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ExpertPruneStage(BaseModel):
    type: Literal["expert-prune"] = "expert-prune"
    # Either flat keep_experts (legacy) OR keep_experts_per_layer (post-§4.1.3.4)
    keep_experts: Optional[int] = Field(default=None, ge=1, alias="keepExperts")
    keep_experts_per_layer: Optional[int] = Field(default=None, ge=1, alias="keepExpertsPerLayer")
    original_experts_per_layer: Optional[int] = Field(default=None, alias="originalExpertsPerLayer")
    # Strategy/selection — both forms shipped on published alloys
    strategy: Optional[str] = None
    selection_strategy: Optional[str] = Field(default=None, alias="selectionStrategy")
    metric: Optional[str] = None
    metric_source: Optional[str] = Field(default=None, alias="metricSource")
    profile_dataset: Optional[str] = Field(default=None, alias="profileDataset")
    profile_steps: int = Field(default=100, ge=1, alias="profileSteps")
    importance_json: Optional[str] = Field(default=None, alias="importanceJson")
    expert_tensor_layout: Optional[Literal[
        "auto",
        "mlp-experts-unfused",
        "block_sparse_moe-unfused",
        "granite-moe-fused",
        "deepseek-routed-shared",
    ]] = Field(default="auto", alias="expertTensorLayout")
    calibration_corpus: Optional[str] = Field(default=None, alias="calibrationCorpus")
    per_layer_normalized: Optional[bool] = Field(default=None, alias="perLayerNormalized")
    prune_pct: Optional[float] = Field(default=None, alias="prunePct")
    experts_dropped: Optional[int] = Field(default=None, alias="expertsDropped")
    experts_renamed: Optional[int] = Field(default=None, alias="expertsRenamed")
    router_sliced_layers: Optional[int] = Field(default=None, alias="routerSlicedLayers")
    implementation: Optional[str] = None
    rationale: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ContextExtendStage(BaseModel):
    type: Literal["context-extend"] = "context-extend"
    target_length: int = Field(ge=1024, alias="targetLength")
    method: Literal["yarn", "ntk", "linear", "dynamic-ntk"]
    training_dataset: Optional[str] = Field(default=None, alias="trainingDataset")
    training_steps: Optional[int] = Field(default=None, alias="trainingSteps")

    model_config = {"populate_by_name": True, "extra": "allow"}


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

    model_config = {"populate_by_name": True, "extra": "allow"}


class BenchmarkAcceptance(BaseModel):
    """Acceptance criterion for one benchmark.

    `min` is the absolute pass@1 floor (0..1) the forged model must clear.
    `anchorDelta` is the §4.1.3.4 discipline gate: the forged score must
    be within Δ of the base anchor measured in the SAME eval pipeline.
    Negative means forged ≥ anchor + delta (i.e. anchorDelta=-3 means the
    forged score is allowed to drop by at most 3 percentage points
    relative to the unmodified base anchor).
    """
    min: float = Field(..., ge=0.0, le=1.0)
    anchor_delta: Optional[float] = Field(default=None, alias="anchorDelta")
    anchor_benchmark: Optional[str] = Field(default=None, alias="anchorBenchmark")
    notes: Optional[str] = None
    model_config = {"populate_by_name": True, "extra": "allow"}


class AcceptanceHardware(BaseModel):
    """Hardware acceptance criteria — must fit on the declared tier."""
    max_vram_gb: Optional[float] = Field(default=None, alias="maxVramGb")
    device_tier: Optional[str] = Field(default=None, alias="deviceTier")
    model_config = {"populate_by_name": True, "extra": "allow"}


class AcceptanceIntegrity(BaseModel):
    """Integrity acceptance criteria — chain-of-custody requirements."""
    model_hash_required: bool = Field(default=False, alias="modelHashRequired")
    samples_path_required: bool = Field(default=False, alias="samplesPathRequired")
    model_config = {"populate_by_name": True, "extra": "allow"}


class AcceptanceCriteria(BaseModel):
    """The part spec — gate the forged model must clear before shipping.

    Lives on the alloy itself (the alloy IS the part spec). Sentinel-ai
    forges and assays; it never reads acceptanceCriteria. Continuum (the
    shipping department) reads BOTH the assayed scores written into the
    finished/ manifest AND the alloy's acceptanceCriteria, and decides
    ship vs rework. Same alloy → same gate verdict on any forge run by
    anyone, anywhere — the spec is portable.
    """
    benchmarks: dict[str, BenchmarkAcceptance] = Field(default_factory=dict)
    hardware: Optional[AcceptanceHardware] = None
    integrity: Optional[AcceptanceIntegrity] = None
    notes: Optional[str] = None
    model_config = {"populate_by_name": True, "extra": "allow"}


class AlloyHardware(BaseModel):
    min_vram_gb: Optional[float] = Field(default=None, alias="minVramGb")
    recommended_vram_gb: Optional[float] = Field(default=None, alias="recommendedVramGb")
    estimated_duration_minutes: Optional[float] = Field(default=None, alias="estimatedDurationMinutes")
    supports_cpu: bool = Field(default=False, alias="supportsCPU")
    tested_on: list[str] = Field(default_factory=list, alias="testedOn")
    # Device target list — every published continuum-ai/* alloy carries this
    # field at hardware.deviceTargets. Caught by the regression round-trip
    # test 2026-04-08: pydantic was silently dropping it because the schema
    # didn't have it.
    device_targets: list[str] = Field(default_factory=list, alias="deviceTargets")

    model_config = {"populate_by_name": True, "extra": "allow"}


# ── Bookend stage types ───────────────────────────────────────────────────── ───────────────────────────────────────────────


class SourceConfigStage(BaseModel):
    """Front bookend: declare target capabilities."""
    type: Literal["source-config"] = "source-config"
    context_length: Optional[int] = Field(default=None, alias="contextLength")
    input_modalities: list[str] = Field(default_factory=list, alias="inputModalities")
    tokenizer: Optional[str] = None
    target_batch_size: Optional[int] = Field(default=None, alias="targetBatchSize")
    target_devices: list[str] = Field(default_factory=list, alias="targetDevices")

    model_config = {"populate_by_name": True, "extra": "allow"}


class PackageStage(BaseModel):
    """End bookend: device-specific packaging."""
    type: Literal["package"] = "package"
    format: str
    runtime: Optional[str] = None
    optimization: str = "balanced"
    validate_on: list[str] = Field(default_factory=list, alias="validateOn")
    include_tokenizer: bool = Field(default=True, alias="includeTokenizer")

    model_config = {"populate_by_name": True, "extra": "allow"}


class DeployStage(BaseModel):
    """End bookend: deploy to grid node."""
    type: Literal["deploy"] = "deploy"
    target: str
    health_check: bool = Field(default=True, alias="healthCheck")
    warmup: bool = Field(default=True)
    max_concurrency: Optional[int] = Field(default=None, alias="maxConcurrency")
    auto_scale: Optional[bool] = Field(default=None, alias="autoScale")

    model_config = {"populate_by_name": True, "extra": "allow"}


# ── Search Strategy (the model compiler's optimizer) ──────────────────────────


class SearchStrategy(BaseModel):
    """How the forge searches for the optimal configuration.

    The search finds the best (prune_config, quant_level) that:
    1. Fits all target devices (VRAM constraint)
    2. Passes all benchmark gates (quality constraint)
    3. Maximizes quality within constraints

    Phases: size_filter (free) → estimate (free) → quick_eval (2min) → full_eval (40min).
    Only the winner gets the expensive evaluation.
    """
    method: Literal[
        "manual",       # user specifies exact config, no search
        "binary",       # binary search on quality/size tradeoff (fast, monotonic assumption)
        "ransac",       # random sampling + consensus (handles noisy quality landscape)
        "bayesian",     # Gaussian process surrogate (fewest evaluations to converge)
        "exhaustive",   # try everything (slow, guaranteed optimal)
        "adaptive",     # per-layer expert counts from activation profile
    ] = "manual"
    quick_eval_chunks: int = Field(default=10, ge=1, le=50, alias="quickEvalChunks")
    max_candidates: int = Field(default=5, ge=1, le=20, alias="maxCandidates")
    confidence_threshold: float = Field(default=0.95, ge=0.5, le=0.999, alias="confidenceThreshold")
    try_compensation_lora: bool = Field(default=False, alias="tryCompensationLora")
    lora_steps_if_needed: int = Field(default=500, ge=100, le=5000, alias="loraStepsIfNeeded")
    coverage_threshold: float = Field(default=0.85, ge=0.5, le=0.99, alias="coverageThreshold")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


# ── Many-Worlds Stage (cross-model substrate) ────────────────────────────────


class ManyWorldsSubstrateStage(BaseModel):
    """§V.6.7 Many-Worlds substrate training.

    Train a shared continuous Gaussian coordinate space that multiple
    frozen pretrained models can project into and read from. The substrate
    is the linker's symbol table for cross-family expert grafting.
    """
    type: Literal["many-worlds-substrate"] = "many-worlds-substrate"
    substrate_dim: int = Field(default=256, ge=64, le=2048, alias="substrateDim")
    num_gaussians: int = Field(default=128, ge=16, le=1024, alias="numGaussians")
    source_models: list[str] = Field(alias="sourceModels")
    calibration_corpus: str = Field(alias="calibrationCorpus")
    training_steps: int = Field(default=1000, ge=100, le=50000, alias="trainingSteps")
    learning_rate: str = Field(default="1e-4", alias="learningRate")
    loss_type: Literal["contrastive", "round_trip", "both"] = Field(default="both", alias="lossType")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ManyWorldsAdapterStage(BaseModel):
    """Per-model Project/Read adapter training against a fixed substrate."""
    type: Literal["many-worlds-adapter"] = "many-worlds-adapter"
    target_model: str = Field(alias="targetModel")
    substrate_path: str = Field(alias="substratePath")
    adapter_rank: int = Field(default=64, ge=8, le=512, alias="adapterRank")
    insert_layer: Optional[int] = Field(default=None, alias="insertLayer")
    training_steps: int = Field(default=500, ge=100, le=10000, alias="trainingSteps")
    learning_rate: str = Field(default="1e-4", alias="learningRate")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class CVIngestStage(BaseModel):
    """Computer vision dataset ingestion for open-eyes pipeline evaluation."""
    type: Literal["cv-ingest"] = "cv-ingest"
    dataset: str
    subset: Optional[str] = None
    frame_format: str = Field(default="jpeg-sequence", alias="frameFormat")
    max_sequences: Optional[int] = Field(default=None, alias="maxSequences")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class CVEvalStage(BaseModel):
    """Computer vision pipeline evaluation (open-eyes triage, detection, tracking)."""
    type: Literal["cv-eval"] = "cv-eval"
    pipeline: str
    pipeline_config: dict = Field(default_factory=dict, alias="pipelineConfig")
    benchmarks: list[BenchmarkDef] = Field(default_factory=list)
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class TeamSearchStage(BaseModel):
    """Many-Worlds team search — find optimal model population via divergence analysis."""
    type: Literal["team-search"] = "team-search"
    search_pool: str = Field(alias="searchPool")
    benchmark: str
    num_problems: int = Field(default=50, alias="numProblems")
    candidates_evaluated: Optional[int] = Field(default=None, alias="candidatesEvaluated")
    selected_team: Optional[list[str]] = Field(default=None, alias="selectedTeam")
    divergence_score: Optional[float] = Field(default=None, alias="divergenceScore")
    complementary_problems: Optional[int] = Field(default=None, alias="complementaryProblems")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ManyWorldsEnsembleStage(BaseModel):
    """Many-Worlds logit ensemble — blend predictions from specialist models.

    No training required. Each specialist's top-K confident predictions
    boost the target model's logits at inference time. The blend can
    only boost tokens, never suppress — result is always ≥ baseline.
    """
    type: Literal["many-worlds-ensemble"] = "many-worlds-ensemble"
    method: Literal["logit-blend", "soft-prompt", "cross-attention"] = "logit-blend"
    target_model: str = Field(alias="targetModel")
    specialists: list[str]
    alpha: float = Field(default=0.2, ge=0.0, le=1.0)
    top_k: int = Field(default=20, ge=1, alias="topK")
    blend_strategy: Literal["specialist-top-k-boost", "full-distribution", "weighted-average"] = Field(
        default="specialist-top-k-boost", alias="blendStrategy")
    vram_gb: Optional[float] = Field(default=None, alias="vramGb")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class GateProfileStage(BaseModel):
    """Profile which specialists contribute on which input types.

    The gate profiling data drives population-level pruning: models that
    never contribute get removed, models that contribute selectively get
    quantized for their non-specialty tokens.
    """
    type: Literal["gate-profile"] = "gate-profile"
    benchmark: str
    num_problems: int = Field(default=100, alias="numProblems")
    per_specialist_contribution: Optional[dict[str, float]] = Field(
        default=None, alias="perSpecialistContribution")
    export_path: Optional[str] = Field(default=None, alias="exportPath")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class PopulationPruneStage(BaseModel):
    """Remove specialists that don't contribute enough to justify their VRAM cost."""
    type: Literal["population-prune"] = "population-prune"
    min_contribution: float = Field(default=0.05, alias="minContribution")
    removed_models: Optional[list[str]] = Field(default=None, alias="removedModels")
    vram_saved_gb: Optional[float] = Field(default=None, alias="vramSavedGb")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


# Discriminated union for stages — must be after ALL stage class definitions
AlloyStage = Annotated[
    Union[
        SourceConfigStage, PruneStage, TrainStage, LoRAStage, CompactStage,
        QuantStage, PackageStage, EvalStage, PublishStage, DeployStage,
        ExpertPruneStage, ExpertActivationProfileStage, CompensationLoRAStage,
        ContextExtendStage, ModalityStage,
        ManyWorldsSubstrateStage, ManyWorldsAdapterStage,
        ManyWorldsEnsembleStage, TeamSearchStage, GateProfileStage, PopulationPruneStage,
        CVIngestStage, CVEvalStage,
    ],
    Field(discriminator="type"),
]


# ── Target (delta from source) ──────────────────────────────────────────────


class AlloyTarget(BaseModel):
    """What the model should BECOME. Only set fields you want to CHANGE."""
    context_length: Optional[int] = Field(default=None, alias="contextLength")
    modalities: Optional[list[str]] = None
    domain: Optional[str] = None
    prune_ratio: Optional[float] = Field(default=None, alias="pruneRatio")
    experts: Optional[int] = None
    output_formats: Optional[list[str]] = Field(default=None, alias="outputFormats")
    quant_types: Optional[list[str]] = Field(default=None, alias="quantTypes")
    target_devices: Optional[list[str]] = Field(default=None, alias="targetDevices")
    deploy_to: Optional[str] = Field(default=None, alias="deployTo")
    benchmarks: Optional[list[str]] = None
    publish: Optional[bool] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


# ── Receipt (proof of delivery) ─────────────────────────────────────────────


class Publication(BaseModel):
    """A single publication record."""
    target: str
    url: str
    published_at: str = Field(alias="publishedAt")
    downloads: Optional[int] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AlloyReceipt(BaseModel):
    """Proof of delivery — where it was published, verification URLs, QR."""
    publications: list[Publication] = Field(default_factory=list)
    verify_url: Optional[str] = Field(default=None, alias="verifyUrl")
    alloy_hash: Optional[str] = Field(default=None, alias="alloyHash")
    card_hash: Optional[str] = Field(default=None, alias="cardHash")
    issued_at: str = Field(alias="issuedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}


# ── Hardware & Outputs ──────────────────────────────────────────────────────


class OutputArtifact(BaseModel):
    type: str
    description: str = ""


class AlloyOutputs(BaseModel):
    produces: list[OutputArtifact] = Field(default_factory=list)


class CalibrationCorpusRef(BaseModel):
    """§4.1.3.4.1 calibration corpus discipline gate — declared at alloy root."""
    id: str
    name: Optional[str] = None
    path: str
    sha256: Optional[str] = None
    examples: Optional[int] = None
    tokens: Optional[int] = None
    distribution_summary: Optional[str] = Field(default=None, alias="distributionSummary")

    model_config = {"populate_by_name": True, "extra": "allow"}


class PriorMetricBaseline(BaseModel):
    """§4.1.3.4 negative-baseline empirical control. Preserves superseded
    forge attempts as falsifiability anchors in the published artifact."""
    id: Optional[str] = None
    name: Optional[str] = None
    metric: Optional[Union[str, dict[str, Any]]] = None
    evaluation: Optional[dict[str, Any]] = None
    prune: Optional[dict[str, Any]] = None
    results: Optional[dict[str, Any]] = None
    samples_path: Optional[str] = Field(default=None, alias="samplesPath")
    outcome: Optional[Literal["shipped", "negative_baseline", "superseded"]] = None
    superseded_by: Optional[str] = Field(default=None, alias="supersededBy")
    methodology_anchor: Optional[str] = Field(default=None, alias="methodologyAnchor")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ForgeAlloy(BaseModel):
    name: str
    version: str
    description: str = ""
    user_summary: Optional[str] = Field(default=None, alias="userSummary")
    author: str = ""
    tags: list[str] = Field(default_factory=list)
    license: str = "apache-2.0"

    source: AlloySource
    target: Optional[AlloyTarget] = None
    stages: list[AlloyStage] = Field(default_factory=list)
    cycles: int = Field(default=1, ge=1)

    hardware: Optional[AlloyHardware] = None
    outputs: Optional[AlloyOutputs] = None
    search: Optional[SearchStrategy] = None

    results: Optional[AlloyResults] = None
    receipt: Optional[AlloyReceipt] = None

    source_alloy_id: Optional[str] = Field(default=None, alias="sourceAlloyId")
    forged_model_ids: Optional[list[str]] = Field(default=None, alias="forgedModelIds")

    # Methodology / prose fields shipped on continuum-ai/* artifacts
    limitations: list[str] = Field(default_factory=list)
    methodology_paper_url: Optional[str] = Field(default=None, alias="methodologyPaperUrl")
    calibration_corpora: list[CalibrationCorpusRef] = Field(default_factory=list, alias="calibrationCorpora")
    prior_metric_baselines: list[PriorMetricBaseline] = Field(default_factory=list, alias="priorMetricBaselines")

    # The part spec — gate the forged model must clear before continuum
    # ships it. Optional (backwards compat with every existing alloy).
    # Sentinel never reads this; continuum's shipping flow does.
    acceptance_criteria: Optional[AcceptanceCriteria] = Field(default=None, alias="acceptanceCriteria")

    model_config = {"populate_by_name": True, "extra": "allow"}

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
    def is_signed(self) -> bool:
        """Check if results have a signed integrity attestation."""
        return (
            self.results is not None
            and self.results.integrity is not None
            and self.results.integrity.signature is not None
        )

    @property
    def trust_level(self) -> Optional[str]:
        """Get the trust level of the attestation."""
        if self.results and self.results.integrity:
            return self.results.integrity.trust_level
        return None
