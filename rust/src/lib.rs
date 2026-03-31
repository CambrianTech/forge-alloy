//! # ForgeAlloy
//!
//! Portable pipeline format for model forging.
//! Define, share, and execute model transformation pipelines across any hardware.
//!
//! ```rust,no_run
//! use forge_alloy::{ForgeAlloy, AlloyStage};
//!
//! let json = std::fs::read_to_string("example.alloy.json").unwrap();
//! let alloy: ForgeAlloy = serde_json::from_str(&json).unwrap();
//!
//! for stage in &alloy.stages {
//!     match stage {
//!         AlloyStage::Prune(p) => println!("Pruning {}%", p.level * 100.0),
//!         AlloyStage::Train(t) => println!("Training {} steps", t.steps),
//!         _ => {}
//!     }
//! }
//! ```

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[cfg(feature = "typescript")]
use ts_rs::TS;

// ── Root Entity ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct ForgeAlloy {
    pub name: String,
    pub version: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub author: String,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default = "default_license")]
    pub license: String,

    pub source: AlloySource,

    /// Target capabilities — what the model should BECOME after forging.
    /// The delta between source (introspected) and target (desired) defines the work.
    /// Stages can be auto-derived from this delta or manually specified.
    /// If target is None, stages must be explicitly provided (legacy/manual mode).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<AlloyTarget>,

    /// Pipeline stages to execute. Either manually specified or derived from source→target delta.
    pub stages: Vec<AlloyStage>,
    #[serde(default = "default_cycles")]
    pub cycles: u32,

    #[serde(default)]
    pub hardware: Option<AlloyHardware>,
    #[serde(default)]
    pub outputs: Option<AlloyOutputs>,

    /// Populated after execution — benchmark scores, hardware verification, samples
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub results: Option<AlloyResults>,

    /// Populated after delivery — where it was published, verification URLs, QR
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub receipt: Option<AlloyReceipt>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_alloy_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub forged_model_ids: Option<Vec<String>>,
}

fn default_license() -> String { "apache-2.0".to_string() }
fn default_cycles() -> u32 { 1 }

// ── Source ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct AlloySource {
    pub base_model: String,
    pub architecture: String,
    #[serde(default)]
    pub revision: Option<String>,
    #[serde(default)]
    pub is_moe: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub total_experts: Option<u32>,
}

// ── Target (desired state — the delta from source defines the work) ────────

/// What the model should BECOME after forging.
/// Each field is optional — only set the fields you want to CHANGE.
/// Unset fields mean "keep as-is" (no work needed for that capability).
/// The system compares source (introspected) vs target (desired) to derive stages.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct AlloyTarget {
    /// Desired context window length (tokens). Triggers context-extend if > source.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub context_length: Option<u32>,

    /// Desired input modalities. Adding new ones triggers modality stages.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub modalities: Option<Vec<String>>,

    /// Target domain specialization (code, reasoning, chat, science). Triggers train stage.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub domain: Option<String>,

    /// Target parameter reduction (0.0-0.9). Triggers prune + defrag stages.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub prune_ratio: Option<f32>,

    /// Target expert count for MoE models. Triggers expert-prune if < source.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub experts: Option<u32>,

    /// Target output formats (gguf, mlx, onnx, coreml). Triggers quant/package stages.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub output_formats: Option<Vec<String>>,

    /// Target quantization types per format (e.g. ["Q4_K_M", "Q8_0"]).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub quant_types: Option<Vec<String>>,

    /// Target devices this model should run on. Drives quant/package decisions.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target_devices: Option<Vec<String>>,

    /// Target deployment node. Triggers deploy stage.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub deploy_to: Option<String>,

    /// Benchmarks to run. Triggers eval stage.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub benchmarks: Option<Vec<String>>,

    /// Whether to publish to HuggingFace. Triggers publish stage.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub publish: Option<bool>,
}

// ── Results (populated after execution) ────────────────────────────────────

/// Complete results from executing an alloy pipeline.
/// This section is empty in a recipe alloy and populated after forging.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct AlloyResults {
    /// When the forge completed
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub completed_at: Option<String>,

    /// Total forge wall-clock time in minutes
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub duration_minutes: Option<f32>,

    /// Perplexity before forging (baseline)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub baseline_perplexity: Option<f64>,

    /// Perplexity after forging
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub final_perplexity: Option<f64>,

    /// Improvement percentage (positive = better)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub improvement_pct: Option<f64>,

    /// Model size after forging in GB
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub final_size_gb: Option<f64>,

    /// Number of parameters after forging
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub final_params: Option<String>,

    /// Benchmark results — extensible, each benchmark defines its own metrics
    #[serde(default)]
    pub benchmarks: Vec<BenchmarkResult>,

    /// Verified hardware performance profiles for model card device grid
    #[serde(default)]
    pub hardware_verified: Vec<HardwareProfile>,

    /// Generation samples — raw model output, no cherry-picking
    #[serde(default)]
    pub samples: Vec<GenerationSample>,

    /// Cryptographic integrity attestation (optional, for verified benchmarks)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub integrity: Option<IntegrityAttestation>,
}

