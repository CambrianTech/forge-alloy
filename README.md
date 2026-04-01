# ForgeAlloy — Trustless Contract for AI and Beyond

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

Stages are the building blocks of every alloy pipeline. They're organized into three phases — **input** (configure), **transform** (modify the model), **output** (produce deliverables) — and are **domain-extensible**. The stages below are the LLM domain. Other domains (vision, audio, diffusion, robotics) register their own stage types with the same schema pattern.

### LLM Domain (built-in)

| Stage | Phase | What It Does |
|-------|-------|-------------|
| `source-config` | input | Context window, modalities, target devices |
| `context-extend` | input | RoPE rescaling (YaRN, NTK) for longer context |
| `modality` | input | Add vision/audio encoder (LLaVA-style, Whisper-style) |
| `prune` | transform | Head pruning (entropy, magnitude, gradient) |
| `train` | transform | Recovery/fine-tuning with full training config |
| `lora` | transform | LoRA adapter training (QLoRA, rank, alpha, dropout) |
| `compact` | transform | Plasticity-based mixed-precision compaction |
| `expert-prune` | transform | MoE expert pruning by activation profile |
| `quant` | output | Output quantization (GGUF, MLX, ONNX, safetensors) |
| `eval` | output | Benchmarking (HumanEval, MMLU, GSM8K, custom) |
| `publish` | output | Push to HuggingFace with generated model card |
| `deploy` | output | Deploy to grid node for serving |

### Domain Extension

Forge-alloy is not LLM-specific. The stage system is generic — any domain can register stages that follow the same input/transform/output pattern:

| Domain | Example Stages |
|--------|---------------|
| **Vision** | `augment`, `backbone-swap`, `detection-head`, `calibrate` |
| **Diffusion** | `unet-prune`, `scheduler-swap`, `vae-tune` |
| **Audio** | `codec-swap`, `speaker-adapt`, `denoise` |
| **Robotics** | `sim-to-real`, `policy-distill`, `safety-bound` |

Each domain defines its own stage configs, executors, and eval benchmarks. The alloy contract, attestation, and pipeline execution are domain-agnostic — the same executor runs any domain's stages. See [#7](https://github.com/CambrianTech/forge-alloy/issues/7) for the domain extension roadmap.

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

## Hardware Trust Integration

Every device that touches the chain can prove its involvement. The trust ladder goes from "take my word for it" to "silicon proves it":

### The Trust Ladder

| Level | Authority | How It Proves | Example |
|-------|-----------|--------------|---------|
| **Repository** | GitHub | Commit hash = Merkle root of repo state. GitHub vouches for content at that hash. | `sourceRepo` + `commit` in `CodeAttestation` |
| **Passkey** | Device Secure Enclave | ES256 keypair bound to hardware. Non-exportable. Proves *this device* signed. | macOS `SecKeyCreateSignature`, Android StrongBox, Windows TPM |
| **GPU TEE** | NVIDIA silicon | Blackwell/Hopper TEE-I/O. Hardware attestation report from SEC2 security component. NRAS remote attestation. | `certificateChain` carries NVIDIA attestation cert |
| **Cloud Enclave** | AWS Nitro / Azure SGX | Isolated execution environment. Hypervisor cannot read enclave memory. | Nitro attestation document in `anchor` |
| **Mobile Enclave** | Apple / Android | Secure Enclave (iPhone/Mac) or StrongBox (Android). Biometric-gated signing. | Touch ID / Face ID protects forge signing key |
| **Sensor** | Camera / microphone / IoT | Hardware-signed capture at the source. Proves content was captured, not generated. | Camera enclave signs raw image → root of trust for content authenticity |

### Repository Binding (Phase 1 — Now)

GitHub is the certificate authority. No additional crypto needed.

```json
{
  "code": {
    "runner": "sentinel-ai/alloy_executor",
    "commit": "abc123def",
    "sourceRepo": "https://github.com/CambrianTech/sentinel-ai",
    "binaryHash": "sha256:..."
  }
}
```

Verification: hash the file at `sourceRepo/blob/commit/script.py`, compare to `binaryHash`. If they match, the code that ran is the code on GitHub. If not, something was modified.

### Passkey Signing (Phase 2)

The forge runner's device signs the attestation with a hardware-bound key:

- **macOS/iOS**: Apple Secure Enclave via `SecKeyCreateSignature` — Touch ID protected, non-exportable
- **Android**: KeyStore with `setIsStrongBoxBacked(true)` — hardware-bound ES256
- **Windows**: TPM 2.0 via `NCryptSignHash` — platform-bound signing

The key never leaves the device. The signature proves *this specific machine* forged *this specific model*. Same primitive as FIDO2 passkeys — different ceremony, same hardware.

### GPU TEE (Phase 4 — Required for Marketplace)

NVIDIA Blackwell architecture has TEE silicon. The GPU itself attests what code ran:

```
Forge runner loads into GPU TEE
  → GPU firmware hash recorded (environmentHash)
  → NVIDIA Attestation Service (NRAS) issues remote attestation
  → SEC2 security component generates hardware report
  → certificateChain carries NVIDIA's attestation certificate
  → Model weights hashed inside TEE before leaving enclave
```

This is the only tier where **every claim is hardware-proven**. The GPU can't lie about what code ran. The model hash is captured inside the enclave before the weights touch untrusted memory. Input-to-output binding is cryptographically guaranteed.

**Supported hardware:**
- NVIDIA B200 / GB200 (datacenter) — TEE-I/O today
- NVIDIA RTX PRO 6000 Server — TEE via R580 TRD1
- NVIDIA RTX 5090 (consumer) — TEE mode pending driver unlock
- AWS Nitro Enclaves — available now for cloud forging
- Intel SGX / TDX — CPU-side TEE

