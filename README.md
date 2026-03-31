# ForgeAlloy

**Trustless AI Compute.** Define, share, execute, and cryptographically verify model transformation pipelines across any hardware.

A `.alloy.json` is a **Dockerfile for models** — the complete, typed specification for transforming a base model into a specialized one. It's both the recipe (before execution) and the report card (after execution), with cryptographic attestation so nobody can fake the results.

## Quick Example

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

After execution, the same file gains a `results` section with benchmark scores, hardware performance profiles, generation samples, and an integrity attestation — everything needed to generate a high-quality model card.

## Packages

| Package | Language | Source of Truth |
|---------|----------|----------------|
| `forge-alloy` | Rust | **Yes** — all types originate here |
| `forge-alloy` | Python | Generated from Rust (Pydantic models) |
| `@continuum-ai/forge-alloy` | TypeScript | Generated from Rust (ts-rs) |

## Stage Types

| Stage | What It Does |
|-------|-------------|
| `prune` | Head pruning (entropy, magnitude, gradient) |
| `train` | Recovery/fine-tuning with full training config |
| `lora` | LoRA adapter training (QLoRA, rank, alpha, dropout) |
| `compact` | Plasticity-based mixed-precision compaction |
| `quant` | Output quantization (GGUF, MLX, ONNX) |
| `eval` | Benchmarking (HumanEval, MMLU, GSM8K, IMO-ProofBench, custom) |
| `publish` | Push to HuggingFace with generated model card |
| `expert-prune` | MoE expert pruning by activation profile |
| `context-extend` | RoPE rescaling (YaRN, NTK) for longer context |
| `modality` | Add vision/audio encoder (LLaVA-style, Whisper-style) |

## Results & Benchmarks

After execution, the alloy carries its own evidence:

```json
{
  "results": {
    "baselinePerplexity": 3.04,
    "finalPerplexity": 2.31,
    "improvementPct": 24.0,
    "benchmarks": [
      {
        "name": "humaneval",
        "metrics": { "passing": 63, "total": 85, "score": 74.1 }
      }
    ],
    "hardwareVerified": [
      { "device": "iPhone 17", "format": "Q4_K_M", "sizeGb": 2.6, "tokensPerSec": 8.0, "verified": true },
      { "device": "RTX 5090", "format": "fp16", "sizeGb": 8.0, "tokensPerSec": 174.0, "verified": true }
    ],
    "samples": [
      { "label": "Merge Sort", "prompt": "def merge_sort(arr):", "completion": "..." }
    ]
  }
}
```

Benchmark metrics are **open-ended** — each benchmark reports whatever it wants. HumanEval has `passing`/`total`/`score`. MMLU has `accuracy`/`nShot`. IMO-ProofBench has `proofScore`/`difficulty`. The format doesn't constrain what benchmarks can express.

## Integrity Attestation

Modeled after **FIDO2/WebAuthn attestation**. Proves what code ran, on what data, in what environment — and signs the whole chain with ES256 (ECDSA P-256).

```json
{
  "results": {
    "integrity": {
      "trustLevel": "self-attested",
      "code": {
        "runner": "sentinel-ai/forge_model",
        "version": "0.9.2",
        "binaryHash": "sha256:a1b2c3...",
        "commit": "09bb60f"
      },
      "modelHash": "sha256:7f8a9b...",
      "datasets": [
        { "name": "humaneval", "hash": "sha256:abc123...", "source": "https://github.com/openai/human-eval" }
      ],
      "signature": {
        "algorithm": "ES256",
        "publicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...",
        "value": "MEUCIQD...",
        "keyRegistry": "https://keys.forge-alloy.dev/v1"
      },
      "attestedAt": "2026-03-28T14:32:00Z"
    }
  }
}
```

**Trust tiers** (like WebAuthn attestation types):

| Tier | What It Proves | Verification |
|------|---------------|-------------|
| `self-attested` | Signer vouches for itself | Public key in registry |
| `verified` | Third-party audited the runner | Certificate chain |
| `enclave` | TEE execution, hardware-bound proof | Hardware attestation |

**What it prevents:** fabricated benchmarks, modified eval code, cherry-picked datasets, model swaps, replay attacks. See [docs/ATTESTATION.md](docs/ATTESTATION.md) for the full design.

## Usage

### Rust

```rust
use forge_alloy::{ForgeAlloy, AlloyStage};

let alloy = ForgeAlloy::from_file("my-alloy.json")?;
alloy.validate()?;

if alloy.has_results() {
    println!("Trust: {:?}", alloy.trust_level());
    println!("Signed: {}", alloy.is_signed());
}

for stage in &alloy.stages {
    match stage {
        AlloyStage::Prune(p) => println!("Pruning {}%", p.level * 100.0),
        AlloyStage::Train(t) => println!("Training {} steps", t.steps),
        _ => {}
    }
}
```

### Python

```python
from forge_alloy import ForgeAlloy

alloy = ForgeAlloy.from_file("my-alloy.json")
errors = alloy.validate_alloy()

if alloy.has_results:
    print(f"Trust: {alloy.trust_level}")
    for b in alloy.results.benchmarks:
        print(f"  {b.name}: {b.metrics}")
```

### TypeScript

```typescript
import { ForgeAlloy, validateAlloy, isSigned, trustLevel } from '@continuum-ai/forge-alloy';

const alloy: ForgeAlloy = JSON.parse(fs.readFileSync('alloy.json', 'utf-8'));
const errors = validateAlloy(alloy);

if (alloy.results) {
  console.log(`Trust: ${trustLevel(alloy)}, Signed: ${isSigned(alloy)}`);
}
```

## Schema

The complete JSON Schema is at [`schema/forge-alloy.schema.json`](schema/forge-alloy.schema.json).

## Examples

- [`qwen3.5-4b-code-balanced.alloy.json`](examples/qwen3.5-4b-code-balanced.alloy.json) — Recipe (before execution)
- [`qwen3.5-4b-code-balanced-executed.alloy.json`](examples/qwen3.5-4b-code-balanced-executed.alloy.json) — Executed (with results, benchmarks, hardware profiles, attestation)

## Design Principles

- **JSON always** — no YAML, no TOML
- **Typed stages** — each stage has its own interface with validation ranges
- **Composable** — stages are ordered, optional, mix and match
- **Portable** — the JSON contains everything needed to reproduce
- **Lineage** — `sourceAlloyId` tracks re-forge chains
- **Verifiable** — cryptographic attestation proves results are genuine
- **Extensible** — open metric bags, arbitrary benchmarks, progressive trust tiers

## HuggingFace Integration

Published models tagged with `forge-alloy` include the alloy file. The `results` section contains everything needed to auto-generate model cards: benchmark tables, hardware device grids, generation samples, and reproducibility commands.

## Documentation

- [docs/ATTESTATION.md](docs/ATTESTATION.md) — Full attestation architecture and design

## License

Apache 2.0
