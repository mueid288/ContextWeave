# EPIC multi-fact quality @ 12k — 2026-10-23

**Pre-reg:** `Docs/pre-reg/pre-reg-epic-quality.md`  
**Session:** `cw-epic-quality` (Colab A100)  
**Verdict:** **PASS** (`pass_heuristic: true`)

| Case | Full p50 | kvlink p50 | Speedup | Contains (full/kvlink) |
|---|---|---|---|---|
| city | 1030 ms | 267 ms | **3.86×** | ✓ / ✓ |
| year | 1265 ms | 577 ms | **2.19×** | ✓ / ✓ |
| code | 1139 ms | 575 ms | **1.98×** | ✓ / ✓ |

- `contains_rate_full` / `contains_rate_kvlink`: **1.0 / 1.0**
- Every case `latency_ok` (≥15%)
- Model: `mistralai/Mistral-7B-Instruct-v0.2`; ~12000 prompt tokens

## Files

- `g1_epic_quality_12k.json`
- `pip_freeze.txt`
