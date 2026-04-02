# Forge Targets — Strategic Model Pipeline

Last updated: 2026-04-02

What to forge, why, and in what order. Models are selected for: popularity (existing audience), forge potential (what we can improve), and device reach (what hardware they unlock).

## Currently Forging

| Model | Status | What |
|-------|--------|------|
| qwen3.5-4b-code-128k-pruned | Running on BigMama | 25% entropy prune of our 128K model, 3 cycles |

## Published

| Model | HF Repo | Highlights |
|-------|---------|------------|
| qwen3.5-4b-code-128k-forged | continuum-ai/qwen3.5-4b-code-128k-forged | 128K context (4x), +18.7% ppl, 32.3% HumanEval |
| qwen3.5-4b-code-forged | continuum-ai/qwen3.5-4b-code-forged | Original code forge |

---

## Tier 1: High Confidence (proven pipeline, known architecture)

### Qwen3.5-9B — THE viral target
- **Source**: Qwen/Qwen3.5-9B (4.77M downloads, 1,135 likes)
- **Forge**: 128K context extend + 25% prune + code domain training
- **Result**: ~7B effective params, 128K context, code-specialized
- **Device**: MacBook Pro 32GB fp16, MacBook Air 16GB Q8, Air 8GB Q4
- **Headline**: "9B coding model with 128K context, runs on MacBook"
- **Why**: Biggest Qwen3.5 that fits 5090 for full LoRA. Sweet spot between capability and deployability. Massive existing audience.
- **Risk**: Low — same dense Qwen3.5 arch as our 4B, pipeline proven

### Qwen3.5-4B variants (what we're already doing)
- **128K + pruned** — running now
- **Future**: different domains (reasoning, math, creative writing)
- **Future**: aggressive prune (40-50%) for iPhone-class deployment
- **Risk**: None — pipeline validated

### Qwen3.5-0.8B — Phone model
- **Source**: Qwen/Qwen3.5-0.8B (2.05M downloads, 466 likes)
- **Forge**: Max context extend + code domain
- **Result**: ~873M params, huge context, code-focused
- **Device**: iPhone, Android, Raspberry Pi, any edge device
- **Headline**: "128K context coding assistant on your phone"
- **Why**: 466 likes for a sub-1B model = people want tiny models. Nobody has context-extended one.
- **Risk**: Low — tiny model, fast to forge, quick iteration

---

## Tier 2: High Value, Needs Validation

### Qwen3.5-35B-A3B (MoE) — Expert pruning showcase
- **Source**: Qwen/Qwen3.5-35B-A3B (3.07M downloads, 1,309 likes — highest of any 3.5)
- **Forge**: Expert pruning after code domain training. Remove unused MoE experts.
- **Result**: Potentially 20-25B total (still 3B active), much smaller on disk
- **Device**: MacBook Pro 32GB at Q4, possibly Air 16GB
- **Headline**: "36B model expert-pruned to run on your laptop"
- **Why**: 1,309 likes. MoE expert pruning is our ExpertPruneExecutor's debut.
- **Risk**: MEDIUM — ExpertPruneExecutor is a stub. Need to implement `cpu_expert_prune.py` first. MoE training on 5090 may need QLoRA (36B total params). Unknown how many experts can be pruned without quality loss.
- **Prerequisite**: Implement ExpertPruneExecutor

### Qwen3-VL-8B — Vision model
- **Source**: Qwen/Qwen3-VL-8B-Instruct (4.4M downloads, 849 likes)
- **Forge**: Domain-specialize for code/UI screenshots, technical diagrams
- **Result**: Vision model that understands code, UI layouts, architecture diagrams
- **Device**: MacBook Pro 32GB fp16
- **Headline**: "Vision model that reads your entire codebase visually"
- **Why**: Nobody has forged a vision model. Feeds our VisionDescriptionService.
- **Risk**: HIGH — VL architecture is different (visual encoder + LLM). Our pipeline handles text-only LLMs. ModalityExecutor is a stub. Training data needs to be image+text pairs, not just code text. Don't know if LoRA on the LLM portion works without breaking the vision encoder.
- **Prerequisite**: Understand VL architecture, test LoRA on LLM-only portion, find/create code screenshot training data

