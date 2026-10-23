# H3 slice calibration — 2026-10-23

**Pre-reg:** `Docs/pre-reg/pre-reg-h3-slice-cal.md`  
**Verdict:** **PASS** (same-suite LOO)

| Suite | Prec | Policy q | Mean TTFT red vs C0 |
|---|---|---|---|
| Phase1 oracle | 1.0 | 1.0 | 41% |
| H3 confirm | 1.0 | 1.0 | 34% |

**Cross-suite transfer:** precision 0.33–0.50 (expected fail — not a pass bar).

**Policy:** C3 only when a **workload-local** `(order, fact_type)` table marks the cell safe; unknown → C0. No global order rule.
