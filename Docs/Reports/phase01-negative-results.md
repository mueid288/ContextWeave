# ContextWeave Phase 0/1 — Scoped negative-results report

**Archive:** tag `v0.1.1-phase01-full` / branch `archive/phase0-1-research`
(see [Docs/status/ARCHIVE.md](../status/ARCHIVE.md)).  
**Date:** 2026-10-24 (revised same day)  
**Scope:** Synthetic needle / multi-fact suites on Colab A100-40GB. Not a claim about
CacheBlend or EPIC in general, nor about real RAG traffic. Tombstone only on `main`.

## 1. Setup and stacks

| Lane | Stack | Model | Scale |
|---|---|---|---|
| Native reorder (early) | vLLM **0.32.0** (+ lmcache MP path where noted) | Qwen3-8B | ~6k–12k |
| CacheBlend G1-DIAG | vLLM **0.18** + lmcache **0.4.2** in-process; **4 compat shims** (attention import, flashinfer sparse, `ConstantList` lookup, `get_input_embeddings` alias) | Qwen3-8B | ~12k chunk_sep |
| EPIC latency / quality / Phase1 | vLLM **0.7.0** + EPIC **LegoLink-8 Python overlay** (not authors’ full CUDA build) | Mistral-7B-Instruct-v0.2 | ~12k tokens |
| H3 / H4 | Banked EPIC A100 JSONL (CPU re-eval) | same | ~12k |
| FP suites | CPU unit / scripted cases | n/a | n/a |

Harness pitfalls (reusable): reorder self-hit pollution; Qwen3 thinking-token scorer traps; lmcache↔vLLM ABI mismatch; DIAG #1 artifacts lost (chat paste only — do not cite as primary); engagement must be measured (`retrieved`/`cached` tokens) before interpreting quality/latency.

## 2. Results (scoped)

| Item | Latency / engagement | Quality | N / seeds / orders | Label (corrected) |
|---|---|---|---|---|
| Native reorder gap (vLLM **0.32**) | **1.25×** (early); **~2.57×** @~6k; **~3.8–4.7×** @~12k chunk_sep vs prefix warm | answers OK | n≈10 | **Strong** (this pin) |
| Native reorder gap (vLLM **0.18** DIAG) | warm_abc p50 **~39 ms** / reorder **~928 ms** → ratio **~24×** (very hot prefix; same-pin as CacheBlend below) | answers OK | n=10 | **Strong** (do not mix with 0.32 range) |
| CacheBlend (vLLM 0.18 + lmcache 0.4.2) | Gate R formal **FAIL**: cached **7705** vs bar **≥8063** (~66.9% of 11520). BAC cached **7705**; CBA **~19**. Per-order blend TTFT: BAC **~622 ms** (~1.5× vs native reorder **924**); CBA **~1065 ms** (miss). Mean blend_reorder/native_reorder **~1.10×** hides that **quality loss is on the fast order (BAC)** | Gate D **bac**: contains/agree **0.67** (**N=12**); Gate D abc **1.0** (N=12) | n=10 TTFT; orders ABC/BAC/CBA | **Closed for this pin** — not “CacheBlend fails” |
| EPIC@12k latency | **3.84×** (city) | gold present | one case scale | **PASS** (latency) |
| EPIC multi-fact quality | 1.98–3.86× | contains **1.0/1.0** | **order-blind** (fixed chunk order) | **PASS order-blind; superseded by oracle** |
| Phase 1 oracle (G2) | **C3 faster** (~2–4× TTFT) but q=**0.70** vs C0 **1.0**; oracle fallback to C0 → **no p95 upside** | C0 q **1.0**, C3 q **0.70** | **N=20**, orders permuted | **G2 FAIL** |
| H3 order / slice / keydev | — | predictors fail transfer | N=12–20; new filler seeds | **FAIL** (no transferable input-side predictor) |
| H4 @450 TFLOP/s | rel err ~0.60 | — | 4 banked suites | **MISSPECIFIED, superseded** |
| H4 MFU band (peak 312, MFU 40–65%) | implied ~177–182 TFLOP/s ∈ [124.8, 202.8] | — | same banked **C0 only** | **Consistent with an MFU prior — not a validation** (prior set after ~58% seen; wide band; ignores load/C3 break-even) |
| FP poison / fault / planner gate | — | refuses as coded | 8/8, 7/7, unit | **Implementation conformance (self-authored)** |

## 3. What is unresolved

EPIC C3 mean quality 0.50–0.70 on simple single-fact lookups under reorder is worse than
typical published “quality-preserving” PIC framing. Candidate causes not ruled out:
overlay vs authors’ build; prompt layout / question placement / Mistral template;
chunk-boundary / position handling after reorder. Same flavor for CacheBlend (shims +
asymmetric BAC vs CBA engagement).

Optional next (only if the quality discrepancy must be resolved): one capped GPU
session that runs the EPIC authors’ demo on this overlay, then the needle suite
with their prompt layout, and stops. Do not reopen CacheBlend, predictors, or
ResolventKV in that session.

## 4. Cannot claim

- That CacheBlend or EPIC fail in general, or that quality loss is inherent to the methods vs this harness.
- That the cost model is calibrated or “validated” (old H4 was misspecified; the MFU band check is consistency only).
- That the provenance gate is secure (self-authored conformance only).
- That non-prefix reuse has no value on real RAG traffic (G0 never validated on partner traces).
- That the shipped planner improves on default serving beyond refusal hooks for a disabled C3 path (**C1 else C0** ≈ prefix-or-prefill).

## 5. Can claim (setup stated)

- On A100-40GB, Qwen3-8B, vLLM **0.18** + lmcache **0.4.2** in-process blend at ~12k tokens (chunk_sep, four shims listed above): reorder reuse engaged partially (BAC **7705**/11520 tokens, CBA ~0); Gate R formal miss (7705 &lt; 8063); mean TTFT about **1.10×** vs native miss, with BAC ~**622 ms** and CBA ~**1065 ms**; Gate D bac quality **0.67** on **N=12**.
- On Mistral-7B with the EPIC LegoLink-8 Python overlay on vLLM **0.7.0** at ~12k tokens: TTFT **2–3.9×** vs full prefill; C3 mean quality **0.70** (N=20) and **0.50** (N=12) on synthetic needle tasks under reorder.
- Neither order nor (order, fact-type) predictors transferred across filler seeds in these suites.
- Harness lessons: self-hit pollution of reorder trials, scorer pitfalls with Qwen3 thinking output, version ABI mismatches between lmcache and vLLM, lost artifacts when sessions stop early.

## 6. Archive / stopping rule

Stay archived by default. No new lane unless: (1) a pre-registered question whose
answer changes a decision; (2) PIC quality gates permute chunk order and use at
least two filler seeds, with engagement measured; (3) at most one more GPU session
in total unless that fidelity check finds a harness bug.
