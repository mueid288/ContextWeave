# ResolventKV → ContextWeave: what we adopt now

**Source:** [`Foundational AI Technology Research.md`](Foundational%20AI%20Technology%20Research.md)  
**Date:** 2026-10-20  
**Rule:** Adopt *insights and evaluation contracts* into Phase 0/1. Do **not** implement ResolventKV kernels until Gate G1 shows existing methods leave a measurable gap.

---

## Plain English (what the research claims)

Prefix cache fails when the same docs appear in new orders. Pasting isolated chunk caches (**PIC** — position-independent caching) often breaks multi-document reasoning because later chunks never “saw” earlier ones (**causal closure** — every token’s KV must reflect the true preceding context).

**ResolventKV** (hypothesis) would fix that with a small spectral math update instead of re-running the model. ContextWeave’s *current* plan still tries **existing** repairs first (CacheBlend, EPIC, SAFE-KV-style suffix recompute). ResolventKV is a **candidate Phase 2 mechanism** if those leave a real gap.

---

## Adopt into ContextWeave **now** (no new GPU code)

| Insight from research | How we use it |
|---|---|
| **SAFE-KV causal-closure contract** | G1/G2 quality bar: composed reuse must report *answer preservation vs full prefill*, not only TTFT |
| **ATTUNER: routing > values** | Phase 1 ablations may separate attention-score mismatch from value mismatch; don’t assume “KV looks fine ⇒ quality fine” |
| **Irminsul first-chunk / sink carve-out** | Keep system/sink prefix on **exact prefix cache**; only non-prefix docs enter chunk cache (already Mode A + FR-02 boundaries) |
| **Provenance-bound cache keys** | Already FR-01/13 fingerprints — reinforce: hash content **and** model/tokenizer/RoPE/build-context (never token-ids alone) |
| **Receiver-necessity dissociation** | Prefer multi-hop / private-fact style evals (HotpotQA, 2Wiki, MuSiQue) where the model *must* read the docs; avoid “GSM8K alone” as the only quality proof |
| **Depth-split intuition (CoMem/EncBank)** | Optional Phase 1 note: upper layers matter more for cross-chunk errors (SpecCache) — not a build task yet |
| **Prior-art kill list** | Do **not** chase MLA-only Δ-RoPE, Koopman constant-memory, or cross-family latent KV bridges as the core wedge |
| **Falsification bar (for ResolventKV later)** | If first-order spectral repair needs suffix recompute on >~20% of requests, or answer preservation stays low on 2Wiki — drop or redesign |

## Defer until **after G1**

- SCSP / spiked SVD packets, Frechet JVP susceptibilities, Neumann resolvent sweep, fused Triton lift kernels  
- Claiming novelty / renaming the product to ResolventKV  
- Training-based cousins (ATTUNER LoRA, KV Packet wrappers) as the *primary* path (MVP stays training-free)

## Gate mapping

```text
G0 (done, provisional)  → demand for non-prefix recurrence
G1 (next, GPU)          → reproduce prefix + CacheBlend + EPIC;
                          measure answer preservation on multi-hop
G2                      → is there upside vs best fixed config?
                          if yes AND token-recompute is the bottleneck
                          → open ResolventKV as a Phase 2 prototype track
```

## Smoke / baseline hardware note

Research protocol used **L40S 48 GB** (SAFE-KV latency bed). Our smoke pick **RTX A6000 48 GB** is in the same class — keep Qwen3-8B / Qwen2.5-7B-Instruct as first models.
