# Closeout — Phase 0 / 1 research (2026-10-24)

## Verdicts

| Gate / hyp | Result |
|---|---|
| G0 demand | **PASS** |
| G1 CacheBlend quality-preserving ≥15% | **FAIL / CLOSED** |
| G1 EPIC@12k latency + easy multi-fact | **PASS** |
| G2 oracle upside vs best fixed | **FAIL** |
| H3 order / slice transfer / keydev | **FAIL** |
| H4 default 450 TFLOP cost model | **FAIL** (~60% vs C0) |
| FP planner provenance gate | **PASS** (desk) |
| FP build-context poison suite | **PASS** (desk) |
| FR fault-injection suite | **PASS** (desk) |

## Shipped policy

**C1** if exact prefix, else **C0**.  
Non-prefix only with FR-13 provenance + matching build-context hash + quality clear
(keydev / exact-distro slice-cal). C4 quality-refused. Phase 2 / ResolventKV **closed**.

## What was learned

Non-prefix reuse can be fast (EPIC) but quality risk is not predicted by cheap
static or isolated-KV signals across golds/filler. Default cost-model TFLOP
assumptions are not measured TTFT. Validity/fingerprint refuses work as designed.

## Default next

**Archive / stay paused.** Resume only with an explicitly new thesis + pre-reg.
