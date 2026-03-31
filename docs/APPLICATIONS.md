# ForgeAlloy Applications — Beyond ML

The alloy contract pattern is general purpose. ML model forging is the first application. The same infrastructure — typed stages, cryptographic attestation, chain of custody, Merkle history, QR verification — applies to any workflow that needs provenance and trust.

## Content Authenticity (The Deepfake Killer)

Camera with hardware enclave signs the raw photo at capture time. Every edit is a tracked delta:

```
Capture (enclave-signed by camera TEE)       → sha256:abc  [root of trust]
  ↓
Crop + color correct (Photoshop API)         → sha256:def  delta: crop(10,20,800,600) + levels(+5)
  ↓
Add watermark (Lightroom)                    → sha256:ghi  delta: overlay(watermark.png, pos:bottom-right)
  ↓
Publish to Twitter                           → sha256:ghi  (unmodified from step 3)
```

Scan the QR on the photo → full edit history. The chain answers every question:

| Question | Answer from the chain |
|----------|----------------------|
| Is this AI generated? | Chain starts with generation model, not camera enclave |
| Was it altered? | Every edit listed with exact parameters |
| Is it unaltered? | Camera hash matches published hash — zero deltas |
| Who took it? | Camera's hardware key, linked to photographer's identity |
| When? | Enclave-attested timestamp, not file metadata |
| What tool edited it? | Each delta records the software + version |

Same pattern as C2PA/Content Credentials but decentralized, extensible, and built on proven attestation infrastructure. No central authority needed. The camera's enclave is the root of trust. The Merkle chain is the proof. The QR is the access point.

### Steganographic Embedding

The alloy hash can be embedded steganographically in the image itself — invisible to the eye but extractable by verification tools. The image IS its own proof. No external database needed. Even if the QR is cropped, the embedded hash survives.

## Physical Manufacturing

An Etsy producer, a factory floor, a supply chain:

```
Design (CAD file, v3)                        → sha256:abc
  ↓
Manufacture (3D print, silver, 80% infill)   → sha256:def  [attested by printer hardware]
  ↓
Quality check (weight: 12.3g, photos: 4)     → sha256:ghi
  ↓
Publish (Etsy listing + Shopify)             → sha256:jkl
  ↓
Ship (USPS, tracking: 9400...)               → sha256:mno
  ↓
Deliver (signed by recipient)                → sha256:pqr
```

QR on the package → scan → full provenance. The buyer verifies without trusting the seller. The attestation proves the photos match the product. The manufacturing parameters are recorded. Returns are traceable.

## Commodities & Futures

The alloy maps directly to commodities contract language:

| Alloy Concept | Commodities Equivalent |
|---------------|----------------------|
| Source | Raw material specification |
| Target | Delivery specification |
| Stages | Processing/refining steps |
| Attestation | Quality certification |
| Trust anchor | Exchange settlement |
| QR | Bill of lading |

## Pharmaceutical / Regulated Manufacturing

Chain of custody for drug manufacturing, FDA compliance:

```
Compound (raw materials, lot numbers)        → sha256:abc  [attested by facility]
  ↓
Synthesize (reactor temp, duration, yield)   → sha256:def
  ↓
Quality test (purity: 99.7%, contaminants)   → sha256:ghi  [enclave-attested lab equipment]
  ↓
Package (lot: XY-2026-0331, expiry: 2028)   → sha256:jkl
  ↓
Distribute (cold chain verified, GPS track)  → sha256:mno
```

FDA audit = verify the chain. Every step attested. Every parameter recorded. The alloy IS the batch record.

## Creative Work & IP

Music production, film editing, software development:

```
Record (studio session, 24-bit/96kHz)        → sha256:abc  [hardware-attested audio interface]
  ↓
Mix (Pro Tools, 47 tracks, master bus EQ)    → sha256:def
  ↓
Master (LUFS: -14, true peak: -1dB)          → sha256:ghi
  ↓
Publish (Spotify + Apple Music + Bandcamp)   → sha256:jkl
```

Proves: this song was recorded by these musicians, mixed by this engineer, mastered to these specs. Copyright disputes resolved by the chain — who created what, when, with what tools.

## The Pattern

Every application follows the same structure:

```
Source (what you start with)
  → Target (what you want)
  → Stages (the work to get there)
  → Attestation (proof it happened)
  → Delivery (where it goes)
  → QR (how anyone verifies)
```

ML forging is the first dictionary. The infrastructure is universal.