/// A single benchmark result. Metrics are open-ended — each benchmark
/// reports whatever it wants (passing, total, accuracy, score, etc.)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct BenchmarkResult {
    /// Benchmark name (e.g. "humaneval", "mmlu-pro", "imo-proofbench-advanced")
    pub name: String,

    /// Optional subset (e.g. "mmlu-pro" subset of MMLU)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub subset: Option<String>,

    /// Open metric bag — any key-value pairs the benchmark produces.
    /// Examples:
    ///   HumanEval: { "passing": 63, "total": 85, "score": 74.1 }
    ///   MMLU: { "accuracy": 68.5, "nShot": 5 }
    ///   IMO-ProofBench: { "proofScore": 42.0, "difficulty": "advanced" }
    ///   Perplexity: { "baseline": 3.04, "final": 2.31, "improvement": 24.0 }
    #[cfg_attr(feature = "typescript", ts(type = "Record<string, number | string | boolean>"))]
    pub metrics: HashMap<String, serde_json::Value>,

    /// Whether this result was submitted to a public leaderboard
    #[serde(default)]
    pub submitted_to_leaderboard: bool,

    /// Per-benchmark integrity hash (optional)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub result_hash: Option<String>,
}

/// Verified performance on a specific device — used to generate model card device grid
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct HardwareProfile {
    /// Device name (e.g. "MacBook Air 8GB", "RTX 5090", "iPhone 17")
    pub device: String,

    /// Format used (e.g. "Q4_K_M", "fp16", "mlx-4bit")
    pub format: String,

    /// Model file size in GB for this format
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub size_gb: Option<f64>,

    /// Inference speed in tokens/second
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tokens_per_sec: Option<f64>,

    /// VRAM/RAM usage in GB during inference
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub memory_usage_gb: Option<f64>,

    /// Whether this was actually tested (true) or estimated (false)
    #[serde(default)]
    pub verified: bool,
}

/// Raw model output sample — no cherry-picking, no post-processing
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct GenerationSample {
    /// Label for this sample (e.g. "Code Generation", "Merge Sort")
    pub label: String,

    /// The input prompt
    pub prompt: String,

    /// The model's output
    pub completion: String,

    /// Optional: what the base model produced for comparison
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub baseline_completion: Option<String>,
}

/// Trust tier — how much should you trust this attestation?
/// Maps to WebAuthn attestation types.
///
/// IMPORTANT: Self-attested only prevents accidental corruption, NOT adversarial
/// modification. A compromised runner can fake self-attestation. Only `enclave`
/// tier (TEE execution) provides actual tamper-proof guarantees.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "kebab-case")]
pub enum TrustLevel {
    /// Signer vouches for itself. Prevents accidental corruption only.
    /// A compromised runner can forge this. Honest about its limitations.
    SelfAttested,
    /// Third-party verified the environment (audited runner, certificate chain).
    /// Requires certificate_chain in AttestationSignature.
    Verified,
    /// TEE execution (SGX, Nitro Enclaves, TrustZone). Hardware-bound proof.
    /// The ONLY tier that prevents input-output binding attacks.
    Enclave,
}

