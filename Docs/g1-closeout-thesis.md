# G1 closeout — thesis restatement (measured)

**Date:** 2026-10-23  
**Status:** Phase 0B G1 CacheBlend **CLOSED**; EPIC not fairly scaled.  
**Decision:** **Pivot** (not stop, not Phase 1 build). Per §6 in
`Docs/Reviews/claude_g1_remaining_gaps_fixes_recommendations.md`.

## What Phase 0 asked

| Gate | Question | Result |
|---|---|---|
| G0 | Enough recurring non-prefix context? | **PASS** — `my_corpus` ~76% working-set @ 128 GB |
| G1 | Reproduce Tier-1 PIC; is there a quality-preserving ≥15% TTFT win? | **CacheBlend: no** on A100 @12k (this pin). EPIC: inconclusive toy scale |

## Measured facts (do not re-litigate without a new pre-reg)

1. **Prefix gap is real:** full vs shared-prefix TTFT ~**2.57×** @6k (G1 step 1).
2. **Reorder hurts prefix:** ~**1.25×** slower when docs reorder (G1 step 2b).
3. **CacheBlend can engage** (G1-DIAG #2 in-process): BAC cached_tokens **7705**,
   warm_bac≈warm_abc (~622 vs ~619 ms). CBA cached **19** (miss); warm_cba &gt; cold.
4. **Quality when engaged:** Gate D bac contains/agree **0.67** — fails policy.
5. **Latency when engaged:** blend reorder ~**1.10×** vs native reorder — below 1.15×
   Gate E; Gate R formal FAIL (7705 &lt; 8063 ≈ 66.9% vs 70% bar).
6. **EPIC:** fast-path ~500 tok only — **not** a fair Tier-1 close.

Artifacts: `artifacts/g1-diag-2026-10-23/`, `artifacts/g1-epic-2026-10-23/`.

## Hypothesis status

| ID | Claim | After G1 |
|---|---|---|
| H1 | Enough non-prefix recurrence | **Supported** (G0) |
| H2 | No single fixed PIC config wins; selection helps | **Open** — oracle study (Phase 1) not started; single fixed CacheBlend **fails** quality bar on this slice |
| H3/H4 | Risk signal / cost model | **Not tested** on GPU; cost model remains planning-only |
| “Beat CacheBlend with our kernels” | ResolventKV path | **Blocked** — §6 requires verified engagement + quality-preserving ≥15% win first |

## Product thesis (restated)

ContextWeave is **not** “a better CacheBlend.” It is a **validity-checked planner**
that chooses among prefix, existing PIC/repair methods, and full prefill — and
**refuses** reuse when fingerprints or quality calibration say so.

On the measured A100 @12k Qwen3 slice, the v0 planner must **discard C4
(CacheBlend)** (quality risk + no ≥15% win) and fall back to **C0** unless **C1**
(exact prefix) applies. See `contextweave.planner.v0`.

## Go / pivot / stop

| Option | When | Now |
|---|---|---|
| Go Phase 1 | G0∧G1 pass with a Tier-1 win | **No** |
| Pivot | Demand real; baselines don’t clear the bar | **Yes** — desk: planner policy + fingerprints + cost model; optional later fair EPIC @12k as a *new* pre-reg |
| Stop | Demand unreal or work abandoned | **No** — G0 still stands |

## Explicitly not next

- More Colab pin-shim fishing for CacheBlend G1
- ResolventKV kernels
- Treating EPIC toy bench as negative or positive

## Next desk work

1. Keep planner v0 calibrations in sync when new slices are measured.
2. ~~Cost-model A100 anchors~~ — done (`Docs/cost_model_8b.md`).
3. Phase 0 exit memo — `Docs/phase0-exit-decision.md` (**pivot**; no Phase 1).
4. Optional partner trace (`Docs/partner-ask.md`) — non-blocking.
5. Only reopen GPU with a written one-question pre-reg (e.g. EPIC @≥6k/12k).
