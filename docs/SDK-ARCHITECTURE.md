# ForgeAlloy SDK Architecture — Certification Through Adapters

The forge-alloy SDK is a certification framework. Every element in the chain of custody is a slot for an adapter that provides deterministic cryptographic proof.

## The Model: UL for AI

UL (Underwriters Laboratories) doesn't manufacture anything. They certify that a product meets safety standards — independently, with their own testing, signed with their own authority. If UL says a toaster is safe, you trust UL, not the toaster manufacturer.

forge-alloy is the same pattern for AI models:

```
UL for Products                  forge-alloy for Models
───────────────                  ──────────────────────
UL certifies safety              Adapter certifies one chain element
UL has its own lab               Adapter runs its own eval/audit
UL signs with its own mark       Adapter signs with its own key
Manufacturer submits product     Forge runner submits alloy
Multiple certifiers per product  Multiple adapters per model
Anyone can check UL listing      Anyone can verify adapter signature
```

## How Adapters Work

An adapter is an independent authority that certifies one aspect of a model. Each adapter:

1. Is reviewed and approved (open source — auditable by anyone)
2. Has its own keypair (its "passkey" — identity in the registry)
3. Runs its own tests (deterministic, reproducible)
4. Signs its results with its own key (independent of the forge runner)
5. Appends its `AdapterAttestation` to the alloy's `certifications[]`

```
┌─ Alloy Chain ─────────────────────────────────────────────────────────┐
│                                                                       │
│  integrity.code            ← Forge runner's own attestation           │
│  integrity.modelHash       ← SHA-256 of weights                      │
│  integrity.signature       ← Forge runner's signature                 │
│                                                                       │
│  certifications[]:         ← Independent adapter attestations         │
│    [0] forge-alloy/humaneval  ← Eval adapter, signed with its key    │
│    [1] ul/safety-audit        ← UL adapter, signed with UL's key     │
│    [2] nvidia/perf-cert       ← NVIDIA adapter, signed with GPU key  │
│    [3] hf/publication         ← HuggingFace adapter, signed with HF  │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

No single entity says "trust me." N independent entities each prove their piece.

## AdapterAttestation Schema

```json
{
  "adapter": "forge-alloy/humaneval",
  "version": "1.0.0",
  "domain": "benchmark:humaneval",
  "result": {
    "passing": 63,
    "total": 85,
    "score": 74.1,
    "harnessHash": "sha256:abc123..."
  },
  "adapterHash": "sha256:def456...",
  "signature": {
    "algorithm": "ES256",
    "publicKey": "MFkwEwYH...",
    "value": "MEUCIQD...",
    "keyId": "forge-alloy/humaneval-001",
    "keyRegistry": "https://keys.forge-alloy.dev"
  },
  "nonce": "dGhpcyBpcyBhIG5vbmNl",
  "sourceRepo": "https://github.com/CambrianTech/forge-alloy",
  "commit": "abc123def456",
  "attestedAt": "2026-03-31T12:00:00Z"
}
```

## Why This Encourages Open Source

The trust equation is simple:

```
Closed-source adapter:  Trust the org's word  →  Low trust
Open-source adapter:    Audit the code yourself  →  Higher trust
```

An open-source adapter's code is at `sourceRepo` + `commit`. Anyone can:
1. Clone the repo at that commit
2. Hash the adapter binary → compare to `adapterHash`
3. Read exactly what tests ran and how
4. Verify the signature against the registry

A closed-source adapter can only say "trust us." An open-source adapter says "don't trust us — read the code." The verify page shows this distinction.

**The incentive**: models certified by open-source adapters get higher trust scores on the verify page. The community naturally gravitates toward auditable certifiers. Closed-source adapters aren't banned, but they're honestly shown as lower trust.

## Adapter Categories

| Domain | Example Adapters | What They Certify |
|--------|-----------------|------------------|
| **Benchmarks** | humaneval, mmlu, gsm8k, arc | Eval scores with nonce challenge |
| **Safety** | toxicity, bias, CSAM detection | Content safety compliance |
| **Hardware** | inference-perf, memory-profile | Performance on specific devices |
| **Publication** | huggingface, ipfs | Published weights match forged weights |
| **Compliance** | HIPAA, SOX, GDPR, export-control | Regulatory compliance |
| **Code audit** | source-review, dependency-scan | Code integrity and supply chain |
| **Data provenance** | dataset-verify, license-check | Training data integrity and licensing |

## The API Role: Verification Gate, Not Service

The forge-alloy API isn't a service — it's an **enforcement mechanism**. Its only job is to verify that claimed transformations are reproducible. You want to publish? Prove it. You want to deliver? Prove it. You want to claim a benchmark score? **The API replays it.**

### The Replay Contract

Every stage in the alloy carries its input hash (from the previous stage) and its output hash. The API's verification is simple:

```
For each stage:
  1. Take the claimed input_hash
  2. Re-execute the stage with the same parameters
  3. Hash the output
  4. Does output_hash match the claimed output_hash?
     YES → stage verified, proceed
     NO  → rejected, chain broken, attestation void
