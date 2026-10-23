# H3 order-risk replay — 2026-10-23

**Pre-reg:** `Docs/pre-reg/pre-reg-h3-order-risk.md`  
**Verdict:** **PASS** (in-sample replay; not a G2 claim)

| Metric | Value |
|---|---|
| Rule | Refuse C3 if order ∈ {ACB, BAC}; else C3; unknown → refuse |
| Precision / recall | **1.0 / 1.0** |
| Policy mean quality | **1.0** |
| Mean TTFT vs always-C0 | **−40%** (688 vs 1148 ms) |

Source labels: `artifacts/phase1-oracle-2026-10-23/oracle_trials.jsonl`.
