# Forge Search — Finding Optimal Models Algorithmically

**Status**: Design. The automated forge optimization algorithm.

## The Problem

Given a source model, target devices, and a quality gate, find the best configuration that:
1. **Fits** every target device (VRAM constraint)
2. **Passes** the quality benchmark (PPL, pass@1, etc.)
3. **Maximizes** quality within constraints (best PPL that fits)

## The Search Space

For an MoE model with N experts per layer:

```
Prune:  keep N, N-1, N-2, ... ceil(N/2) experts  (N/2 options)
Quant:  Q2_K, Q3_K_S, Q3_K_M, Q4_K_S, Q4_K_M, Q5_K_M, Q6_K, Q8_0, F16
        (9 options)

Mixtral 8x7B:   4 prune × 9 quant = 36 combinations
Mixtral 8x22B:  4 prune × 9 quant = 36 combinations
Qwen3 128-expert: ~10 prune × 9 quant = 90 combinations
```

Small enough to reason about. Too many for full eval (each takes 30-40 min).

## Phase 1: Size Filter (instant, eliminates ~70% of candidates)

Model size is deterministic — no eval needed.

```
size_gb(params_b, quant) = params_b × bits_per_param(quant) / 8

bits_per_param:
  F16    = 16.0
  Q8_0   = 8.5
  Q6_K   = 6.5
  Q5_K_M = 5.5
  Q4_K_M = 4.85
  Q4_K_S = 4.5
  Q3_K_M = 3.9
  Q3_K_S = 3.5
  Q2_K   = 3.35

params_after_prune(total_params, total_experts, kept_experts) =
  non_expert_params + expert_params × (kept_experts / total_experts)
```

For each target device, eliminate every combination where `size_gb > vram_gb`.

**Example: Mixtral 8x22B on RTX 5090 (32GB)**

```
8→8 (141B): Q4_K_M=82GB ❌, Q3_K_M=66GB ❌, Q2_K=57GB ❌  — all eliminated
8→7 (123B): Q4_K_M=72GB ❌, Q3_K_M=58GB ❌, Q2_K=50GB ❌  — all eliminated
8→6 (105B): Q4_K_M=61GB ❌, Q3_K_M=49GB ❌, Q2_K=42GB ❌  — all eliminated
8→5 ( 88B): Q4_K_M=51GB ❌, Q3_K_M=41GB ❌, Q2_K=35GB ❌  — all eliminated
8→4 ( 70B): Q4_K_M=41GB ❌, Q3_K_M=33GB ✅, Q3_K_S=30GB ✅, Q2_K=28GB ✅

Survivors: 3 out of 36 combinations (92% eliminated)
```

## Phase 2: Quality Estimation (instant, ranks survivors)

PPL degrades predictably with compression. Two factors:
- **Pruning degradation**: roughly linear with fraction removed
- **Quantization degradation**: known offsets per quant level

From empirical data:
```
Mixtral 8x7B:
  8→6 (25% cut) + Q4_K_M: PPL 8.97 (baseline 8.14, Δ +10.2%)

Mixtral 8x22B:
  8→4 (50% cut) + Q4_K_M: PPL 12.04 (baseline 7.81, Δ +54%)

Derived model:
  prune_degradation ≈ baseline × (fraction_removed ^ 1.5) × k
  quant_degradation ≈ known offset per quant tier (Q3 adds ~0.3-0.5 over Q4)
```

Rank survivors by estimated PPL. Best estimated quality first.

## Phase 3: Quick Eval (2 min each, validates estimates)

Run `llama-perplexity --chunks 10` on top candidates. 10 chunks instead of 162.
Gives PPL ± 0.5 in ~2 minutes.

```
Candidate 1: 8→4, Q3_K_M (33GB) → quick eval → PPL ≈ 12.5
Candidate 2: 8→4, Q3_K_S (30GB) → quick eval → PPL ≈ 13.1
Candidate 3: 8→4, Q2_K  (28GB) → quick eval → PPL ≈ 15.2

Quality gate: PPL < 10.0
All fail → "No config meets constraints"
Quality gate: PPL < 13.0
Candidate 1 passes → full eval
```

## Phase 4: Full Eval (30-40 min, final validation)

Run full `llama-perplexity` (162 chunks) on the best candidate from Phase 3.
This is the number that goes on the model card. Full precision, fully attested.

## Total Time

```
Phase 1: Size filter    →  instant    (math only)
Phase 2: Quality estimate → instant   (lookup + interpolation)
Phase 3: Quick eval      →  2-6 min   (1-3 candidates × 2 min)
Phase 4: Full eval       →  30-40 min (1 candidate)
                            ─────────
Total:                      ~35-45 min for the OPTIMAL config

vs. brute force:            36 × 35 min = 21 hours
```

## The Algorithm

