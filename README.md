# ForgeAlloy — Trustless AI Compute Contract

End-to-end cryptographically secured workflow — chain of custody from creation through delivery, tracked in a blockchain, rewindable in time, corruption prevented by technology.

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
- [`qwen3.5-4b-multimodal-code.alloy.json`](examples/qwen3.5-4b-multimodal-code.alloy.json) — Full pipeline: source-config → vision → context → prune → train → quant → eval → publish → deploy

## Case Studies — The Alloy Pattern Applied

The same Merkle-chained, cryptographically secured workflow handles any process that needs provenance and trust. We're using it NOW between [continuum](https://github.com/CambrianTech/continuum) and [sentinel-ai](https://github.com/CambrianTech/sentinel-ai) for model forging. The pattern is universal.

### AI Model Forging (In Production)

We forge models on consumer GPUs and publish to HuggingFace with full chain of custody. Every claim on the model card is backed by the alloy.

```
Introspect Qwen3.5-4B → delta: add code domain + GGUF quant
  → forge (3 cycles on RTX 5090) → attest (code hash + model hash)
  → eval (HumanEval 74.1%) → publish (HF + alloy file + QR)
```

**Result**: 15,000+ downloads across 13 published models. Every model carries its alloy. Anyone can verify the forge, reproduce the pipeline, or re-forge with modifications.

### Content Authenticity (Deepfake Prevention)

Camera with hardware enclave signs the raw image at capture. Every edit is a tracked delta. The Merkle chain proves what's real and what's modified.

```
Capture (Canon R5, enclave-signed)          → sha256:abc  ← root of trust
  ↓
Crop + levels (Photoshop CC via API)        → sha256:def  ← delta: crop(10,20,800,600)
  ↓
Publish to Twitter                          → sha256:def  ← unmodified since edit
```

**Scan QR → full edit history.** AI generated? Chain starts with a generation model, not a camera enclave. Altered? Every edit listed with exact parameters and tool. Unaltered? Camera hash matches published hash. No chain = no trust.

Steganographic embedding puts the alloy hash invisibly in the image itself. Even if the QR is cropped, the proof survives.

### Physical Manufacturing (Etsy, Supply Chain)

A producer's workflow from design through delivery, verified end to end:

```
Design (ring-v3.stl, silver)                → sha256:abc
  ↓
3D Print (Formlabs, 80% infill)             → sha256:def  ← attested by printer
  ↓
Quality check (weight: 12.3g, 4 photos)     → sha256:ghi
  ↓
Publish (Etsy + Shopify)                    → sha256:jkl
  ↓
Ship (USPS 9400..., GPS cold chain)         → sha256:mno
```

**QR on the package.** Buyer scans → sees full provenance. Photos match product. Manufacturing specs recorded. Returns traceable. Trust without trusting the seller.

### Pharmaceutical / Regulated Manufacturing

FDA-grade batch records as alloy contracts:

```
Compound (lot numbers, raw materials)       → sha256:abc  ← facility-attested
  ↓
Synthesize (reactor: 180°C, 4hr, yield 94%) → sha256:def
  ↓
Quality test (purity 99.7%)                 → sha256:ghi  ← enclave-attested lab
  ↓
Package (lot XY-2026-0331, exp 2028-03)     → sha256:jkl
  ↓
Distribute (cold chain verified)            → sha256:mno
```

**FDA audit = verify the chain.** Every step attested. Every parameter recorded. The alloy IS the batch record.

### Creative IP (Music, Film, Software)

Prove who created what, when, with what tools:

```
Record (studio, 24-bit/96kHz, 3 musicians)  → sha256:abc  ← hardware-attested interface
  ↓
Mix (Pro Tools, 47 tracks)                  → sha256:def
  ↓
Master (LUFS -14, true peak -1dB)           → sha256:ghi
  ↓
Publish (Spotify + Apple + Bandcamp)        → sha256:jkl
```

**Copyright dispute?** The chain resolves it. Who recorded what, when, mixed by whom, mastered to what spec. Timestamped and signed.

### The Common Pattern

Every case follows the same structure. Different stage types, same infrastructure:

```
Source → Delta → Stages → Attest → Deliver → Verify (QR)
```

The Merkle chain secures it. The attestation proves it. The QR makes it accessible. The blockchain anchors it in time. [Full applications doc →](docs/APPLICATIONS.md)

## Design Principles

- **JSON always** — no YAML, no TOML
- **Typed stages** — each stage has its own interface with validation ranges
- **Composable** — stages are ordered, optional, mix and match
- **Portable** — the JSON contains everything needed to reproduce
- **Lineage** — `sourceAlloyId` tracks re-forge chains
- **Verifiable** — cryptographic attestation proves results are genuine
- **Extensible** — open metric bags, arbitrary benchmarks, progressive trust tiers

## Delivery

An executed alloy is self-contained and self-verifying. The signature survives any transport:

- **HuggingFace** — upload with `forge-alloy` tag, auto-generate model card from results
- **IPFS** — content-addressed, immutable by design
- **Grid transfer** — node-to-node via mesh network
- **HTTP / S3 / torrent** — any file transfer
- **USB / local copy** — airgapped delivery

No central authority required. The verifier checks the alloy's hashes and signature, not where it came from. The alloy IS the proof.

## Documentation

- [docs/ATTESTATION.md](docs/ATTESTATION.md) — Full attestation architecture and design

## License

Apache 2.0
