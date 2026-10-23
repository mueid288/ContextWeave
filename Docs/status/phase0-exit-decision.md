# Phase 0 exit decision

**Date:** 2026-10-23  
**Owner:** project (ContextWeave)  
**Status:** **PIVOT** then **PAUSED** — Phase 0 desk complete; Phase 1 **not** opened;
active work stopped on purpose ([`pause.md`](pause.md)).

Related: [`g1-closeout-thesis.md`](g1-closeout-thesis.md), experiment-log Current verdict,
§6 in `Reviews/claude_g1_remaining_gaps_fixes_recommendations.md`.

## Decision

| Question | Answer |
|---|---|
| Open Phase 1 (oracle / G2)? | **No** |
| Open Phase 2 (planner@runtime / G3)? | **No** |
| Open ResolventKV kernels? | **No** |
| Continue Phase 0-style desk (planner policy, fingerprints, cost notes)? | **Yes** (maintenance) |
| GPU again? | **Only** with a new one-question pre-reg (e.g. fair EPIC @≥6k/12k) |

## Why (one paragraph)

G0 showed enough recurring non-prefix demand. G1 showed the prefix gap is real and
CacheBlend can engage on A100 @12k, but **not** with a quality-preserving ≥15% TTFT
win (Gate D bac agree 0.67; ~1.10× latency; CBA miss). EPIC was never fairly scaled.
PRD Phase 1 is contingent on clearing that bar / proving oracle upside — neither is
in hand. Building G2/G3 machinery now would be inventing ahead of evidence.

## What “pivot” means in practice

1. **Ship policy, not kernels:** keep `planner.v0` + fingerprints as the product shape.
2. **Best fixed config on this slice** = exact prefix when available, else **full prefill**
   (C4 discarded).
3. **Falsification already hit for “beat CacheBlend with custom repair”** on this pin —
   ResolventKV stays blocked per §6.
4. **Optional later experiments** are new projects with their own pre-reg, not G1 reopen.

## Ratify G2–G4 thresholds?

**Deferred.** PRD allows revising thresholds at G1 before Phase 1 data. We are **not**
entering Phase 1, so threshold ratification is postponed until a future go decision.
Do not treat proposed G2/G3 numbers as active.

## Checklist

- [x] G0 demand measured (provisional without partner trace)
- [x] CacheBlend baseline engaged + closed on quality-constrained KPI
- [x] Thesis restated with numbers
- [x] Planner v0 encodes refusal of failing C4
- [x] Cost-model doc anchored with A100 measurements (not H4)
- [x] Explicit: Phase 1 / G2 / G3 **not** started
- [ ] Partner trace (optional, non-blocking) — still none; do not wait
- [x] Fair EPIC @scale pre-reg written — `Docs/pre-reg/pre-reg-epic-12k.md` (**PARKED**; run only on explicit start)
- [x] Intentional **pause** recorded — `Docs/status/pause.md` (2026-10-23)
