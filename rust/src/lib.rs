//! # ForgeAlloy
//!
//! Portable pipeline format for model forging.
//! Define, share, and execute model transformation pipelines across any hardware.
//!
//! ```rust
//! use forge_alloy::ForgeAlloy;
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

#[cfg(feature = "typescript")]
use ts_rs::TS;

// ── Root Entity ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
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
    pub stages: Vec<AlloyStage>,
    #[serde(default = "default_cycles")]
    pub cycles: u32,

    #[serde(default)]
    pub hardware: Option<AlloyHardware>,
    #[serde(default)]
    pub outputs: Option<AlloyOutputs>,

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

// ── Stages (discriminated union via serde tag) ──────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum AlloyStage {
    Prune(PruneStage),
    Train(TrainStage),
    Lora(LoRAStage),
    Compact(CompactStage),
    Quant(QuantStage),
    Eval(EvalStage),
    Publish(PublishStage),
    ExpertPrune(ExpertPruneStage),
    ContextExtend(ContextExtendStage),
    Modality(ModalityStage),
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
}