/// Cryptographic attestation for verified benchmark execution.
/// Modeled after FIDO2/WebAuthn attestation: prove WHAT code ran,
/// on WHAT data, in WHAT environment, and sign the whole chain.
///
/// Canonicalization: signed payload MUST use RFC 8785 (JSON Canonicalization
/// Scheme / JCS) — deterministic key ordering, number formatting, and Unicode
/// normalization. Without this, cross-language verification breaks.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct IntegrityAttestation {
    /// Trust tier — how much should you trust this attestation?
    pub trust_level: TrustLevel,

    /// The code that produced these results
    pub code: CodeAttestation,

    /// SHA-256 hash of the FULL model weights (not partial — every byte).
    /// Partial hashing is trivially bypassed by swapping tensor data after headers.
    pub model_hash: String,

    /// SHA-256 hash of the alloy pipeline definition (stages + source, excluding results).
    /// REQUIRED when signature is present — proves what pipeline was executed.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub alloy_hash: Option<String>,

    /// Hashes of benchmark datasets used — proves eval wasn't run on modified data.
    /// Hash spec: sort filenames lexicographically, hash each file fully, combine via Merkle tree.
    /// Must cover exactly the subset used, not the full dataset.
    #[serde(default)]
    pub datasets: Vec<DatasetAttestation>,

    /// Verifier-provided nonce for replay prevention (like WebAuthn challenge).
    /// Required for marketplace transactions — the marketplace issues this before forge begins.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub nonce: Option<String>,

    /// Audience binding — canonical origin URI of the intended verifier (e.g. "https://marketplace.forge-alloy.dev").
    /// Verifiers compare against their own origin — exact string match. Prevents cross-marketplace replay.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub audience: Option<String>,

    /// Cryptographic signature over the attestation payload (RFC 8785 JCS canonical form)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub signature: Option<AttestationSignature>,

    /// External trust anchor — optional immutable record of this attestation.
    /// Blockchain tx, Merkle root, RFC 3161 timestamp, or any external proof
    /// that this attestation existed at a specific time and hasn't been backdated.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub anchor: Option<TrustAnchor>,

    /// Third-party adapter attestations — independent certifications from approved adapters.
    /// Each adapter (eval harness, safety auditor, hardware certifier, etc.) signs its own
    /// result with its own key. The chain becomes a stack of independent proofs.
    /// Like UL certification — each adapter is an independent certifier with its own passkey.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub certifications: Vec<AdapterAttestation>,

    /// ISO 8601 timestamp of attestation
    pub attested_at: String,
}

/// External trust anchor — immutable proof that an attestation existed at a point in time.
/// The signature proves integrity. The anchor proves existence. Together they prevent
/// both tampering AND backdating.
///
/// Use cases:
/// - Blockchain: publish attestation hash to an immutable ledger
/// - Merkle tree: batch attestations into a root published periodically
/// - RFC 3161: traditional timestamping authority
/// - IPFS: content-addressed storage (hash = address)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct TrustAnchor {
    /// Anchor type
    pub anchor_type: AnchorType,

    /// The hash or ID that was anchored (typically SHA-256 of the full attestation)
    pub anchored_hash: String,

    /// Where the anchor lives (tx hash, IPFS CID, TSA URL, Merkle root location)
    pub location: String,

    /// When the anchor was created
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub anchored_at: Option<String>,

    /// Chain/network identifier (e.g. "ethereum:mainnet", "solana:mainnet")
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub network: Option<String>,
}

/// Type of external trust anchor
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "kebab-case")]
pub enum AnchorType {
    /// Blockchain transaction containing the attestation hash
    Blockchain,
    /// Merkle root published to a known location (batched attestations)
    MerkleRoot,
    /// RFC 3161 Timestamp Authority response
    Rfc3161,
    /// IPFS content-addressed storage
    Ipfs,
    /// Custom anchor (describe in location field)
    Custom,
}

/// Third-party adapter attestation — an independent certification for one chain element.
/// Each approved adapter has its own keypair and signs its own results.
/// Like UL certification: the adapter is an independent authority that tested one aspect
/// of the model and vouches for it with its own passkey.
///
/// Examples:
/// - HumanEval adapter: runs eval, signs scores with its key
/// - UL safety adapter: runs safety audit, certifies compliance with its key
/// - NVIDIA hardware adapter: runs perf test, signs results with GPU TEE key
/// - HuggingFace adapter: verifies publication, signs receipt with HF key
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct AdapterAttestation {
    /// Adapter identifier (e.g. "forge-alloy/humaneval", "ul/safety-audit", "nvidia/perf-cert")
    pub adapter: String,

    /// Adapter version (semver)
    pub version: String,

    /// What this adapter certifies (e.g. "benchmark:humaneval", "safety:toxicity", "hardware:inference")
    pub domain: String,

    /// The result or finding — adapter-specific, open-ended metrics
    #[serde(default)]
    pub result: HashMap<String, serde_json::Value>,

    /// SHA-256 of the adapter binary or entry script (same pattern as CodeAttestation.binaryHash)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub adapter_hash: Option<String>,

    /// Cryptographic signature from the adapter's own key — independent of the forge runner's signature.
    /// Payload: JCS-canonical { adapter, version, domain, result, nonce, attestedAt }
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub signature: Option<AttestationSignature>,

    /// Nonce provided by the API for this specific adapter run (prevents replay/cherry-picking)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub nonce: Option<String>,

    /// Source repo for the adapter (GitHub URL — auditable)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_repo: Option<String>,

    /// Git commit of the adapter at execution time
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub commit: Option<String>,

    /// ISO 8601 timestamp of this certification
    pub attested_at: String,
}

