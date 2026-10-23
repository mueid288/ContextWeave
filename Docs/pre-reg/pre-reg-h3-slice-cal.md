# Pre-registration: H3 slice calibration (offline)

**Status:** **PASS** (2026-10-23) — `artifacts/h3-slice-cal-2026-10-23/`  
**Depends on:** H3 order-only GPU confirm **FAIL**  
**Not a G2 redo.** Phase 2 / ResolventKV still closed.

## One question

Can a **workload-local** offline table over CPU-visible
`(chunk_order, fact_type)` predict C3 quality fails well enough that
“C3 iff cell calibrated safe, else C0” keeps mean contains ≥0.95 and cuts
**mean** TTFT ≥20% vs always-C0 — when fit and evaluated on the **same**
prompt distribution (leave-one-trial-out per cell)?

This is PRD §3.2 H3 “per-chunk offline calibration”, **not** the order-only
ACB/BAC rule (archived).

## Result

| Suite | Precision | Policy mean_q | Mean TTFT red |
|---|---|---|---|
| Phase1 oracle | **1.0** | **1.0** | **41%** |
| H3 confirm | **1.0** | **1.0** | **34%** |
| `pass_heuristic` | **true** | | |

Cross-suite transfer (secondary): precision **0.33–0.50** — tables do **not**
transfer across golds. Local calibration is required.

## Decision

Planner: C3 only if `RequestView.slice_calibration` marks `(order, fact)` safe;
else C0. Default (no table) remains refuse C3.

## Next

GPU confirm pre-reg (desk): `Docs/pre-reg/pre-reg-h3-slice-cal-gpu.md` —
calibrate seed 99 → serve seed 100, **same** golds.
