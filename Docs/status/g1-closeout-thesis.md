# G1 closeout — thesis restatement (measured)

**Date:** 2026-10-23 (updated after EPIC@12k)  
**Status:** CacheBlend G1 **CLOSED**; EPIC@12k latency **PASS**; multi-fact quality
**PASS** (city/year/code @12k).  
**Decision:** **Pivot** (not stop, not Phase 1 build). Per §6 in
`Docs/Reviews/claude_g1_remaining_gaps_fixes_recommendations.md`.

## What Phase 0 asked

| Gate | Question | Result |
|---|---|---|
| G0 | Enough recurring non-prefix context? | **PASS** — `my_corpus` ~76% working-set @ 128 GB |
| G1 | Reproduce Tier-1 PIC; quality-preserving ≥15% TTFT? | **CacheBlend: no** @12k. **EPIC: yes** on Mistral demo fork @12k (3 facts) |

## Measured facts (do not re-litigate without a new pre-reg)

1. **Prefix gap is real:** full vs shared-prefix TTFT ~**2.57×** @6k (G1 step 1).
2. **Reorder hurts prefix:** ~**1.25×** slower when docs reorder (G1 step 2b).
3. **CacheBlend can engage** (G1-DIAG #2): BAC cached **7705**; quality/latency fail policy.
4. **EPIC@12k:** prompt **12001**, LegoLink-8 **3.84×** vs full, gold contains
   (`artifacts/g1-epic-12k-2026-10-23/`). Dedicated EPIC fork — not CacheBlend pins.
5. **EPIC multi-fact quality:** city/year/code contains **1.0**; speedups **3.86× /
   2.19× / 1.98×** (`artifacts/g1-epic-quality-2026-10-23/`).

## Hypothesis status

| ID | Claim | After G1 |
|---|---|---|
| H1 | Enough non-prefix recurrence | **Supported** (G0) |
| H2 | No single fixed PIC config wins; selection helps | **Open** — CacheBlend fails; EPIC passes one slice; oracle/Phase 1 not started |
| H3/H4 | Risk signal / cost model | **Not tested** on GPU; cost model planning-only |
| ResolventKV | Beat CacheBlend with our kernels | **Blocked** — §6; prefer verifying EPIC quality breadth first |

## Product thesis (restated)

ContextWeave is a **validity-checked planner** over prefix, existing PIC methods, and
full prefill. On measured calibrations: **C1** when exact prefix; else **C3** (EPIC)
when non-prefix artifacts are valid; **C4** (CacheBlend) refused; else **C0**.

## Go / pivot / stop

| Option | When | Now |
|---|---|---|
| Go Phase 1 | G0∧G1 with durable Tier-1 win | **No** — needs explicit go memo (EPIC fork ≠ product runtime) |
| Pivot | Demand real; baselines mixed | **Yes** |
| Stop | Demand unreal | **No** |

## Next

1. Stay paused / archive unless owner writes a Phase 1 go memo.
2. Keep planner calibrations in sync.
3. Partner trace optional.
