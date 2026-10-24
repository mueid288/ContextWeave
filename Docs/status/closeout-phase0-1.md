# Closeout — Phase 0 / 1 research (2026-10-24)

## Verdicts

| Gate / hyp | Result |
|---|---|
| G0 demand | **Provisional PASS** (synthetic + own corpus; no partner trace) |
| G1 CacheBlend quality-preserving ≥15% | **CLOSED** for vLLM 0.18 + lmcache 0.4.2 + shims @12k (quality 0.67 when engaged; ~1.10×) — **not** “CacheBlend fails” |
| G1 EPIC@12k latency | **PASS** |
| G1 EPIC multi-fact quality | **PASS (order-blind)** — superseded by oracle for reorder quality |
| G2 oracle upside vs best fixed | **FAIL** — C3 faster (~2–4×) but q=0.70 vs 1.0; fallback to C0 → no p95 upside (N=20) |
| H3 order / slice transfer / keydev | **FAIL** |
| H4 default 450 TFLOP cost model | **MISSPECIFIED, superseded** |
| H4 MFU band (peak 312 × 40–65%) | **Consistent with prior — not a validation** (~177–182 TFLOP/s; C0-only) |
| FP planner / poison / fault | **PASS — implementation conformance (self-authored)**; not security |

## Shipped policy

**C1** if exact prefix, else **C0** (≈ default serving).  
Non-prefix only with FR-13 provenance + matching build-context hash + quality clear
(keydev / exact-distro slice-cal). C4 quality-refused. Phase 2 / ResolventKV **closed**.

## What was learned

Non-prefix reuse can be fast (EPIC) but quality risk is not predicted by cheap
static or isolated-KV signals across golds/filler. Default 450 TFLOP/s was above
peak; measured C0 ~57–58% of 312 is consistent with a wide MFU band, not a
calibrated cost model. Validity/fingerprint refuses work as implemented
(conformance only). Literature vs harness quality gap unresolved.

## Writeup

`Docs/Reports/phase01-negative-results.md`

## Default next

**Archive / stay paused.** Resume only with an explicitly new thesis + pre-reg
(stopping rule R6). Do not reopen H3 predictors or misspecified H4.
