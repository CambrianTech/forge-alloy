# ForgeAlloy Attestation Model

Cryptographic integrity for model forging pipelines. Proves what code ran, on what data, in what environment — and that nobody tampered with any of it.

## Why This Matters

AI model benchmarks are trivially spoofable today. Anyone can claim any score. There's no standard way to verify:
- Was the eval actually run, or were the numbers fabricated?
- Was the benchmark dataset modified to make the model score higher?
- Was the evaluation code patched to skip hard cases?
- Is this model actually the one that was evaluated, or was a better model swapped in?

ForgeAlloy attestation solves this by binding cryptographic proof to every claim.

## Architecture

Modeled after **FIDO2/WebAuthn attestation** — the same framework used for passwordless authentication. The pattern is proven at global scale (billions of passkeys deployed).

### The Attestation Chain

```
┌─────────────────────────────────────────────────────┐
│                  IntegrityAttestation                │
│                                                     │
│  trustLevel: "self-attested" | "verified" | "enclave"│
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  CodeAttestation                             │    │
│  │  runner: "sentinel-ai/forge_model"           │    │
│  │  version: "0.9.2"                            │    │
│  │  binaryHash: sha256(runner binary)           │    │
│  │  sourceHash: sha256(source repo)             │    │
│  │  commit: "09bb60f"                           │    │
│  │  environmentHash: sha256(container image)    │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  modelHash: sha256(model weights)                   │
│  alloyHash: sha256(alloy pipeline definition)       │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  DatasetAttestation[] (one per benchmark)    │    │
│  │  name: "humaneval"                           │    │
│  │  hash: sha256(dataset files)                 │    │
│  │  source: "https://github.com/openai/..."     │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  AttestationSignature (ES256)                │    │
│  │  algorithm: "ES256" (P-256 + SHA-256)        │    │
│  │  publicKey: base64url(EC public key)         │    │
│  │  value: base64url(signature)                 │    │
│  │  credentialId: "passkey-abc123" (optional)   │    │
│  │  keyRegistry: "https://keys.forge-alloy.dev" │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  attestedAt: "2026-03-28T14:32:00Z"                 │
└─────────────────────────────────────────────────────┘
```

### What Gets Hashed

The signature covers a canonical JSON payload containing ALL hashes:

```json
{
  "modelHash": "sha256:...",
  "alloyHash": "sha256:...",
  "codeHash": "sha256:...",
  "datasetHashes": ["sha256:...", "sha256:..."],
  "benchmarkResults": { ... },
  "attestedAt": "2026-03-28T14:32:00Z"
}
```

`signature.value = ES256(SHA-256(canonical_json))`

Anyone with the public key can verify: if any hash doesn't match, the signature breaks.

## Trust Tiers

Inspired by WebAuthn attestation types:

| Tier | WebAuthn Analog | What It Proves | Verification |
|------|----------------|---------------|-------------|
| **self-attested** | Self attestation | Signer vouches for itself | Check public key against registry |
| **verified** | Basic attestation | Third-party audited the runner | Verify certificate chain |
| **enclave** | AttCA / TPM | Hardware-bound, tamper-proof execution | Hardware attestation certificate |

### Self-Attested (Starting Point)

The forge runner generates its own keypair and signs results. Trust comes from the public key being registered in a known registry (like a JSON file on GitHub or HuggingFace).

```
Runner generates ES256 keypair → registers public key → signs results
Verifier fetches public key from registry → verifies signature
```

This prevents casual fraud (can't claim someone else's results) but doesn't prevent a compromised runner from lying.

### Verified (Production)

A third party (e.g., a CI system, an auditor) verifies the runner code matches its claimed hash before allowing it to sign. The verifier issues a certificate that chains to a known CA.

```
Auditor hashes runner binary → issues certificate → runner signs with certified key
Verifier checks certificate chain → trusts the CA → trusts the results
```

### Enclave (Maximum Trust)

The evaluation runs inside a TEE (Trusted Execution Environment) like Intel SGX, ARM TrustZone, or AWS Nitro Enclaves. The hardware itself attests that the code running inside is genuine and unmodified.

```
Runner executes inside TEE → hardware generates attestation → signs with hardware-bound key
Verifier checks hardware attestation certificate → code provably unmodified → results provably genuine
```

## Signing Algorithm: ES256

**ECDSA with P-256 and SHA-256** — the same algorithm used by WebAuthn/FIDO2, Apple's Secure Enclave, and most modern authentication systems.

- **Why not RSA?** Smaller keys (32 bytes vs 256+ bytes), faster verification, modern standard.
- **Why not Ed25519?** P-256 has broader hardware support (every passkey, every Secure Enclave, every HSM). Ed25519 is great but less universal for hardware attestation.
- **Why not blockchain?** Expensive, slow, overkill. Signed attestations with a public key registry achieve the same integrity guarantees without the overhead. If immutable anchoring is needed later, batch-publish Merkle roots.

## Key Registry