```python
def forge_search(
    source_model: str,
    target_devices: list[Device],
    quality_gate: QualityGate,
    importance_json: str,  # from profiling (already computed)
) -> ForgeResult:
    
    # Phase 1: enumerate and size-filter
    candidates = []
    for keep_experts in range(total_experts, total_experts // 2 - 1, -1):
        for quant in QUANT_LEVELS:
            size = estimate_size(source_model, keep_experts, quant)
            fits_all = all(size <= dev.vram_gb for dev in target_devices)
            if fits_all:
                est_ppl = estimate_ppl(source_model, keep_experts, quant)
                candidates.append((keep_experts, quant, size, est_ppl))
    
    if not candidates:
        return ForgeResult.no_fit(
            f"No config fits all targets. "
            f"Smallest possible: {min_possible_size}GB. "
            f"Smallest target: {min(d.vram_gb for d in target_devices)}GB."
        )
    
    # Phase 2: sort by estimated quality (best first)
    candidates.sort(key=lambda c: c[3])  # sort by est_ppl ascending
    
    # Phase 3: quick eval top candidates
    quick_results = []
    for keep, quant, size, est_ppl in candidates[:3]:
        # Prune if not already pruned at this level
        pruned_dir = prune_if_needed(source_model, keep, importance_json)
        gguf_path = quantize(pruned_dir, quant)
        ppl = quick_eval(gguf_path, chunks=10)
        quick_results.append((keep, quant, size, ppl, gguf_path))
        
        # Early termination: if this passes the gate, don't eval worse candidates
        if quality_gate.passes(ppl, tolerance=0.5):
            break
    
    # Phase 4: full eval on best passing candidate
    best = min(quick_results, key=lambda r: r[3])
    if quality_gate.passes(best[3], tolerance=0.5):
        final_ppl = full_eval(best[4])
        if quality_gate.passes(final_ppl):
            return ForgeResult.success(
                keep_experts=best[0],
                quant=best[1],
                size_gb=best[2],
                ppl=final_ppl,
            )
    
    # No candidate passed
    return ForgeResult.no_pass(
        f"Best achievable: PPL {best[3]:.2f} "
        f"(gate requires < {quality_gate.max_ppl}). "
        f"Try: compensation LoRA, or a different source model."
    )
```

## Prune Caching

The profiling (importance JSON) is computed ONCE. Different prune levels reuse it:
- 8→6: keep top 6 experts per layer (from same importance ranking)
- 8→5: keep top 5
- 8→4: keep top 4

One profiling run → multiple prune variants. Each prune is a separate shard rewrite (~20 min) but they all use the same importance data.

The search can try multiple prune levels efficiently:
```
Profile:    60 min (once)
Prune 8→6:  20 min
Prune 8→5:  20 min  
Prune 8→4:  20 min (already done for 8x22B)
Quick eval:  2 min each
Full eval:  35 min (best candidate only)
```

Total for trying 3 prune levels: ~100 min. Much better than 21 hours brute force.

## Compensation LoRA (Optional Phase 5)

If the best candidate is CLOSE to the quality gate but doesn't pass:

```
Best: PPL 10.5 (gate: < 10.0) — 0.5 points short

→ Run 500-step KL-distillation LoRA against the teacher
→ Typical recovery: 1-2 PPL points
→ Re-eval: PPL 9.3 → passes gate ✅
```

The search algorithm can decide whether compensation LoRA is worth trying:
```python
if best_ppl < quality_gate.max_ppl * 1.2:  # within 20% of gate
    # Close enough — LoRA might push it over
    lora_result = run_compensation_lora(best)
    if quality_gate.passes(lora_result.ppl):
        return ForgeResult.success_with_lora(...)
```

## Alloy Recipe

```json
{
  "name": "optimal-8x22b-for-5090",
  "searchStrategy": {
    "method": "binary",
    "quickEvalChunks": 10,
    "maxCandidates": 3,
    "tryCompensationLora": true,
    "loraStepsIfNeeded": 500
  },
  "acceptanceCriteria": {
    "perplexity": { "max": 10.0 },
    "size": { "maxGb": 32 }
  },
  "source": {
    "baseModel": "mistralai/Mixtral-8x22B-Instruct-v0.1"
  }
}
```

The alloy says WHAT you want. The search finds HOW to get it.

## Factory Widget Integration

The forge console shows the search live:

```
┌─ Forge Search ───────────────────────────────────────┐
│                                                       │
│  Source: Mixtral 8x22B (141B, 8 experts)             │
│  Target: RTX 5090 (32GB)                             │
│  Gate:   PPL < 10.0                                  │
│                                                       │
│  Phase 1: Size filter          36 → 3 candidates     │
│  Phase 2: Quality estimate     ranked by est. PPL    │
│  Phase 3: Quick eval                                  │
│    🔄 8→4 Q3_K_M (33GB)       PPL ≈ 12.5  🔴 FAIL  │
│    ⬜ 8→4 Q3_K_S (30GB)       est. ~13               │
│    ⬜ 8→4 Q2_K  (28GB)        est. ~15               │
│                                                       │
│  ❌ No config meets PPL < 10.0 on 32GB               │
│  💡 Recommendation: Use Mixtral 8x7B instead         │
│     (PPL 8.97, 20GB, fits with headroom)             │
│                                                       │
└───────────────────────────────────────────────────────┘
```

The Factory widget (existing tab) shows this in real time. Each quick eval updates the table. The user watches the search converge.
