# Pre-registration: H4 cost model vs measured TTFT

**Status:** **MISSPECIFIED, superseded** (2026-10-24) — `artifacts/h4-cost-model-2026-10-24/`  
**Superseded by:** `Docs/pre-reg/pre-reg-h4-mfu.md` (peak 312 × MFU 40–65%)  
**Not a G2 redo. Not H3.**

Default **450** TFLOP/s exceeds A100 dense bf16 peak (~312). Large absolute error
was guaranteed before data collection; do not cite as “cost model fails.”

## Result (primary)

Mistral-7B params, **450** TFLOP/s vs banked EPIC A100 C0 @~12k:

| Suite | Rel abs error | ≤20%? |
|---|---|---|
| Phase1 / confirm / keydev×2 | **~0.60** | **no** |
| `pass_heuristic` | **false** | |

Pred ~457 ms vs meas ~1.13–1.16 s.

## Secondary (report only)

Calibrate TFLOP on confirm seed 99 → **~182** TFLOP/s; seed 100 rel err **~2.9%**.
Calibrated rate transfers; PRD default does **not**.

## Decision

§7.5 planning tables are **not** H4-validated at default assumptions. Planner
keeps C1-else-C0; do not treat estimated prefill as measured. **PAUSED.**
