# ForgeAlloy Attestation Model

Cryptographic integrity for model forging pipelines. Proves what code ran, on what data, in what environment — and signs the whole chain.

## Why This Matters

AI model benchmarks are trivially spoofable. Anyone can claim any score. There's no standard way to verify that an eval was actually run, that the data wasn't modified, or that the model is the one that was evaluated.

## Architecture

Modeled after **FIDO2/WebAuthn attestation**. Proven at global scale (billions of passkeys deployed).

### The Attestation Chain

```
IntegrityAttestation
├── trustLevel: self-attested | verified | enclave
├── code: CodeAttestation
│   ├── runner + version + binaryHash
│   ├── sourceHash + commit
│   └── environment + environmentHash
├── modelHash: SHA-256(FULL model weights — every byte)
├── alloyHash: SHA-256(pipeline definition)
├── datasets[]: DatasetAttestation
│   ├── name + version + hash
│   └── source URL
├── nonce: verifier-provided challenge (replay prevention)
├── audience: who this is for (cross-marketplace binding)
├── signature: AttestationSignature
│   ├── algorithm: ES256 | ES384 | EdDSA | ML-DSA-65 | ML-DSA-87 | SLH-DSA-128s
│   ├── publicKey (MUST verify against registry, not trust directly)
│   ├── value: sign(SHA-256(JCS-canonical payload))
│   ├── keyId (registry lookup + revocation)
│   └── certificateChain (for verified tier)
└── attestedAt: ISO 8601
```

## Trust Tiers

| Tier | WebAuthn Analog | What It Proves | Limitations |
|------|----------------|---------------|-------------|
| **self-attested** | Self attestation | Prevents accidental corruption | **Does NOT prevent adversarial modification.** A compromised runner can fake this. |
| **verified** | Basic/AttCA | Third-party audited the runner | Requires trust in the auditor's certificate chain |
| **enclave** | TPM/hardware | TEE execution, hardware-bound | **Only tier that prevents input-output binding attacks.** Required for marketplace. |

### Honest Limitations of Self-Attestation

Self-attestation means the signer vouches for itself. This is the "who watches the watchmen" problem:
- A compromised runner can patch the self-check to return the expected hash
- The code attestation records what hash was computed, but a modified script computes its own (different) hash truthfully
- FIPS modules solve this because the hash is verified by the OS loader or hardware root of trust, not by the code itself

**Self-attestation is useful for:**
- Preventing accidental corruption (wrong version deployed)
- Audit trails (what code was running when)
- Stepping stone to verified/enclave tiers

**Self-attestation does NOT prevent:**
- A malicious runner forging attestations
- Running correct code to get real results, then substituting better results
- Cherry-picking the best of N evaluation runs

**The real fix is enclave execution (Phase 4)**, where hardware guarantees code integrity.

## Canonicalization: RFC 8785 (JCS)

The signed payload MUST use **RFC 8785 JSON Canonicalization Scheme (JCS)**:
- Deterministic key ordering (lexicographic)
- No whitespace
- Specific number formatting
- Specific Unicode normalization

Without this, the same payload produces different SHA-256 hashes across Rust, Python, and TypeScript — cross-language verification breaks.

The signed payload contains:
```json
{
  "alloyHash": "sha256:...",
  "attestedAt": "2026-03-28T14:32:00Z",
  "audience": "https://marketplace.forge-alloy.dev",
  "benchmarkResults": { ... },
  "codeHash": "sha256:...",
  "datasetHashes": ["sha256:...", "sha256:..."],
  "modelHash": "sha256:...",
  "nonce": "base64url-random-bytes"
}
```

`signature.value = ES256(SHA-256(JCS(payload)))`

## Signing Algorithms

