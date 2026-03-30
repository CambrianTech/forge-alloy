# ForgeAlloy

Portable pipeline format for model forging. Define, share, and execute model transformation pipelines across any hardware.

## What Is An Alloy?

An alloy is a complete, typed specification for transforming a base model into a specialized one. It's a JSON pipeline of stages — pruning, training, compaction, quantization, evaluation, publishing — that any compatible tool can execute.

```json
{
  "name": "qwen3.5-4b-code-balanced",
  "version": "1.0.0",
  "source": { "baseModel": "Qwen/Qwen3.5-4B", "architecture": "qwen3_5" },
  "stages": [
    { "type": "prune", "strategy": "entropy", "level": 0.3 },
    { "type": "train", "domain": "code", "steps": 1000, "learningRate": "2e-4" },
    { "type": "quant", "format": "gguf", "quantTypes": ["Q4_K_M"] },
    { "type": "eval", "benchmarks": [{ "name": "humaneval" }] },
    { "type": "publish", "org": "continuum-ai" }
  ],
  "cycles": 3
}
```

## Packages

| Package | Language | Install |
|---------|----------|---------|
| `forge-alloy` | Rust | `cargo add forge-alloy` |
| `forge-alloy` | Python | `pip install forge-alloy` |
| `@continuum-ai/forge-alloy` | TypeScript | `npm install @continuum-ai/forge-alloy` |

All three are generated from the same Rust source of truth.

## Stage Types

| Stage | What It Does |
|-------|-------------|
| `prune` | Head pruning (entropy, magnitude, gradient) |
| `train` | Recovery/fine-tuning with full training config |
| `lora` | LoRA adapter training (QLoRA, rank, alpha, dropout) |
| `compact` | Plasticity-based mixed-precision compaction |
| `quant` | Output quantization (GGUF, MLX, ONNX) |
| `eval` | Benchmarking (HumanEval, MMLU, GSM8K, custom) |
| `publish` | Push to HuggingFace with generated model card |
| `expert-prune` | MoE expert pruning by activation profile |
| `context-extend` | RoPE rescaling (YaRN, NTK) for longer context |
| `modality` | Add vision/audio encoder (LLaVA-style, Whisper-style) |

## Schema

The complete JSON Schema is at [`schema/forge-alloy.schema.json`](schema/forge-alloy.schema.json).

## Usage

### Python

```python
from forge_alloy import ForgeAlloy

alloy = ForgeAlloy.from_file("my-alloy.json")
alloy.validate()

for stage in alloy.stages:
    print(f"{stage.type}: {stage}")
```

### Rust

```rust
use forge_alloy::ForgeAlloy;

let alloy: ForgeAlloy = serde_json::from_str(&json)?;
alloy.validate()?;

for stage in &alloy.stages {
    match stage {
        AlloyStage::Prune(p) => println!("Pruning {}%", p.level * 100.0),
        AlloyStage::Train(t) => println!("Training {} steps", t.steps),
        _ => {}
    }
}
```

### TypeScript

```typescript
import { ForgeAlloy, validateAlloy } from '@continuum-ai/forge-alloy';

const alloy: ForgeAlloy = JSON.parse(fs.readFileSync('alloy.json', 'utf-8'));
validateAlloy(alloy);
```

## Design Principles

- **JSON always** — no YAML, no TOML
- **Typed stages** — each stage has its own interface with validation ranges
- **Composable** — stages are ordered, optional, mix and match
- **Portable** — the JSON contains everything needed to reproduce
- **Lineage** — `sourceAlloyId` tracks re-forge chains
- **Community** — publish alongside models on HuggingFace, import others' alloys

## License

Apache 2.0
