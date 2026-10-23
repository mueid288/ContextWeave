# Phase 0 exit decision

**Date:** 2026-10-23  
**Owner:** project (ContextWeave)  
**Status:** **PIVOT** completed → Phase 1 **GO (scoped)** on 2026-10-23 —
see [`phase1-go-memo.md`](phase1-go-memo.md). Historical pause:
[`pause.md`](pause.md).

Related: [`g1-closeout-thesis.md`](g1-closeout-thesis.md), experiment-log Current verdict,
§6 in `Reviews/claude_g1_remaining_gaps_fixes_recommendations.md`.

## Decision (updated)

| Question | Answer |
|---|---|
| Open Phase 1 (oracle / G2)? | **Yes — scoped {C0,C1,C3}** ([`phase1-go-memo.md`](phase1-go-memo.md)) |
| Open Phase 2 (planner@runtime / G3)? | **No** |
| Open ResolventKV kernels? | **No** |
| Continue Phase 0-style desk? | Folded into Phase 1 harness |
| GPU again? | Per [`pre-reg-phase1-oracle.md`](../pre-reg/pre-reg-phase1-oracle.md) |

## Why pivot first, then go

G0 demand held. CacheBlend failed the quality-preserving ≥15% bar. EPIC later
cleared latency + multi-fact quality @12k on the demo fork. That is enough to
test **H2 oracle upside** on {C0,C1,C3}, not to open full C0–C6 or ResolventKV.

## Checklist

- [x] G0 demand measured
- [x] CacheBlend closed on quality-constrained KPI
- [x] EPIC@12k + multi-fact quality PASS
- [x] Thesis + planner v0 (C3 keep, C4 refuse)
- [x] Phase 1 go memo + G2 thresholds ratified
- [ ] Phase 1 GPU oracle collect
- [ ] Partner trace (optional)