Public keys are published at a well-known URL so anyone can verify signatures without trusting a blockchain or centralized authority.

```
https://keys.forge-alloy.dev/v1/{key-id}.json

{
  "keyId": "continuum-ai/forge-runner-001",
  "algorithm": "ES256",
  "publicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...",
  "owner": "continuum-ai",
  "registeredAt": "2026-03-01T00:00:00Z",
  "revokedAt": null
}
```

Initially this can be a JSON file in the forge-alloy repo itself. Later, a proper hosted registry with revocation support.

## Self-Verification (OpenSSL FIPS Pattern)

Before signing anything, the forge runner verifies its own integrity:

```python
# 1. Hash own binary/source
own_hash = sha256(open(sys.argv[0], 'rb').read())

# 2. Compare to expected hash (compiled in or fetched from registry)
if own_hash != EXPECTED_HASH:
    raise IntegrityError("Runner binary has been modified")

# 3. Hash benchmark datasets
for dataset in datasets:
    actual_hash = sha256_dir(dataset.path)
    if actual_hash != dataset.expected_hash:
        raise IntegrityError(f"Dataset {dataset.name} has been modified")

# 4. Only THEN proceed with evaluation and signing
results = run_benchmarks(model, datasets)
attestation = sign_attestation(results, private_key)
```

This is the "check yourself before you wreck yourself" pattern from FIPS-validated crypto modules. The code validates its own integrity before performing security-critical operations.

## Marketplace Integration

The attestation chain enables a trustworthy compute marketplace:

```
1. User submits alloy.json (forge recipe)
2. Factory node executes the pipeline
3. Node signs results with its registered key
4. Marketplace verifies:
   - Signature is valid (ES256 check)
   - Public key is registered (registry lookup)
   - Code hash matches known runner version (code attestation)
   - Dataset hashes match canonical versions (dataset attestation)
   - Model hash matches the published weights (model attestation)
5. Payment released (proof of genuine work)
```

Nobody gets paid for compute they didn't do. Nobody gets credit for benchmarks they didn't run. Nobody can swap in a better model and claim the training improved it.

## Anti-Exploitation

The attestation model prevents several classes of exploitation:

| Attack | Prevention |
|--------|-----------|
| **Fabricated benchmarks** | Signature binds results to model hash — can't claim scores for a different model |
| **Modified eval code** | Code attestation includes binary hash — modified runner produces wrong hash |
| **Cherry-picked datasets** | Dataset attestation includes file hash — modified data produces wrong hash |
| **Model swap** | Model hash is signed — can't substitute a better model post-eval |
| **Replay attacks** | Timestamp + model hash + alloy hash = unique per evaluation |
| **Sybil (fake nodes)** | Key registry with registration requirements — can't generate unlimited identities |
| **Mathematical exploitation** | Deterministic eval harness + dataset hashing — can't game the math |

## Implementation Phases

### Phase 1: Self-Attested (Now)
- Forge runner hashes itself, model, datasets
- Signs with self-generated ES256 key
- Public key in forge-alloy repo as JSON
- Verifiable but trust-on-first-use

### Phase 2: Passkey-Based Signing
- Runner uses WebAuthn credential (passkey) for signing
- Hardware-bound key (Secure Enclave, TPM) — can't be exported
- `credentialId` field links to the WebAuthn credential
- Joel's day job expertise directly applies here

### Phase 3: Verified Runners
- CI/CD pipeline builds runner from audited source
- Build system issues certificate for the binary hash
- Certificate chain verifiable by anyone
- Third-party audit trail

### Phase 4: Enclave Execution
- Benchmark evaluation runs in TEE (Nitro Enclaves, SGX)
- Hardware attestation proves code integrity
- Maximum trust — results are provably from unmodified code on unmodified data
- Required for high-stakes marketplace transactions

## Relation to Persona/LoRA Attestation

The same attestation model applies to:

- **LoRA adapters**: prove training data, base model, training code, resulting adapter weights
- **Persona genomes**: prove the lineage of adapter combinations (which adapters, which order, which merge)
- **Marketplace work**: prove GPU compute was actually performed (proof of work without blockchain waste)
- **Model lineage**: `sourceAlloyId` chain becomes a certificate chain — each link signed

The `IntegrityAttestation` struct is designed to be reusable across all these contexts. The same ES256 signing, the same key registry, the same trust tiers.

## References

- [WebAuthn Attestation](https://www.w3.org/TR/webauthn-3/#sctn-attestation) — W3C specification
- [FIDO2 Attestation Types](https://fidoalliance.org/specs/fido-v2.1-ps-20210615/fido-v2.1-ps-20210615.html#sctn-attestation-types) — FIDO Alliance
- [FIPS 140-3 Self-Tests](https://csrc.nist.gov/pubs/fips/140-3/final) — NIST module integrity verification
- [AWS Nitro Enclaves](https://aws.amazon.com/ec2/nitro/nitro-enclaves/) — TEE for confidential computing