| Algorithm | Type | Status | Use Case |
|-----------|------|--------|----------|
| **ES256** | ECDSA P-256 + SHA-256 | Production | Default. Universal hardware support (passkeys, Secure Enclave, TPM) |
| **ES384** | ECDSA P-384 + SHA-384 | Production | Higher security margin |
| **EdDSA** | Ed25519 | Production | Fast verification, less hardware support |
| **ML-DSA-65** | CRYSTALS-Dilithium (FIPS 204) | Future | Post-quantum lattice-based. Add when libraries stabilize. |
| **ML-DSA-87** | CRYSTALS-Dilithium (FIPS 204) | Future | Higher security post-quantum |
| **SLH-DSA-128s** | SPHINCS+ (FIPS 205) | Future | Hash-based post-quantum. Stateless, conservative choice. |

The algorithm enum is extensible. When quantum-safe standards mature, add new variants without breaking existing attestations.

## Hardware Key Signing (Phase 2)

WebAuthn credentials sign `clientDataJSON` (which includes a relying party challenge), NOT arbitrary payloads. Standard passkeys bind the key to the RP ID. But the underlying hardware keys are directly accessible:

**The real path — raw Secure Enclave / StrongBox access:**
- **macOS/iOS**: Apple's `SecKeyCreateSignature` with a Secure Enclave key gives ES256 signing of arbitrary data, no WebAuthn ceremony needed. The key is hardware-bound, non-exportable, Touch ID protected. This is the intended use of the hardware.
- **Android**: `KeyStore` with `setIsStrongBoxBacked(true)` — same properties, same direct signing of arbitrary data.
- **Windows**: TPM 2.0 via `NCryptSignHash` — hardware-bound ES256.

This isn't a workaround — it's the primary use case for hardware security modules. WebAuthn is one protocol that uses these keys; forge attestation is another. Same hardware, different ceremony.

The `credentialId` field can optionally link to a WebAuthn credential for cross-referencing, but the signing happens via the platform's native crypto API, not the WebAuthn ceremony.

## Key Registry

```json
{
  "keyId": "continuum-ai/forge-runner-001",
  "algorithm": "ES256",
  "publicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...",
  "owner": "continuum-ai",
  "registeredAt": "2026-03-01T00:00:00Z",
  "expiresAt": "2027-03-01T00:00:00Z",
  "revokedAt": null,
  "supersededBy": null,
  "registrationAuthority": "forge-alloy-maintainers"
}
```

**Critical verification requirement:** Verifiers MUST fetch the key from the registry and compare, NOT trust the `publicKey` embedded in the signature. A naive verifier using only the embedded key defeats the entire system.

**Revocation propagation:** Short-lived keys (90-day expiry) + registry polling. Verifiers cache keys with max-age matching the key's remaining validity. On revocation, verifiers see `revokedAt` on next cache refresh. For marketplace payments: hold funds for a grace period (24-48h) before release, allowing revocation to propagate.

**Superseded vs revoked:** Supersession is operational (key rotation), not a security event. A superseded key was valid when it signed — attestations signed before `supersededBy` was set MUST still verify. A revoked key was compromised — attestations signed by a revoked key SHOULD be treated as suspect regardless of when they were signed. Verifiers: check `revokedAt` first (reject if set), then check `supersededBy` (accept if attestation timestamp < supersession timestamp).

**Registration authority:** Initially the forge-alloy repo maintainers (anyone with write access). Phase 3 introduces certificate-based registration where an auditor must sign the key before it's accepted.

## Replay Prevention

- **nonce**: Verifier-provided random bytes (base64url, minimum 16 bytes). Required for marketplace. The marketplace issues a nonce before forge begins — the nonce is included in the signed payload.
- **audience**: A URI identifying who this attestation is for. MUST be the marketplace's canonical origin (e.g., `https://marketplace.forge-alloy.dev`). An attestation signed for marketplace A with `audience: "https://a.example.com"` MUST be rejected by marketplace B. Verifiers compare audience against their own origin — exact string match, no normalization.
- **timestamp**: `attestedAt` provides ordering but NOT freshness. A replayed attestation from a year ago is still valid without nonce/audience checks.