### Qwen3-VL-4B — Smaller vision
- Same as above but 4B. Easier to experiment with.
- **Risk**: Same as VL-8B but faster to iterate
- **Try this first** before committing to 8B

---

## Tier 3: Sensory Pipeline (small, fast, high utility)

### Qwen3-ASR-1.7B — Speech to text
- **Source**: Qwen/Qwen3-ASR-1.7B (1.19M downloads, 642 likes)
- **Forge**: Domain-specialize for technical/programming vocabulary
- **Result**: STT that understands "kubectl", "async await", "refactor the middleware"
- **Device**: Any (1.7B is tiny)
- **Why**: Personas need ears. Technical vocabulary is a real pain point for STT.
- **Risk**: MEDIUM — ASR architecture is encoder-decoder, not autoregressive LLM. Different training pipeline. Need audio+transcript pairs for code/tech domain.
- **Prerequisite**: Understand ASR training, find/create tech vocabulary audio dataset

### Qwen3-TTS-1.7B-VoiceDesign — Text to speech
- **Source**: Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign (642K downloads, 310 likes)
- **Forge**: Create unique persona voices
- **Result**: Each persona gets a distinctive voice
- **Device**: Any
- **Why**: Personas need mouths. Unique voices = personality.
- **Risk**: MEDIUM — TTS training is different from LLM training. Voice cloning needs target audio samples.

### Qwen3-Embedding-0.6B — RAG embeddings
- **Source**: Qwen/Qwen3-Embedding-0.6B (5.62M downloads, 956 likes)
- **Forge**: Fine-tune on our domain data (code, architecture docs, API specs)
- **Result**: Better retrieval for persona RAG pipeline
- **Device**: Any (596M is trivial)
- **Why**: 5.6M downloads. Better embeddings = better persona context = better answers.
- **Risk**: LOW — embedding fine-tuning is well-understood. Contrastive learning on domain pairs.
- **Prerequisite**: Create domain-specific positive/negative pairs from our codebase

---

## Tier 4: When Qwen3.6-Plus Weights Drop

### Qwen3.6-Plus — Opus-tier forge
- **Source**: Not yet released (API-only as of 2026-04-02)
- **Benchmarks**: Matches Opus 4.5 on Terminal-Bench (61.6 vs 59.3), SWE-bench, Claw Eval
- **Forge**: Context extend + prune + code domain. The full pipeline.
- **Result**: Opus-quality coding at consumer hardware scale
- **Headline**: "Opus-tier code generation, 6GB, runs on MacBook Air"
- **Why**: This is THE forge target if/when weights release. 95% of Opus, fully controllable.
- **Risk**: Unknown model size. If it's 70B+, needs multi-GPU or aggressive quantized training. May be months before open weights (if ever).
- **Watch**: Alibaba's release cadence — Qwen3.5 weights came ~2 weeks after announcement

---

## Forge Pipeline Readiness

| Capability | Status | Models That Need It |
|------------|--------|---------------------|
| Context extend (YaRN) | ✅ Working | All LLMs |
| Entropy pruning (heads) | ✅ Working | All dense LLMs |
| LoRA training | ✅ Working | All LLMs |
| HumanEval benchmark | ✅ Working | Code models |
| publish_model.py | ✅ Working | All |
| alloy_to_card.py | ✅ Working | All |
| Expert pruning (MoE) | ❌ Stub | 35B-A3B, 122B-A10B |
| Vision LoRA | ❌ Unknown | VL-4B, VL-8B |
| ASR fine-tuning | ❌ Not built | ASR-1.7B |
| TTS voice cloning | ❌ Not built | TTS-1.7B |
| Embedding fine-tuning | ❌ Not built | Embedding-0.6B |
| Multi-GPU training | ❌ Not needed yet | 27B+, 3.6-Plus |

## Decision Framework

**For each target, ask:**
1. Does our pipeline support it TODAY? (If no, what's missing?)
2. How many downloads does the base model have? (Audience exists?)
3. What device tier does the forged model unlock?
4. What's the headline? (If you can't write it in one sentence, skip it)
5. Has anyone else done this? (Novelty = attention)

**Priority = confidence × impact × novelty**

The 9B is high confidence, high impact, high novelty. Do it next.
The VL models are high impact but unknown confidence. Experiment with VL-4B first.
The sensory models are medium impact but open up persona capabilities nobody else has.
