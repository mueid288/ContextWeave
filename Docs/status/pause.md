# Project status (H3 slice-cal PASS)

**Effective:** 2026-10-23  
**State:** **ACTIVE (desk)** — not paused  
**G2:** FAIL · **H3 order GPU confirm:** FAIL · **H3 slice-cal:** **PASS**

## Policy (shipped)

1. **C1** if exact prefix  
2. Else **C3** only if workload-local `SliceCalibration` marks `(order, fact)` safe  
3. Else **C0** · **C4** refused  

Without a calibration table → same as before (C1 else C0).

## Evidence

- Same-suite LOO PASS: `artifacts/h3-slice-cal-2026-10-23/`
- Cross-suite transfer fails → do not ship a global order/fact rule

## Frozen

Phase 2, ResolventKV, G2 re-attack, order-only ACB/BAC as production gate.

## Next

1. Optional: GPU confirm of calibrate-then-serve on **same** gold distribution  
2. Partner trace — optional  
3. Desk-idle — fine; C3 stays off until a table is supplied  