/// Attestation of the code that produced results.
/// Like WebAuthn authenticator attestation — proves the forge runner is genuine.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct CodeAttestation {
    /// Runner identifier (e.g. "forge-alloy/forge-runner", "sentinel-ai/forge_model")
    pub runner: String,

    /// Runner version (semver)
    pub version: String,

    /// SHA-256 of the runner binary or entry script
    pub binary_hash: String,

    /// SHA-256 of the source repository at build time
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_hash: Option<String>,

    /// Git commit hash of the runner source
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub commit: Option<String>,

    /// Execution environment description
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub environment: Option<String>,

    /// SHA-256 of the container image or environment (for reproducibility)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub environment_hash: Option<String>,
}

/// Attestation of a benchmark dataset — proves eval used unmodified data.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct DatasetAttestation {
    /// Dataset name (e.g. "humaneval", "mmlu-pro", "imo-proofbench-advanced")
    pub name: String,

    /// Dataset version or commit hash
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,

    /// SHA-256 of the dataset files
    pub hash: String,

    /// Source URL or repository
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source: Option<String>,
}

/// Signing algorithm for attestation signatures.
/// Extensible to post-quantum algorithms when standards mature.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
pub enum SigningAlgorithm {
    /// ECDSA with P-256 and SHA-256 (WebAuthn default, universal hardware support)
    ES256,
    /// ECDSA with P-384 and SHA-384 (higher security margin)
    ES384,
    /// EdDSA with Ed25519 (fast, but less hardware attestation support)
    EdDSA,
    /// CRYSTALS-Dilithium (NIST PQC standard, FIPS 204 / ML-DSA)
    /// Post-quantum lattice-based signatures. Add when libraries stabilize.
    #[serde(rename = "ML-DSA-65")]
    MlDsa65,
    /// CRYSTALS-Dilithium higher security level
    #[serde(rename = "ML-DSA-87")]
    MlDsa87,
    /// SPHINCS+ (NIST PQC standard, FIPS 205 / SLH-DSA)
    /// Hash-based post-quantum signatures. Stateless, conservative choice.
    #[serde(rename = "SLH-DSA-128s")]
    SlhDsa128s,
}

/// ECDSA signature over the attestation payload.
/// Payload MUST be canonicalized via RFC 8785 (JCS) before signing.
///
/// NOTE on passkeys: WebAuthn credentials sign `clientDataJSON` (which includes
/// a relying party challenge), NOT arbitrary payloads. To use passkeys for
/// forge attestation, the attestation hash must be embedded in the WebAuthn
/// challenge field, or the raw Secure Enclave key must be accessed outside the
/// WebAuthn ceremony (which standard passkeys don't allow — the key is bound
/// to the RP ID). Phase 2 needs a signing service that bridges this gap.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct AttestationSignature {
    /// Signing algorithm
    pub algorithm: SigningAlgorithm,

    /// Base64url-encoded public key of the signer.
    /// CRITICAL: verifiers MUST fetch the key from the registry and compare,
    /// NOT trust this embedded key directly. A naive verifier using only this
    /// field defeats the entire registry.
    pub public_key: String,

    /// Base64url-encoded signature over SHA-256(JCS-canonicalized attestation payload)
    pub value: String,

    /// Key ID in the registry (for lookup and revocation checking)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub key_id: Option<String>,

    /// Credential ID — for passkey-based signing (see NOTE above on limitations)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub credential_id: Option<String>,

    /// Certificate chain for CA-attested signers (PEM-encoded, leaf first)
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub certificate_chain: Vec<String>,

    /// Key registry URL where this public key can be verified and revocation checked.
    /// Registry MUST support: key lookup, revocation status, key rotation (supersededBy).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub key_registry: Option<String>,
}

