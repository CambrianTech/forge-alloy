# The Model Compiler — forge-alloy as a Programming Language for Model Optimization

**Status**: Architecture. The unifying abstraction.

forge-alloy is not a configuration format. It's a **compiler for neural networks**. The recipe is the source code. The search algorithm is the optimizer. The benchmark is the test suite. The GGUF is the compiled binary. The attestation is the build manifest.

---

## The Analogy (it's not a metaphor — it's literal)

| Traditional Compiler | Model Compiler |
|---|---|
| Source code (C, Rust) | forge-alloy recipe |
| Target architecture (x86, ARM) | Target hardware (5090 32GB, 3090 24GB) |
| Optimization level (-O0, -O2, -Os) | Search strategy (binary, RANSAC, adaptive) |
| Compiler passes (parse, optimize, codegen) | Forge stages (profile, prune, quant, eval) |
| Test suite (unit tests, integration tests) | Benchmarks (HumanEval, MMLU, PPL) |
| Binary output (.exe, .so) | GGUF output (.gguf) |
| Build manifest (checksums, deps) | Attestation chain (hashes, provenance) |
| Compiler flags (-march=native) | Device targets, quant levels, domain |
| Link-time optimization (LTO) | Compensation LoRA (post-prune recovery) |
| Dead code elimination | Dead expert elimination |
| Profile-guided optimization (PGO) | Calibration-corpus-guided pruning |

**Dead code elimination IS dead expert elimination.** The compiler removes functions that are never called. The forge removes experts that are never activated. Same optimization, different domain.

**Profile-guided optimization IS calibration-aware pruning.** GCC's PGO instruments the binary, runs a workload, then optimizes hot paths. Our forge profiles the model on a calibration corpus, then prunes cold experts. Same technique, different domain.

---

## The Language

### Source (the recipe)

```
forge mixtral-8x22b-coding {
    source: "mistralai/Mixtral-8x22B-Instruct-v0.1"
    
    target {
        devices: [rtx-5090-32gb, rtx-3090-24gb]
        domain: coding
        benchmark: humaneval >= 0.65
    }
    
    calibration: "humaneval + python-stdlib"
    
    search: auto    // compiler picks the strategy
}
```

That's the entire program. Everything else is derived:
- The search algorithm explores the prune/quant space
- The calibration corpus determines which experts survive
- The benchmark determines pass/fail
- The device target determines the size constraint
- The output is the best GGUF that meets ALL constraints

### Compilation Phases

```
                    ┌─────────────────────────────┐
                    │     forge-alloy recipe       │
                    │     (source code)            │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
         Phase 0   │  PARSE                       │
                   │  Validate recipe, resolve     │
                   │  source model, check deps     │
                   └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
         Phase 1   │  PROFILE (PGO)               │  ← calibration corpus
                   │  Run corpus through model,    │     determines what's "hot"
                   │  measure expert activations   │
                   │  Output: importance.json      │
                   └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
         Phase 2   │  SEARCH (optimizer)           │  ← finds the best config
                   │                               │
                   │  for each candidate:          │
                   │    size_filter → estimate →    │
                   │    quick_eval → rank           │
                   │                               │
                   │  Output: optimal (prune, quant)│
                   └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
         Phase 3   │  PRUNE (dead code elim)       │  ← remove cold experts
                   │  Per-layer adaptive pruning    │
                   │  based on importance profile   │
                   │  Output: pruned safetensors    │
                   └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
         Phase 4   │  QUANT (codegen)              │  ← target-specific output
                   │  Quantize to target format     │
                   │  Q4_K_M, Q3_K_M, etc.         │
                   │  Output: .gguf binary          │
                   └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
         Phase 5   │  EVAL (test suite)            │  ← verify correctness
                   │  Full benchmark eval           │
                   │  Compare against acceptance    │
                   │  Output: pass/fail + metrics   │
                   └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
         Phase 6   │  LINK (optional)              │  ← compensation LoRA
        (LTO)      │  Post-prune KL distillation   │
                   │  Recover lost quality          │
                   │  Output: patched .gguf         │
                   └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
         Phase 7   │  PACKAGE (ship)               │  ← publish + attest
                   │  Model card from results       │
                   │  Attestation chain              │
                   │  Upload to HuggingFace         │
                   │  Output: published model       │
                   └─────────────────────────────┘
```

### The Search Phase (the optimizer)

The search phase IS the optimization pass. It explores the space of valid configurations and finds the best one. The search is fast because it uses progressive precision:

```
Precision cascade:
  
  ┌─────────────────────────────────┐
  │ SIZE FILTER (instant, 0% error) │  ← eliminates 70-95% of candidates
  │ Pure math: params × bits ≤ VRAM │
  └────────────┬────────────────────┘
               │ survivors
  ┌────────────▼────────────────────┐
  │ ESTIMATE (instant, ±20% error)  │  ← ranks survivors by predicted quality
  │ Interpolate from known forges   │
  └────────────┬────────────────────┘
               │ top 3
  ┌────────────▼────────────────────┐
  │ QUICK EVAL (2 min, ±0.4 error)  │  ← 10 benchmark chunks
  │ SE = σ/√n — statistically sound │
  └────────────┬────────────────────┘
               │ best candidate
  ┌────────────▼────────────────────┐
  │ FULL EVAL (40 min, ±0.09 error) │  ← 162 chunks, precise
  │ Only the WINNER gets this       │
  └─────────────────────────────────┘

  Total time: ~45 minutes for optimal config
  Brute force: ~21 hours
  Speedup: ~28×
```

