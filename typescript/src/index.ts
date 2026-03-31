/**
 * ForgeAlloy — Portable pipeline format for model forging.
 *
 * NOTE: These types will be auto-generated from Rust via ts-rs.
 * This hand-written version is the initial scaffold.
 */

// ── Source ──────────────────────────────────────────────────────────────────

export interface AlloySource {
  baseModel: string;
  architecture: string;
  revision?: string;
  isMoE?: boolean;
  totalExperts?: number;
}

// ── Results (populated after execution) ────────────────────────────────────

/** Complete results from executing an alloy pipeline. */
export interface AlloyResults {
  completedAt?: string;
  durationMinutes?: number;
  baselinePerplexity?: number;
  finalPerplexity?: number;
  improvementPct?: number;
  finalSizeGb?: number;
  finalParams?: string;
  benchmarks: BenchmarkResult[];
  hardwareVerified: HardwareProfile[];
  samples: GenerationSample[];
  integrity?: IntegrityAttestation;
}

/**
 * A single benchmark result. Metrics are open-ended — each benchmark
 * reports whatever it wants (passing, total, accuracy, score, etc.)
 */
export interface BenchmarkResult {
  name: string;
  subset?: string;
  metrics: Record<string, number | string | boolean>;
  submittedToLeaderboard?: boolean;
  resultHash?: string;
}

/** Verified performance on a specific device — generates model card device grid */
export interface HardwareProfile {
  device: string;
  format: string;
  sizeGb?: number;
  tokensPerSec?: number;
  memoryUsageGb?: number;
  verified: boolean;
}

/** Raw model output sample — no cherry-picking, no post-processing */
export interface GenerationSample {
  label: string;
  prompt: string;
  completion: string;
  baselineCompletion?: string;
}

/** Trust tier — maps to WebAuthn attestation types */
export type TrustLevel = 'self-attested' | 'verified' | 'enclave';

/** Signing algorithm — extensible to post-quantum */
export type SigningAlgorithm = 'ES256' | 'ES384' | 'EdDSA' | 'ML-DSA-65' | 'ML-DSA-87' | 'SLH-DSA-128s';

/**
 * Cryptographic attestation for verified benchmark execution.
 * Modeled after FIDO2/WebAuthn attestation.
 *
 * IMPORTANT: Self-attested only prevents accidental corruption, NOT adversarial
 * modification. Only enclave tier provides tamper-proof guarantees.
 *
 * Canonicalization: signed payload MUST use RFC 8785 (JCS).
 */
export interface IntegrityAttestation {
  trustLevel: TrustLevel;
  code: CodeAttestation;
  modelHash: string;
  alloyHash?: string;
  datasets: DatasetAttestation[];
  /** Verifier-provided nonce for replay prevention (like WebAuthn challenge) */
  nonce?: string;
  /** Audience binding — who this attestation is for (prevents cross-marketplace replay) */
  audience?: string;
  signature?: AttestationSignature;
  attestedAt: string;
}

/** Attestation of the code that produced results */
export interface CodeAttestation {
  runner: string;
  version: string;
  binaryHash: string;
  sourceHash?: string;
  commit?: string;
  environment?: string;
  environmentHash?: string;
}

/** Attestation of a benchmark dataset — hash covers exactly the subset used */
export interface DatasetAttestation {
  name: string;
  version?: string;
  hash: string;
  source?: string;
}

/**
 * Signature over the attestation payload (RFC 8785 JCS canonical form).
 *
 * NOTE on passkeys: WebAuthn signs clientDataJSON, not arbitrary payloads.
 * Phase 2 needs a signing service that bridges this gap.
 */
export interface AttestationSignature {
  algorithm: SigningAlgorithm;
  /** Base64url public key — verifiers MUST check against registry, not trust this directly */
  publicKey: string;
  value: string;
  keyId?: string;
  credentialId?: string;
  certificateChain?: string[];
  keyRegistry?: string;
}

// ── Stages ──────────────────────────────────────────────────────────────────

export type AlloyStage =
  | PruneStage
  | TrainStage
  | LoRAStage
  | CompactStage
  | QuantStage
  | EvalStage
  | PublishStage
  | ExpertPruneStage
  | ContextExtendStage
  | ModalityStage;

export interface PruneStage {
  type: 'prune';
  strategy: 'entropy' | 'magnitude' | 'gradient' | 'random';
  level: number;
  minHeadsPerLayer?: number;
  minKvHeadsPerLayer?: number;
  analysisSteps?: number;
}

export interface TrainStage {
  type: 'train';
  domain: string;
  dataset?: string;
  steps: number;
  learningRate: string;
  batchSize?: number;
  gradientAccumulation?: number;
  scheduler?: 'cosine' | 'linear' | 'constant' | 'constant_with_warmup' | 'polynomial';
  warmupRatio?: number;
  weightDecay?: number;
  maxGradientNorm?: number;
  precision?: 'bf16' | 'fp16' | 'fp32';
  sequenceLength?: number;
  optimizations?: string[];
}

