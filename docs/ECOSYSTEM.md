# ForgeAlloy Ecosystem — Beyond Model Forging

The alloy contract pattern is universal. Model forging is the first application. The same structure — define work, execute, attest, compensate — applies to every creative and computational contribution in the ecosystem.

## The Pattern

```
Work Order (alloy)  →  Execute (grid)  →  Attest (proof)  →  Compensate (marketplace)
```

This pattern works for:

| Work Type | Who Does It | What the Contract Defines | What Gets Attested |
|-----------|-------------|--------------------------|-------------------|
| **Model forging** | GPU nodes | Stages: prune, train, quant, eval | Model hash, benchmark scores, hardware verified |
| **Universe design** | Human artists | Assets: 3D models, shaders, sounds, layouts | Asset hashes, render previews, adoption metrics |
| **LoRA training** | Academy nodes | Curriculum, dataset, epochs, evaluation | Adapter hash, exam scores, training lineage |
| **Benchmark evaluation** | Eval nodes | Which benchmarks, which model, passing threshold | Dataset hashes, result hashes, execution environment |
| **Inference serving** | Grid nodes | Model, concurrency, latency SLA | Uptime, latency percentiles, request count |
| **Data curation** | Humans + AI | Dataset selection, cleaning, labeling | Dataset hash, quality metrics, provenance |

## Compensation

The attestation IS the invoice. The contract defines the work. The executed contract proves it was done. The marketplace settles payment.

- **GPU nodes** get paid for forge compute (measured in stage-minutes)
- **Universe designers** get paid for adoption (measured in active citizens)
- **Academy trainers** get paid for successful training (measured in exam scores)
- **Eval nodes** get paid for benchmark execution (measured in benchmarks completed)
- **Data curators** get paid for quality data (measured in downstream model improvement)

No intermediary decides the price. The contract is public. The attestation is verifiable. Supply and demand set the rate. The grid is the marketplace.

## Reputation IS Verification Rate

No voting. No reviews. No stars. Your reputation is derived from one thing: **can your attestation chains be replayed right now?**

```
Node A: 99.8% chains verifiable, 500 completed forges  →  premium rate
Node B: 94.0% chains verifiable, 50 completed forges   →  market rate
Node C: 80.0% chains verifiable, 10 completed forges   →  discount or no work
```

The verification endpoint IS the rating system. One mechanism, not two. The grid checks your chains, computes your percentage, routes work accordingly. Reliable nodes get more work, earn more, get even more work. Unreliable nodes fade unless they fix their storage.

**New nodes** start with no history — they take lower-paying jobs to build reputation, just like a new eBay seller. Transaction count + verification rate = trust score. Buyers filter: "only nodes >99% verification, >100 completed forges."

**Pricing follows trust.** A 5090 with 80% reliability is worth less than a 4090 with 99.9%. Hardware specs set the ceiling. Reputation sets the actual rate. The market decides — no authority sets prices.

**The incentive is self-enforcing:**
- Lose data → chain breaks → visible to everyone immediately
- Not "we might get audited someday" — your models show UNVERIFIABLE right now
- Nobody needs to be told to back up their data — the consequence of losing it is instant and public
- HuggingFace, node operators, grid participants all have their own incentive to maintain their piece of the chain

## Humans Thrive

The ecosystem is designed so humans and AI both contribute value and both get compensated:

- **Artists** design universes — the Warcraft blacksmith forge, the Tron light-cycle factory
- **Curators** select and clean training data — the fuel for forging
- **Architects** design forge pipelines — the recipes that produce the best models
- **Operators** run grid nodes — the hardware that executes the work
- **Teachers** design academy curricula — the programs that train personas
- **Researchers** discover new techniques — the algorithms that improve forging

Every contribution is trackable, attestable, and compensable through the same contract pattern. The creative work of designing a universe is as valued as the computational work of forging a model.

## The Alternative

The current AI economy concentrates value in a few companies that control the models, the compute, and the distribution. Users are products. Creators are uncompensated. Hardware is rented, never owned.

ForgeAlloy enables a different economy:
- **Own your hardware** — your GPU is your factory, not rented cloud
- **Own your models** — forged on your hardware, attested by your keys
- **Own your data** — training data stays local, attestation proves it was used correctly
- **Own your work** — every contribution has a verifiable contract and fair compensation
- **Own your world** — the universe you design is yours to share and profit from

The contract is the trust layer. The grid is the marketplace. The attestation is the proof. No single entity controls the value chain.