```

No trust. No review board. No human judgment. The replay IS the verification.

### Longevity Guarantee

Each stage's data must remain available for the NEXT stage to verify against. This is the contract:

- You claim `output_hash: sha256:abc` for your prune stage
- The train stage's `input_hash` must be `sha256:abc`
- If you can't produce the data that hashes to `sha256:abc` for replay, your attestation is void
- The chain demands the data. Delete your inputs after claiming an output = broken chain = rejected

This is how the API **forces adherence**. If your source code complies with the alloy spec, compliance is mathematically proven through replay. Not audited. Not reviewed. Proven.

### Compliant Source Code = Proven Source Code

The alloy spec defines what stages are required and what each stage must produce. If your forge runner implements the spec:

1. Each stage hashes its input before execution
2. Each stage hashes its output after execution
3. Each hash is recorded in the alloy
4. The API can replay any stage and verify the hashes match

A compliant runner CANNOT produce a fraudulent alloy — the math prevents it. The spec IS the enforcement. The API IS the judge. The replay IS the proof.

### Matchmaking and Witnessing

Beyond enforcement, the API coordinates the certification process:

1. **Before forge**: API issues nonces for each adapter that will run
2. **During forge**: SDK invokes adapters at the right pipeline points
3. **After each adapter**: API receives and countersigns the adapter's attestation
4. **After forge**: API registers the complete alloy in the public log

```
Forge Runner                 forge-alloy API              Adapter
───────────                  ───────────────              ───────
Start forge ──────────────→  Issue nonces ──────────────→ Receive nonce
Execute pipeline
                             ← eval stage ──────────────→ Run eval with nonce
                                                          Sign results
                             ← receive attestation ←──── Return signed cert
                             Countersign ──────────────→ Stored
Finish forge
Write alloy with certs ────→ Register in public log
```

The API countersignature adds a second independent witness: "I saw this adapter run with this nonce at this time." The adapter's signature proves it ran. The API's countersignature proves it wasn't replayed.

## SDK Integration Points

The SDK wraps each pipeline stage and invokes the appropriate adapter:

```python
from forge_alloy import ForgeAlloy, ForgeSDK

sdk = ForgeSDK(api_key="...")  # Optional — works without for self-attested
alloy = ForgeAlloy.from_file("recipe.alloy.json")

# SDK hashes base model at load, compares to HF published hash
model = sdk.load_model(alloy.source)

# SDK wraps each stage, emitting checkpoints
for stage in alloy.stages:
    sdk.execute_stage(stage, model)

# SDK invokes eval adapters with API-issued nonces
results = sdk.evaluate(model, alloy.stages)

# SDK signs and registers
executed = sdk.finalize(alloy, model, results)
```

Without the SDK, everything still works — but certifications[] is empty and the verify page shows "self-attested" for every element. The SDK is the path to higher trust.

## Becoming a Certifier

Anyone can build an adapter:

1. Fork the adapter template (`forge-alloy/adapter-template`)
2. Implement the `AdapterInterface`:
   ```python
   class MyAdapter:
       def domain(self) -> str: ...
       def run(self, model_path: str, nonce: str) -> dict: ...
       def sign(self, result: dict, nonce: str) -> AdapterAttestation: ...
   ```
3. Register your public key at `keys.forge-alloy.dev`
4. Submit PR to `forge-alloy/adapter-registry` for review
5. Once approved, your adapter is available to all forge runners

**The bar for approval**: your adapter must be open source, deterministic, and your key must be registered. That's it. forge-alloy doesn't gatekeep what you certify — it provides the framework for provable, independent certification.

## Trust Composition

The verify page composes trust from all certifications:

```
Model with 0 certifications:  "Self-attested — all claims are self-reported"
Model with 3 certifications:  "3 independent certifications — eval witnessed, hardware tested, published verified"
Model with UL certification:  "UL safety certified — regulatory compliance verified"
Model with enclave + certs:   "Enclave-proven with 5 independent certifications — highest trust"
```

More certifications = more trust. Open-source certifications = higher trust than closed-source. API-witnessed certifications = higher trust than local-only.

The market decides what certifications matter. forge-alloy provides the slots.

## The Repository "Passkey"

A participating repository's identity in the chain is simple:

```
sourceRepo: "https://github.com/cambriantech/sentinel-ai"
commit: "abc123def456"
binaryHash: "sha256:..."
```

GitHub is the authority. The commit hash is the content-addressed proof. The binary hash catches local modifications. No additional crypto ceremony needed — GitHub's word is the trust anchor for code identity.

The only time you need device-bound keys is when you don't trust GitHub: air-gapped environments, self-hosted git, enclave tier. For everything else, GitHub is the CA.

## References

- [ATTESTATION.md](ATTESTATION.md) — Cryptographic attestation model
- [ECOSYSTEM.md](ECOSYSTEM.md) — Beyond model forging
- [APPLICATIONS.md](APPLICATIONS.md) — Use cases