### Mobile Enclave (Inference Verification)

iPhone and MacBook have Secure Enclaves that can sign inference results:

```
Model runs on iPhone → inference result signed by Secure Enclave
  → signature proves: this device, this model, this output
  → hardware profile (tokens/sec, memory) is measured, not claimed
```

This enables verified inference benchmarks on consumer devices — the device proves it actually ran the model at the claimed speed.

### Sensor Attestation (Content Authenticity)

Cameras and microphones with hardware enclaves sign captures at the source. The sensor is the root of trust — every transformation after capture is a tracked stage.

**Photography:**
```
Canon R5 (enclave) captures image → signs raw bytes → sha256:abc (root of trust)
  → Photoshop edit (tracked delta: crop, levels) → sha256:def
  → publish → sha256:def matches, chain intact
```

**Video production — full Merkle chain from lens to screen:**
```
Sony sensor (enclave-signed raw frames)          → sha256:abc  ← hardware root of trust
  ↓
ProRes encode (attested by encoder adapter)      → sha256:def  ← stage: transcode
  ↓
DaVinci Resolve edit (each cut is a delta)       → sha256:ghi  ← stage: edit
  ↓
Color grade (LUT application)                    → sha256:jkl  ← stage: color
  ↓
VFX composite (real vs generated — declared)     → sha256:mno  ← stage: vfx (declares what's synthetic)
  ↓
Master (final encode)                            → sha256:pqr  ← stage: master
  ↓
Distribute (Netflix, theaters, YouTube)          → sha256:pqr  ← receipt: delivery matches master
```

Every frame's provenance traces back to the sensor that captured it. Sony signs at capture with their enclave. Each tool in the chain (Resolve, After Effects, Nuke) is an adapter that attests its transformation. The Merkle chain proves:

- **This was captured** — sensor enclave signature, not AI generated
- **These edits were made** — every cut, grade, and composite is a declared stage
- **What's synthetic is declared** — VFX stage explicitly marks generated content
- **Nothing else changed** — hash of each stage input matches previous stage output
- **The final master is authentic** — alloy hash = what was delivered

**Deepfake detection becomes trivial:** if the chain starts with a generation model instead of a camera enclave, that's visible. No sensor attestation at the root = no proof of capture. The absence of hardware proof IS the tell.

The forge-alloy pattern doesn't care if it's a GPU forging a model or a CMOS sensor capturing photons. Same chain, same math, same verification page.

### Adapter Certifications (Independent Witnesses)

Third-party adapters sign their own findings with their own keys. Each adapter is an independent certifier — like UL for products:

```json
{
  "certifications": [
    {
      "adapter": "forge-alloy/humaneval",
      "domain": "benchmark:humaneval",
      "result": { "passing": 63, "total": 85, "score": 74.1 },
      "signature": { "algorithm": "ES256", "publicKey": "...", "value": "..." },
      "nonce": "api-provided-challenge",
      "sourceRepo": "https://github.com/CambrianTech/forge-alloy",
      "attestedAt": "2026-03-31T12:00:00Z"
    }
  ]
}
```

Open-source adapters get higher trust — anyone can audit the code. The forge-alloy API issues nonces and countersigns results, adding a second independent witness. See [docs/SDK-ARCHITECTURE.md](docs/SDK-ARCHITECTURE.md).

## Design Principles

- **JSON always** — no YAML, no TOML
- **Typed stages** — each stage has its own interface with validation ranges
- **Composable** — stages are ordered, optional, mix and match
- **Portable** — the JSON contains everything needed to reproduce
- **Lineage** — `sourceAlloyId` tracks re-forge chains
- **Verifiable** — cryptographic attestation proves results are genuine
- **Extensible** — open metric bags, arbitrary benchmarks, progressive trust tiers

## This Repo IS the Trust Infrastructure

This repository is Merkle-chained by git itself. Every commit hashes its parent. Every file has a SHA. The spec, the SDK, the verification page, and the examples all live here — secured by the same chain they describe.

- **The spec** is a file in this repo → its hash is in the commit → the commit is in the chain
- **The SDK** validates alloys using types defined here → the types are hashed → in the chain
- **The verify page** runs on GitHub Pages from this repo → its source is hashed → in the chain
- **The examples** are real alloys → their hashes are verifiable → in the chain

The repo that defines the trust standard IS part of the trust chain. The certificate authority certifies itself — not circularly, but because git's Merkle tree is the root. Fork this repo and your fork has a different hash. The chain proves which is the original.

`git log --format='%H %s'` is the audit trail. Every change to the spec, the SDK, the verification page — tracked, hashed, immutable in history.

## Delivery

An executed alloy is self-contained and self-verifying. The signature survives any transport:

- **[HuggingFace](https://huggingface.co/models?other=forge-alloy)** — upload with `forge-alloy` tag, auto-generate model card from results
- **IPFS** — content-addressed, immutable by design
- **Grid transfer** — node-to-node via mesh network
- **HTTP / S3 / torrent** — any file transfer
- **USB / local copy** — airgapped delivery

No central authority required. The verifier checks the alloy's hashes and signature, not where it came from. The alloy IS the proof.

## Documentation

- [docs/ATTESTATION.md](docs/ATTESTATION.md) — Full attestation architecture (FIDO2 model, trust tiers, signing, replay prevention)
- [docs/SDK-ARCHITECTURE.md](docs/SDK-ARCHITECTURE.md) — SDK adapter framework (independent certifications, API witnessing, becoming a certifier)
- [docs/APPLICATIONS.md](docs/APPLICATIONS.md) — Use cases beyond model forging
- [docs/ECOSYSTEM.md](docs/ECOSYSTEM.md) — Compensation and contribution model

## License

Apache 2.0