## Dataset Hashing Specification

Dataset hash must be deterministic and cover exactly the subset used:

1. List all files in the dataset directory
2. Sort filenames lexicographically
3. For each file: `leaf = SHA-256(0x00 || file_contents)` (leaf domain prefix)
4. Combine via Merkle tree: `node = SHA-256(0x01 || left || right)` (internal node domain prefix)
5. If odd number of leaves, promote the last leaf unpaired
6. Record the root hash, plus the number of items evaluated

**Domain separation (RFC 6962 pattern):** Without the `0x00`/`0x01` prefixes, a two-file dataset could produce the same root as a single file whose contents happen to be the concatenation of two leaf hashes. Prepending `0x00` for leaves and `0x01` for internal nodes makes this impossible.

If a subset was used (e.g., MMLU-Pro subset of MMLU), the hash covers ONLY the subset files, not the full dataset. The `name` field reflects the subset.

## Pipeline Lifecycle: Forge → Attest → Verify → Deliver → Anchor

The alloy is a full contract. The recipe is the work order, the executed alloy is the receipt, the attestation is the notarized proof. Each phase has its own trust guarantee and they compose.

```
FORGE (compute node)          DELIVER (any path)             ANCHOR (immutable)
─────────────────────         ──────────────────             ──────────────────
1. Load alloy recipe          4. Receive executed alloy      7. Hash attestation
2. Execute pipeline           5. VERIFY all hashes:          8. Publish to anchor:
   ├── prune                     ├── model weights match?       ├── blockchain tx
   ├── train (cycles)            ├── code hash match?           ├── Merkle batch
   ├── eval (benchmarks)         └── ABORT if mismatch          ├── RFC 3161 TSA
   └── generate samples       6. Deliver via ANY path:          └── IPFS pin
3. ATTEST:                       ├── HuggingFace upload      9. Record anchor in alloy
   ├── hash model (full)         ├── IPFS pin
   ├── hash code (runner)        ├── Grid transfer
   ├── hash datasets             ├── USB / local copy
   ├── sign (if Phase 2+)        ├── HTTP / S3 / torrent
   └── write executed alloy      └── literally anything
                                  (signature survives transport)
```

### Phase 1 (Now): Forge + Deliver

Forge produces hashes. Publish verifies hashes before upload. No signature. Trust: accidental corruption detection. Anyone can modify the alloy between forge and publish — the hash verification catches it.

### Phase 2: Forge + Sign + Deliver

Forge signs the attestation with hardware-bound key. Publish verifies signature AND hashes. Tampering between forge and publish breaks the signature. Trust: identity proven (who forged), integrity proven (what was forged).

### Phase 3: Forge + Sign + Deliver + Anchor

Same as Phase 2, plus the attestation is anchored to an immutable ledger. Trust: identity + integrity + existence (when it was forged, provably). Prevents backdating.

### Phase 4: Enclave Forge + Sign + Deliver + Anchor

Forge runs inside TEE. Hardware proves code integrity. Signature is hardware-bound. Anchor is immutable. Trust: complete. The ONLY phase where every claim is cryptographically proven from compute through delivery. Required for marketplace payments.

## Model Card Integrity

HuggingFace lets repo owners edit README.md. The card can claim anything. **The alloy is the source of truth, the card is a render.**

Protection:
1. **cardHash** — SHA-256 of the generated model card, stored in the alloy's PublishStage. If the card is edited after publish, the hash breaks.
2. **Verification tools** — Download the .alloy.json, recompute SHA-256 of the README.md, compare to cardHash. Mismatch = card was edited.
3. **The alloy file in the HF repo** — the contract. Anyone can download it and verify every claim independently.

The card is like a certificate printout — nice to look at, but the real proof is the signed document behind it. You wouldn't trust a photocopy of a diploma without checking with the university.

At enclave tier, the card is generated and hashed inside the TEE before upload. Maximum integrity.