// ── Stages (discriminated union via serde tag) ──────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum AlloyStage {
    // ── Input stages (front of pipeline) ─────────────────
    /// Declare source model capabilities and configuration
    SourceConfig(SourceConfigStage),
    /// Add vision/audio/video encoder to the model
    Modality(ModalityStage),
    /// Extend context window via RoPE rescaling
    ContextExtend(ContextExtendStage),

    // ── Transform stages (middle of pipeline) ────────────
    /// Head pruning by entropy, magnitude, gradient
    Prune(PruneStage),
    /// Recovery/fine-tuning with full training config
    Train(TrainStage),
    /// LoRA adapter training
    Lora(LoRAStage),
    /// Plasticity-based mixed-precision compaction
    Compact(CompactStage),
    /// MoE expert pruning by activation profile
    ExpertPrune(ExpertPruneStage),

    // ── Output stages (end of pipeline) ──────────────────
    /// Quantize to GGUF, MLX, ONNX, safetensors
    Quant(QuantStage),
    /// Package for specific device targets (CoreML, TensorRT, etc.)
    Package(PackageStage),
    /// Run benchmarks (HumanEval, MMLU, custom)
    Eval(EvalStage),
    /// Push to HuggingFace or other registry
    Publish(PublishStage),
    /// Deploy to grid node for serving
    Deploy(DeployStage),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct PruneStage {
    pub strategy: String,
    pub level: f32,
    #[serde(default = "default_min_heads")]
    pub min_heads_per_layer: u32,
    #[serde(default = "default_min_kv_heads")]
    pub min_kv_heads_per_layer: u32,
    #[serde(default = "default_analysis_steps")]
    pub analysis_steps: u32,
}

fn default_min_heads() -> u32 { 4 }
fn default_min_kv_heads() -> u32 { 2 }
fn default_analysis_steps() -> u32 { 200 }

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct TrainStage {
    pub domain: String,
    #[serde(default)]
    pub dataset: Option<String>,
    pub steps: u32,
    pub learning_rate: String,
    #[serde(default = "default_batch_size")]
    pub batch_size: u32,
    #[serde(default = "default_one")]
    pub gradient_accumulation: u32,
    #[serde(default = "default_scheduler")]
    pub scheduler: String,
    #[serde(default = "default_warmup")]
    pub warmup_ratio: f32,
    #[serde(default = "default_weight_decay")]
    pub weight_decay: f32,
    #[serde(default = "default_grad_norm")]
    pub max_gradient_norm: f32,
    #[serde(default = "default_precision")]
    pub precision: String,
    #[serde(default = "default_seq_len")]
    pub sequence_length: u32,
    #[serde(default)]
    pub optimizations: Vec<String>,
}

fn default_batch_size() -> u32 { 4 }
fn default_one() -> u32 { 1 }
fn default_scheduler() -> String { "cosine".to_string() }
fn default_warmup() -> f32 { 0.03 }
fn default_weight_decay() -> f32 { 0.01 }
fn default_grad_norm() -> f32 { 1.0 }
fn default_precision() -> String { "bf16".to_string() }
fn default_seq_len() -> u32 { 2048 }

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct LoRAStage {
    #[serde(default = "default_rank")]
    pub rank: u32,
    #[serde(default)]
    pub alpha: Option<u32>,
    #[serde(default = "default_dropout")]
    pub dropout: f32,
    #[serde(default = "default_target_modules")]
    pub target_modules: Vec<String>,
    #[serde(default = "default_true")]
    pub quantize: bool,
    #[serde(default = "default_quant_bits")]
    pub quantize_bits: u32,
    #[serde(default)]
    pub dataset: Option<String>,
    #[serde(default = "default_epochs")]
    pub epochs: u32,
    #[serde(default = "default_lora_lr")]
    pub learning_rate: String,
    #[serde(default = "default_batch_size")]
    pub batch_size: u32,
    #[serde(default)]
    pub merge_after: bool,
}

fn default_rank() -> u32 { 32 }
fn default_dropout() -> f32 { 0.05 }
fn default_target_modules() -> Vec<String> {
    vec!["q_proj".into(), "k_proj".into(), "v_proj".into(), "o_proj".into()]
}
fn default_true() -> bool { true }
fn default_quant_bits() -> u32 { 4 }
fn default_epochs() -> u32 { 3 }
fn default_lora_lr() -> String { "1e-4".to_string() }

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct CompactStage {
    #[serde(default = "default_dead")]
    pub dead_threshold: f32,
    #[serde(default = "default_dormant")]
    pub dormant_threshold: f32,
    #[serde(default = "default_low")]
    pub low_threshold: f32,
    #[serde(default = "default_medium")]
    pub medium_threshold: f32,
    #[serde(default = "default_high")]
    pub high_threshold: f32,
    #[serde(default)]
    pub target_size_gb: Option<f32>,
    #[serde(default = "default_true")]
    pub enable_quantization: bool,
}

