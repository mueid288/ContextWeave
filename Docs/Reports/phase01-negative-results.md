# ContextWeave Phase 0/1 — Scoped negative-results report

**Tag:** `v0.1.0-phase01-archive`  
**Date:** 2026-10-24  
**Scope:** Synthetic needle / multi-fact suites on Colab A100-40GB. Not a claim about
CacheBlend or EPIC in general, nor about real RAG traffic.

## 1. Setup and stacks

| Lane | Stack | Model | Scale |
|---|---|---|---|
| CacheBlend G1-DIAG | vLLM **0.18** + lmcache **0.4.2** in-process; **4 compat shims** (attention import, flashinfer sparse, `ConstantList` lookup, `get_input_embeddings` alias) | Qwen3-8B | ~12k chunk_sep |
| EPIC latency / quality / Phase1 | vLLM **0.7.0** + EPIC **LegoLink-8 Python overlay** (not authors’ full CUDA build) | Mistral-7B-Instruct-v0.2 | ~12k tokens |
| H3 / H4 | Banked EPIC A100 JSONL (CPU re-eval) | same | ~12k |
| FP suites | CPU unit / scripted cases | n/a | n/a |

Harness pitfalls (reusable): reorder self-hit pollution; Qwen3 thinking-token scorer traps; lmcache↔vLLM ABI mismatch; DIAG #1 artifacts lost (chat paste only — do not cite as primary); engagement must be measured (`retrieved`/`cached` tokens) before interpreting quality/latency.

## 2. Results (scoped)

| Item | Latency / engagement | Quality | N / seeds / orders | Label (corrected) |
|---|---|---|---|---|
| Native reorder gap | 4–24× slower vs prefix warm | answers OK | n≈10, several scales | **Strong** |
| CacheBlend (this config) | BAC cached **7705**/11520; CBA **~19**; mean TTFT **~1.10×** vs native miss | agree/contains **0.67** when engaged | Gate D bac; orders ABC/BAC/CBA | **Closed for this pin** — not “CacheBlend fails” |
| EPIC@12k latency | **3.84×** (city) | gold present | one case scale | **PASS** (latency) |
| EPIC multi-fact quality | 1.98–3.86× | contains **1.0/1.0** | **order-blind** (fixed chunk order) | **PASS order-blind; superseded by oracle** |
| Phase 1 oracle (G2) | C3 not better than C0 on p95 | C0 q **1.0**, C3 q **0.70** | **N=20**, orders permuted | **G2 FAIL** |
| H3 order / slice / keydev | — | predictors fail transfer | N=12–20; new filler seeds | **FAIL** (no transferable input-side predictor) |
| H4 @450 TFLOP/s | rel err ~0.60 | — | 4 banked suites | **MISSPECIFIED, superseded** |
| H4 MFU prior (peak 312, MFU 40–65%) | implied ~177–182 TFLOP/s ∈ [124.8, 202.8] | — | same banked C0 | **PASS** (desk) |
| FP poison / fault / planner gate | — | refuses as coded | 8/8, 7/7, unit | **Implementation conformance (self-authored)** |

## 3. What is unresolved

EPIC C3 mean quality 0.50–0.70 on simple single-fact lookups under reorder is worse than
typical published “quality-preserving” PIC framing. Candidate causes not ruled out:
overlay vs authors’ build; prompt layout / question placement / Mistral template;
chunk-boundary / position handling after reorder. Same flavor for CacheBlend (shims +
asymmetric BAC vs CBA engagement). Optional fidelity session: review **R4** only.

## 4. Cannot claim

- That CacheBlend or EPIC fail in general, or that quality loss is inherent to the methods vs this harness.
- That the cost model “fails” (old H4 was misspecified; MFU prior contains measured).
- That the provenance gate is secure (self-authored conformance only).
- That non-prefix reuse has no value on real RAG traffic (G0 never validated on partner traces).
- That the shipped planner improves on default serving beyond refusal hooks for a disabled C3 path (**C1 else C0** ≈ prefix-or-prefill).

## 5. Can claim (setup stated)

See `Docs/Reviews/claude_contextweave_post_archive_review.md` §3 and
`Docs/status/experiment-log.md` **Final verdict**. Archive decision and stopping rule (R6) remain: no new lane without a pre-reg that changes a decision, order+seed quality gates, and a hard GPU cap.
