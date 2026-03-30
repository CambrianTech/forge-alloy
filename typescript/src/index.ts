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