fn default_dead() -> f32 { 0.1 }
fn default_dormant() -> f32 { 0.2 }
fn default_low() -> f32 { 0.3 }
fn default_medium() -> f32 { 0.5 }
fn default_high() -> f32 { 0.7 }

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct QuantStage {
    pub format: String,
    pub quant_types: Vec<String>,
    #[serde(default)]
    pub device_targets: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct EvalStage {
    pub benchmarks: Vec<BenchmarkDef>,
    #[serde(default)]
    pub passing_threshold: Option<f32>,
    #[serde(default = "default_true")]
    pub compare_to_base: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct BenchmarkDef {
    pub name: String,
    #[serde(default)]
    pub subset: Option<String>,
    #[serde(default)]
    pub n_shot: Option<u32>,
    #[serde(default)]
    pub submit_to_leaderboard: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct PublishStage {
    pub org: String,
    #[serde(default = "default_repo_template")]
    pub repo_name_template: String,
    #[serde(default = "default_true")]
    pub include_alloy: bool,
    #[serde(default = "default_true")]
    pub card_from_benchmarks: bool,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub private: bool,
    /// SHA-256 of the generated model card (README.md). If the card is edited
    /// after publish, this hash won't match — verification tools flag the discrepancy.
    /// The alloy is the source of truth, the card is a render.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub card_hash: Option<String>,
}

fn default_repo_template() -> String { "{base}-{domain}-forged".to_string() }

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct ExpertPruneStage {
    pub keep_experts: u32,
    #[serde(default = "default_activation")]
    pub selection_strategy: String,
    #[serde(default)]
    pub profile_dataset: Option<String>,
    #[serde(default = "default_profile_steps")]
    pub profile_steps: u32,
}

fn default_activation() -> String { "activation".to_string() }
fn default_profile_steps() -> u32 { 100 }

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct ContextExtendStage {
    pub target_length: u32,
    pub method: String,
    #[serde(default)]
    pub training_dataset: Option<String>,
    #[serde(default)]
    pub training_steps: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct ModalityStage {
    pub modality: String,
    pub encoder_model: String,
    #[serde(default = "default_projection")]
    pub projection_arch: String,
    #[serde(default = "default_true")]
    pub freeze_base: bool,
    #[serde(default = "default_true")]
    pub freeze_encoder: bool,
    #[serde(default)]
    pub training_dataset: Option<String>,
    #[serde(default)]
    pub training_steps: Option<u32>,
    #[serde(default)]
    pub projection_dim: Option<u32>,
}

fn default_projection() -> String { "mlp".to_string() }

// ── Front Bookend: Source Configuration ─────────────────────────────────────

/// Declares the starting model's capabilities and target configuration.
/// This is the "what are we working with" stage — sits at the front of every pipeline.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct SourceConfigStage {
    /// Target context window length (tokens). May trigger context-extend stage.
    #[serde(default)]
    pub context_length: Option<u32>,

    /// Input modalities the final model should support
    #[serde(default)]
    pub input_modalities: Vec<String>,

    /// Target vocabulary/tokenizer (if different from base model)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tokenizer: Option<String>,

    /// Maximum batch size the model should support at inference
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target_batch_size: Option<u32>,

    /// Target devices this model should run on (drives quant/package decisions)
    #[serde(default)]
    pub target_devices: Vec<String>,
}

// ── End Bookend: Package & Deploy ───────────────────────────────────────────

/// Package the model for specific device targets and runtimes.
/// Converts model weights into device-optimized formats beyond basic quantization.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct PackageStage {
    /// Target format for packaging
    pub format: String,

    /// Target runtime/platform
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub runtime: Option<String>,

    /// Optimization level (speed vs accuracy tradeoff)
    #[serde(default = "default_optimization")]
    pub optimization: String,

    /// Target devices to validate against
    #[serde(default)]
    pub validate_on: Vec<String>,

    /// Whether to include tokenizer in the package
    #[serde(default = "default_true")]
    pub include_tokenizer: bool,
}

fn default_optimization() -> String { "balanced".to_string() }

/// Deploy the model to a grid node or serving endpoint.
/// The final stage — puts the model into production.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct DeployStage {
    /// Target node or endpoint (grid node ID, URL, "local")
    pub target: String,

    /// Whether to run a health check after deployment
    #[serde(default = "default_true")]
    pub health_check: bool,

    /// Whether to warm up the model (run a test inference)
    #[serde(default = "default_true")]
    pub warmup: bool,

    /// Maximum serving concurrency
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_concurrency: Option<u32>,

    /// Auto-scale configuration (grid-specific)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub auto_scale: Option<bool>,
}

// ── Receipt (populated after delivery) ──────────────────────────────────────

/// The receipt — proof of delivery. Populated after publish/deploy stages complete.
/// The alloy is the work order. The results are the work product. The receipt is the delivery confirmation.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct AlloyReceipt {
    /// Where the model was published (HuggingFace URL, IPFS CID, grid node ID)
    #[serde(default)]
    pub publications: Vec<Publication>,

    /// QR code verification URL (links to verification page with alloy hash)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub verify_url: Option<String>,

    /// SHA-256 of the alloy at time of publication
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub alloy_hash: Option<String>,

    /// SHA-256 of the generated model card
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub card_hash: Option<String>,

    /// When the receipt was issued
    pub issued_at: String,
}