## Known Limitations (Not Solvable by Attestation)

| Attack | Status | Notes |
|--------|--------|-------|
| **Training on test set** | Out of scope | The biggest benchmark fraud. Attestation proves eval integrity, not training integrity. |
| **Cherry-picking best of N** | Mitigated by nonce | Without verifier nonce, attacker runs N times, signs best. With nonce, only one attempt per challenge. |
| **Eval harness gaming** | Out of scope | Model specifically trained to overfit on eval set — ML problem, not crypto problem. |
| **Hardware profile fabrication** | Partial | Hardware profiles are in results but not inside the signed attestation scope. Future: include in signed payload. |

## Implementation Phases

### Phase 1: Unsigned Attestation (Now)
- Runner hashes itself, model, datasets
- Records hashes in attestation — **no signature**
- **Zero integrity guarantee** — anyone can modify the hashes after the fact
- Value: audit trail, accidental corruption detection, format validation
- Public key infrastructure not required

### Phase 2: Hardware-Key Signed Attestation
- ES256 signing via platform Secure Enclave / StrongBox / TPM
  - macOS: `SecKeyCreateSignature` (Touch ID protected, non-exportable)
  - Android: `KeyStore.setIsStrongBoxBacked(true)`
  - Windows: TPM 2.0 via `NCryptSignHash`
- Key registry (JSON in repo, then hosted)
- RFC 8785 JCS canonical payload
- Verifier implementation in all three languages
- Trust level: still `self-attested` — hardware key proves identity but not code integrity

### Phase 3: Verified Runners
- CI/CD builds runner from audited source
- Auditor issues certificate for binary hash
- Certificate chain in signature
- Registration authority for key approval
- Trust level: `verified`

### Phase 4: Enclave Execution (Required for Marketplace)
- Trust level: `enclave`
- The ONLY tier that prevents all identified attacks
- Required before real money flows through the system

**NVIDIA GPU TEE (primary target):**
- Blackwell architecture has TEE silicon — datacenter SKUs (B200, GB200) have full TEE-I/O today
- Consumer Blackwell (RTX 5090): TEE mode pending driver unlock (RTX PRO 6000 Server has it via R580 TRD1)
- NVIDIA Attestation Service (NRAS) provides remote attestation + Reference Integrity Manifests (RIM)
- SEC2 security component generates hardware attestation reports
- Integration: `certificateChain` carries NVIDIA's attestation certificate, `environmentHash` is the GPU firmware hash
- Ref: [NVIDIA Secure AI with Blackwell and Hopper](https://docs.nvidia.com/nvidia-secure-ai-with-blackwell-and-hopper-gpus-whitepaper.pdf)

**Other TEE options:**
- AWS Nitro Enclaves (cloud, available now)
- Intel SGX / TDX (broad CPU-side support)
- ARM TrustZone (mobile/embedded — phone-based attestation)
- Apple Secure Enclave (macOS/iOS — already used in Phase 2 for key signing)

### Phase 5: Post-Quantum Migration
- Monitor NIST PQC standard maturity (ML-DSA, SLH-DSA)
- Algorithm field already supports PQC variants
- Dual-sign (classical + PQC) during transition period
- No format changes needed — just new enum values

## References

- [RFC 8785 — JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785) — JCS
- [WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/) — W3C attestation model
- [FIDO2 Attestation Types](https://fidoalliance.org/specs/fido-v2.1-ps-20210615/fido-v2.1-ps-20210615.html#sctn-attestation-types)
- [FIPS 204 — ML-DSA](https://csrc.nist.gov/pubs/fips/204/final) — Post-quantum signatures (Dilithium)
- [FIPS 205 — SLH-DSA](https://csrc.nist.gov/pubs/fips/205/final) — Post-quantum signatures (SPHINCS+)
- [AWS Nitro Enclaves](https://aws.amazon.com/ec2/nitro/nitro-enclaves/) — TEE
