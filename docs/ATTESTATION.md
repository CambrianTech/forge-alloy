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

## Passkey Signing (Phase 2 — Gap Identified)

WebAuthn credentials sign `clientDataJSON` (which includes a relying party challenge), **NOT** arbitrary payloads. Standard passkeys bind the key to the RP ID.

To use passkeys for forge attestation:
1. **Hacky but works**: Embed attestation hash in the WebAuthn challenge field
2. **Proper but complex**: Use a signing service that holds the Secure Enclave key and signs on behalf of the credential
3. **Alternative**: Use the platform's raw key access (Apple CryptoKit on macOS/iOS gives direct Secure Enclave access outside WebAuthn)

The `credentialId` field links to a WebAuthn credential. The signing mechanism bridges the gap.

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

**Registration authority:** Initially the forge-alloy repo maintainers (anyone with write access). Phase 3 introduces certificate-based registration where an auditor must sign the key before it's accepted.

## Replay Prevention

- **nonce**: Verifier-provided random bytes (like WebAuthn challenge). Required for marketplace. The marketplace issues a nonce before forge begins — the nonce is included in the signed payload.
- **audience**: Binds the attestation to a specific verifier. An attestation for marketplace A is invalid on marketplace B.
- **timestamp**: `attestedAt` provides ordering but NOT freshness. A replayed attestation from a year ago is still valid without nonce/audience checks.

## Dataset Hashing Specification

Dataset hash must be deterministic and cover exactly the subset used:

1. List all files in the dataset directory
2. Sort filenames lexicographically
3. For each file: SHA-256(contents)
4. Combine via Merkle tree (sorted leaves)
5. Record the root hash, plus the number of items evaluated

If a subset was used (e.g., MMLU-Pro subset of MMLU), the hash covers ONLY the subset files, not the full dataset. The `name` field reflects the subset.

## Known Limitations (Not Solvable by Attestation)

| Attack | Status | Notes |
|--------|--------|-------|
| **Training on test set** | Out of scope | The biggest benchmark fraud. Attestation proves eval integrity, not training integrity. |
| **Cherry-picking best of N** | Mitigated by nonce | Without verifier nonce, attacker runs N times, signs best. With nonce, only one attempt per challenge. |
| **Eval harness gaming** | Out of scope | Model specifically trained to overfit on eval set — ML problem, not crypto problem. |
| **Hardware profile fabrication** | Partial | Hardware profiles are in results but not inside the signed attestation scope. Future: include in signed payload. |

## Implementation Phases

### Phase 1: Self-Attested (Now)
- Runner hashes itself, model, datasets
- Records hashes in attestation (no signature yet)
- Honest: prevents accidental corruption only
- Public key infrastructure not required

### Phase 2: Signed Self-Attestation
- ES256 signing with self-generated keys
- Key registry (JSON in repo, then hosted)
- RFC 8785 canonical payload
- Verifier implementation in all three languages

### Phase 3: Verified Runners
- CI/CD builds runner from audited source
- Auditor issues certificate for binary hash
- Certificate chain in signature
- Registration authority for key approval

### Phase 4: Enclave Execution (Required for Marketplace)
- TEE: AWS Nitro Enclaves, Intel SGX, ARM TrustZone
- Hardware attestation proves code integrity
- Nonce from marketplace for freshness
- The ONLY tier that prevents all identified attacks
- Required before real money flows through the system

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