/// A single publication record — one per delivery target
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct Publication {
    /// Target platform (huggingface, ipfs, grid, github)
    pub target: String,

    /// URL or identifier where the model can be found
    pub url: String,

    /// When it was published
    pub published_at: String,

    /// Download count at time of receipt (for tracking)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub downloads: Option<u64>,
}

// ── Hardware & Outputs ──────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct AlloyHardware {
    #[serde(default)]
    pub min_vram_gb: Option<f32>,
    #[serde(default)]
    pub recommended_vram_gb: Option<f32>,
    #[serde(default)]
    pub estimated_duration_minutes: Option<f32>,
    #[serde(default)]
    pub supports_cpu: bool,
    #[serde(default)]
    pub tested_on: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
pub struct AlloyOutputs {
    #[serde(default)]
    pub produces: Vec<OutputArtifact>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
pub struct OutputArtifact {
    #[serde(rename = "type")]
    pub artifact_type: String,
    #[serde(default)]
    pub description: String,
}

// ── Validation ──────────────────────────────────────────────────────────────

impl ForgeAlloy {
    /// Load from a JSON file
    pub fn from_file(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let json = std::fs::read_to_string(path)?;
        let alloy: Self = serde_json::from_str(&json)?;
        Ok(alloy)
    }

    /// Validate the alloy definition
    pub fn validate(&self) -> Result<(), Vec<String>> {
        let mut errors = Vec::new();

        if self.name.is_empty() { errors.push("name is required".into()); }
        if self.source.base_model.is_empty() { errors.push("source.baseModel is required".into()); }
        if self.stages.is_empty() { errors.push("at least one stage is required".into()); }
        if self.cycles == 0 { errors.push("cycles must be >= 1".into()); }

        for (i, stage) in self.stages.iter().enumerate() {
            match stage {
                AlloyStage::Prune(p) => {
                    if p.level < 0.0 || p.level > 0.9 {
                        errors.push(format!("stage[{}] prune level must be 0.0-0.9", i));
                    }
                }
                AlloyStage::Train(t) => {
                    if t.steps == 0 {
                        errors.push(format!("stage[{}] train steps must be > 0", i));
                    }
                }
                _ => {}
            }
        }

        if errors.is_empty() { Ok(()) } else { Err(errors) }
    }

    /// Check if this alloy has been executed (has results)
    pub fn has_results(&self) -> bool {
        self.results.is_some()
    }

    /// Check if results have a signed integrity attestation
    pub fn is_signed(&self) -> bool {
        self.results
            .as_ref()
            .and_then(|r| r.integrity.as_ref())
            .map(|i| i.signature.is_some())
            .unwrap_or(false)
    }

    /// Get the trust level of the attestation (if present)
    pub fn trust_level(&self) -> Option<&TrustLevel> {
        self.results
            .as_ref()
            .and_then(|r| r.integrity.as_ref())
            .map(|i| &i.trust_level)
    }

    /// Check if this alloy has a target (delta-based mode)
    pub fn has_target(&self) -> bool {
        self.target.is_some()
    }

    /// Check if stages are empty (needs derivation from target delta)
    pub fn needs_stage_derivation(&self) -> bool {
        self.target.is_some() && self.stages.is_empty()
    }

    /// Serialize to JSON string
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_example() {
        let json = include_str!("../../examples/qwen3.5-4b-code-balanced.alloy.json");
        let alloy: ForgeAlloy = serde_json::from_str(json).unwrap();
        assert_eq!(alloy.name, "qwen3.5-4b-code-balanced");
        assert_eq!(alloy.stages.len(), 6);
        assert_eq!(alloy.cycles, 3);
        assert!(alloy.validate().is_ok());
        assert!(!alloy.has_results());
    }

    #[test]
    fn test_roundtrip() {
        let json = include_str!("../../examples/qwen3.5-4b-code-balanced.alloy.json");
        let alloy: ForgeAlloy = serde_json::from_str(json).unwrap();
        let serialized = alloy.to_json().unwrap();
        let reparsed: ForgeAlloy = serde_json::from_str(&serialized).unwrap();
        assert_eq!(alloy.name, reparsed.name);
        assert_eq!(alloy.stages.len(), reparsed.stages.len());
    }

