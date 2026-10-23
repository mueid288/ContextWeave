# H3 slice-cal GPU confirm — 2026-10-23

**Pre-reg:** `Docs/pre-reg/pre-reg-h3-slice-cal-gpu.md`  
**Verdict:** **FAIL**

Calibrate: seed **99** Lisbon table → Serve: seed **100** same golds.

| Metric | Value |
|---|---|
| Precision | **0.33** (need ≥0.9) |
| Policy mean_q | **0.83** (need ≥0.95) |
| Mean TTFT red vs C0 | 28% (irrelevant — quality miss) |
| `pass_heuristic` | **false** |

## Cell flip (C3 mean quality)

| Cell | seed 99 | seed 100 |
|---|---|---|
| ABC/city | 1.0 | **0.0** |
| ACB/city | 1.0 | 1.0 |
| BCA/year | 1.0 | 1.0 |
| BAC/year | 0.0 | 0.0 |
| CAB/code | 0.0 | **1.0** |
| CBA/code | 0.0 | **1.0** |

**Conclusion:** same golds + new filler is **not** the same workload for EPIC quality. Slice-cal tables do not transfer across filler text.
