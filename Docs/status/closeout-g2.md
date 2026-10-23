# Closeout after Phase 1 / G2 FAIL

**Date:** 2026-10-23  
**State:** **PAUSED / archived for research spend**  
**Policy shipped:** C1 if exact prefix else **C0**; C3/C4 refused (`planner.v0`)

## What was answered

| Question | Answer |
|---|---|
| G0 demand? | **PASS** (~76% working-set) |
| CacheBlend quality-preserving ≥15%? | **No** (CLOSED) |
| EPIC latency + multi-fact @12k? | **PASS** on easy orders; **0.70** contains on reorder suite |
| H2 oracle upside vs best fixed? | **G2 FAIL** — upside 0 vs C0 on p95/quality |
| Open Phase 2 / ResolventKV? | **No** |

## Why not re-attack G2

Perfect C3 → best fixed becomes C3 → selection upside still 0.  
Order-aware refusal → mean TTFT can improve, **p95** still tracks C0 fallbacks → G2 TTFT bar still fails.  
See experiment-log 2026-10-23 oracle entry + `artifacts/phase1-oracle-2026-10-23/`.

## Resume only via

1. Stay paused (default).
2. Parked H3 pre-reg — [`Docs/pre-reg/pre-reg-h3-order-risk.md`](../pre-reg/pre-reg-h3-order-risk.md) (mean-TTFT product policy; **not** a G2 redo).
3. Explicit new go memo (Phase 2 or kernels) — not justified by current evidence.