    #[test]
    fn test_parse_with_results() {
        let json = include_str!("../../examples/qwen3.5-4b-code-balanced-executed.alloy.json");
        let alloy: ForgeAlloy = serde_json::from_str(json).unwrap();
        assert_eq!(alloy.name, "qwen3.5-4b-code-balanced");
        assert!(alloy.has_results());

        let results = alloy.results.as_ref().unwrap();
        assert_eq!(results.benchmarks.len(), 3);

        // HumanEval has passing/total/score
        let humaneval = &results.benchmarks[0];
        assert_eq!(humaneval.name, "humaneval");
        assert_eq!(humaneval.metrics["passing"], serde_json::json!(63));
        assert_eq!(humaneval.metrics["total"], serde_json::json!(85));

        // Hardware profiles
        assert_eq!(results.hardware_verified.len(), 4);
        let iphone = results.hardware_verified.iter()
            .find(|h| h.device.contains("iPhone"))
            .unwrap();
        assert_eq!(iphone.format, "Q4_K_M");
        assert!(iphone.verified);

        // Samples
        assert!(!results.samples.is_empty());
        assert!(results.samples[0].baseline_completion.is_some());
    }

    #[test]
    fn test_integrity_attestation() {
        let json = include_str!("../../examples/qwen3.5-4b-code-balanced-executed.alloy.json");
        let alloy: ForgeAlloy = serde_json::from_str(json).unwrap();

        // Example has integrity but no signature yet (self-attested, unsigned)
        assert!(!alloy.is_signed());
        assert_eq!(alloy.trust_level(), Some(&TrustLevel::SelfAttested));

        let integrity = alloy.results.as_ref().unwrap().integrity.as_ref().unwrap();
        assert!(!integrity.model_hash.is_empty());

        // Code attestation
        assert_eq!(integrity.code.runner, "sentinel-ai/forge_model");
        assert_eq!(integrity.code.version, "0.9.2");
        assert!(!integrity.code.binary_hash.is_empty());
        assert!(integrity.code.commit.is_some());

        // Dataset attestations
        assert_eq!(integrity.datasets.len(), 3);
        let humaneval = &integrity.datasets[0];
        assert_eq!(humaneval.name, "humaneval");
        assert!(!humaneval.hash.is_empty());
        assert!(humaneval.source.is_some());
    }

    #[test]
    fn test_signed_attestation() {
        let signed_json = r#"{
            "trustLevel": "verified",
            "code": {
                "runner": "forge-alloy/runner",
                "version": "1.0.0",
                "binaryHash": "sha256:aabb"
            },
            "modelHash": "sha256:ccdd",
            "alloyHash": "sha256:eeff",
            "datasets": [],
            "nonce": "dGVzdC1ub25jZQ",
            "audience": "https://marketplace.forge-alloy.dev",
            "signature": {
                "algorithm": "ES256",
                "publicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...",
                "value": "MEUCIQD...",
                "keyId": "continuum-ai/forge-runner-001",
                "credentialId": "passkey-abc123",
                "keyRegistry": "https://keys.forge-alloy.dev/v1"
            },
            "attestedAt": "2026-03-28T14:32:00Z"
        }"#;
        let attestation: IntegrityAttestation = serde_json::from_str(signed_json).unwrap();
        assert_eq!(attestation.trust_level, TrustLevel::Verified);
        assert!(attestation.signature.is_some());
        assert_eq!(attestation.nonce, Some("dGVzdC1ub25jZQ".into()));
        assert_eq!(attestation.audience, Some("https://marketplace.forge-alloy.dev".into()));
        assert_eq!(attestation.alloy_hash, Some("sha256:eeff".into()));

        let sig = attestation.signature.as_ref().unwrap();
        assert_eq!(sig.algorithm, SigningAlgorithm::ES256);
        assert_eq!(sig.key_id, Some("continuum-ai/forge-runner-001".into()));
        assert!(sig.credential_id.is_some());
        assert!(sig.key_registry.is_some());
        assert!(sig.certificate_chain.is_empty());
    }

    #[test]
    fn test_benchmark_metrics_extensible() {
        // Any benchmark can have any metrics — the format doesn't constrain them
        let result_json = r#"{
            "name": "imo-proofbench-advanced",
            "metrics": {
                "proofScore": 42.0,
                "difficulty": "advanced",
                "proofsCompleted": 7,
                "proofsAttempted": 10,
                "averageSteps": 23.5,
                "usedLemmas": true
            },
            "submittedToLeaderboard": false
        }"#;
        let result: BenchmarkResult = serde_json::from_str(result_json).unwrap();
        assert_eq!(result.name, "imo-proofbench-advanced");
        assert_eq!(result.metrics.len(), 6);
        assert_eq!(result.metrics["proofsCompleted"], serde_json::json!(7));
    }
}