export interface LoRAStage {
  type: 'lora';
  rank: number;
  alpha?: number;
  dropout?: number;
  targetModules?: string[];
  quantize?: boolean;
  quantizeBits?: 4 | 8;
  dataset?: string;
  epochs?: number;
  learningRate?: string;
  batchSize?: number;
  mergeAfter?: boolean;
}

export interface CompactStage {
  type: 'compact';
  deadThreshold?: number;
  dormantThreshold?: number;
  lowThreshold?: number;
  mediumThreshold?: number;
  highThreshold?: number;
  targetSizeGb?: number;
  enableQuantization?: boolean;
}

export interface QuantStage {
  type: 'quant';
  format: 'gguf' | 'mlx' | 'safetensors' | 'onnx';
  quantTypes: string[];
  deviceTargets?: string[];
}

export interface BenchmarkDef {
  name: string;
  subset?: string;
  nShot?: number;
  submitToLeaderboard?: boolean;
}

export interface EvalStage {
  type: 'eval';
  benchmarks: BenchmarkDef[];
  passingThreshold?: number;
  compareToBase?: boolean;
}

export interface PublishStage {
  type: 'publish';
  org: string;
  repoNameTemplate?: string;
  includeAlloy?: boolean;
  cardFromBenchmarks?: boolean;
  tags?: string[];
  private?: boolean;
}

export interface ExpertPruneStage {
  type: 'expert-prune';
  keepExperts: number;
  selectionStrategy?: 'activation' | 'gradient' | 'random';
  profileDataset?: string;
  profileSteps?: number;
}

export interface ContextExtendStage {
  type: 'context-extend';
  targetLength: number;
  method: 'yarn' | 'ntk' | 'linear' | 'dynamic-ntk';
  trainingDataset?: string;
  trainingSteps?: number;
}

export interface ModalityStage {
  type: 'modality';
  modality: 'vision' | 'audio' | 'multimodal';
  encoderModel: string;
  projectionArch?: 'mlp' | 'cross-attention' | 'linear';
  freezeBase?: boolean;
  freezeEncoder?: boolean;
  trainingDataset?: string;
  trainingSteps?: number;
  projectionDim?: number;
}

// ── Hardware & Outputs ──────────────────────────────────────────────────────

export interface AlloyHardware {
  minVramGb?: number;
  recommendedVramGb?: number;
  estimatedDurationMinutes?: number;
  supportsCPU?: boolean;
  testedOn?: string[];
}

export interface OutputArtifact {
  type: 'safetensors' | 'gguf' | 'mlx' | 'lora-adapter' | 'model-card' | 'alloy';
  description?: string;
}

export interface AlloyOutputs {
  produces: OutputArtifact[];
}

// ── Root Entity ─────────────────────────────────────────────────────────────

export interface ForgeAlloy {
  name: string;
  version: string;
  description?: string;
  author?: string;
  tags?: string[];
  license?: string;

  source: AlloySource;
  stages: AlloyStage[];
  cycles: number;

  hardware?: AlloyHardware;
  outputs?: AlloyOutputs;

  /** Populated after execution — benchmark scores, hardware verification, samples */
  results?: AlloyResults;

  sourceAlloyId?: string;
  forgedModelIds?: string[];
}

// ── Validation ──────────────────────────────────────────────────────────────

export function validateAlloy(alloy: ForgeAlloy): string[] {
  const errors: string[] = [];

  if (!alloy.name) errors.push('name is required');
  if (!alloy.source?.baseModel) errors.push('source.baseModel is required');
  if (!alloy.stages?.length) errors.push('at least one stage is required');
  if (!alloy.cycles || alloy.cycles < 1) errors.push('cycles must be >= 1');

  for (let i = 0; i < (alloy.stages?.length ?? 0); i++) {
    const stage = alloy.stages[i];
    if (stage.type === 'prune' && (stage.level < 0 || stage.level > 0.9)) {
      errors.push(`stage[${i}] prune level must be 0.0-0.9`);
    }
    if (stage.type === 'train' && (!stage.steps || stage.steps <= 0)) {
      errors.push(`stage[${i}] train steps must be > 0`);
    }
  }

  return errors;
}

/** Check if an alloy has been executed (has results) */
export function hasResults(alloy: ForgeAlloy): boolean {
  return alloy.results != null;
}

/** Check if results have a signed integrity attestation */
export function isSigned(alloy: ForgeAlloy): boolean {
  return alloy.results?.integrity?.signature != null;
}

/** Get the trust level of the attestation */
export function trustLevel(alloy: ForgeAlloy): TrustLevel | undefined {
  return alloy.results?.integrity?.trustLevel;
}