The error bars from each phase determine whether to promote, eliminate, or refine:

```
quick_ppl - SE > gate  →  ELIMINATE (definitely fails, don't waste time)
quick_ppl + SE < gate  →  PROMOTE (definitely passes, run full eval)
otherwise              →  REFINE (uncertain — run more chunks to tighten SE)
```

Statistical decision theory. Buy precision (more chunks) only when the decision is uncertain. Don't buy precision on obvious outcomes.

### Per-Layer Adaptive Pruning (the smart optimization)

Uniform pruning (8→6 everywhere) is `-O1`. Adaptive pruning (different per layer) is `-O2`:

```
Uniform (8→6):
  Every layer keeps 6 experts. Simple. Safe. Suboptimal.

Adaptive (per-layer):
  Layer 0:  keep 7 (all experts contribute evenly)
  Layer 14: keep 5 (wide spread — two experts dominate)
  Layer 29: keep 4 (17.6x spread — one expert handles everything)
  Layer 42: keep 7 (even activation pattern)
  
  Result: fewer total params for the SAME quality
  Or: same total params with BETTER quality
```

The importance JSON has the data. The pruner already supports per-layer keep counts. We just need the search to explore per-layer configurations, not just uniform cuts.

### Domain Specialization (target-specific compilation)

Different calibration corpus = different dead code analysis = different model:

```
forge mixtral-8x22b-coding { calibration: "humaneval" }
  → Prose experts are "dead code" → cut aggressively
  → Coding experts are "hot" → preserved
  → Result: smaller model, excellent at code, weak at prose

forge mixtral-8x22b-math { calibration: "gsm8k + math" }
  → Code experts are "dead code" → cut aggressively
  → Math/reasoning experts are "hot" → preserved
  → Result: smaller model, excellent at math, weak at code

forge mixtral-8x22b-general { calibration: "wikitext + code + math" }
  → No experts are dead → can't cut much
  → Result: larger model, good at everything
```

Same source model. Same compiler. Different target domain. The calibration corpus IS the target specification. `-march=coding` vs `-march=math` vs `-march=general`.

---

## Cross-Family Grafting (link-time optimization across libraries)

The next frontier. Different model families trained different experts on different data. Their experts are SPECIALISTS in different domains:

```
Mixtral experts:  strong at French, European languages, prose
Qwen experts:     strong at Chinese, code, multilingual
DeepSeek experts: strong at math, reasoning, long-context
```

Cross-family grafting: take the best expert from each family for each domain, combine into one model. Like linking libraries from different vendors:

```
libprose.so     → Mixtral expert 3
libcode.so      → Qwen expert 7
libmath.so      → DeepSeek expert 2
libreasoning.so → DeepSeek expert 5
```

Requirements:
- Compatible hidden dimensions (or learned projection layers)
- Router fine-tuning (teach the router to dispatch to foreign experts)
- The Many-Worlds substrate provides the shared representation space

This is the ultimate product of the model compiler: CHIMERA models that no single training run could produce. Best-of-breed experts assembled from across the open-source ecosystem.

---

## The Grid Accelerates the Compiler

The search phase parallelizes across the grid. 10 GPUs = 10× faster search:

```
BigMama (5090):     evaluating candidate A... PPL ≈ 8.2  ✓
Friend's 4090:      evaluating candidate B... PPL ≈ 9.1  ✓
Tokyo node (A100):  evaluating candidate C... PPL ≈ 11.3 ✗
Berlin node (3090): evaluating candidate D... PPL ≈ 8.8  ✓

All four in 2 minutes. Not 8.
```

The grid doesn't ship models — it ships RECIPES (3KB). Each node has the source model cached (from HuggingFace). The recipe tells each node what to prune, quantize, and evaluate. Results stream back as grid events. The Factory widget shows the search converging in real time.

---

## What We Ship

```
1. The compiler itself:
   forge-alloy + search algorithm + pruner + quantizer + evaluator
   Open source. AGPL. Anyone can run it.

2. The recipe library:
   Pre-tested recipes for popular models × domains × hardware
   Community-contributed, attested, reproducible.

3. The compiled models:
   Published on HuggingFace with full attestation.
   "This model was compiled from [source] for [domain] on [hardware]
    using recipe [hash]. Reproduce it yourself."

4. The grid:
   Distributed compilation across the mesh.
   Submit a recipe, the grid finds the optimal model for your hardware.
```

---

## The Pitch

**"gcc turns C into binaries. We turn neural networks into models that run on YOUR hardware."**

Nobody writes assembly anymore. Nobody should manually prune and quantize models either. The compiler does it. You specify what you want (domain, hardware, quality bar). The compiler finds the optimal model. Attested. Reproducible. Published.

The weights are already good enough. Pandora's box is open. What's missing is the compiler that turns frontier weights into models that run on the hardware people actually have. That's us.

---

## See Also

- [FORGE-SEARCH.md](FORGE-SEARCH.md) — the search algorithm (optimizer phase)
- [GRID-TRANSPORT-INTERFACES.md](GRID-TRANSPORT-INTERFACES.md) — grid acceleration
- [Many-Worlds §V.6.6](../../continuum/docs/papers/MANY-WORLDS-ABSTRACT.md) — forge-alloy as a language
- [PROGRESSIVE-ATTESTATION.md](../../sentinel-ai/docs/PROGRESSIVE-ATTESTATION.md) — build manifest
