# H3 GPU confirm — 2026-10-23

**Pre-reg:** `Docs/pre-reg/pre-reg-h3-gpu-confirm.md`  
**Verdict:** **FAIL**

Fresh golds: Lisbon / 2021 / BETA-4242 · filler-seed 99 · N=12

| Metric | Value |
|---|---|
| C3 mean quality | **0.50** |
| ACB/BAC rule precision | **0.50** (need ≥0.9) |
| Policy mean quality | **0.67** (need ≥0.95) |
| Mean TTFT red vs C0 | 38% (irrelevant — quality miss) |
| `pass_heuristic` | **false** |

## C3 fails on this suite

CAB_code, CBA_code, BAC_year (ACB_city **OK** — opposite of Phase1 suite).

**Conclusion:** order-only H3 does **not** generalize. Revert planner to blanket C3 refuse.
