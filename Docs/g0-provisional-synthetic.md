# Provisional Gate G0 — Synthetic RAG default

Date: 2026-10-11  
Trace: `benchmarks/workloads/synthetic_rag_default/trace.jsonl`  
Config: `configs/workloads/synthetic_rag_default.yaml`  
Status: **PASS (provisional)**

Regenerate:

```bash
source .venv/bin/activate
python scripts/generate_workload.py --config configs/workloads/synthetic_rag_default.yaml
python scripts/analyze_trace.py \
  --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --report benchmarks/reports/g0_synthetic_rag_default.md \
  --metrics-json benchmarks/reports/g0_synthetic_rag_default.json
```

## Result

| Metric | Value |
|---|---|
| Requests | 500 |
| Total prefill tokens | 1,247,367 |
| Served by native prefix cache | 574,800 (46.1%) |
| Prefix-cache token budget | 183,105 (evictions=423) |
| Recurring non-prefix / post-prefix | **78.0%** (threshold 30%) |
| Median chunk length | **912** (threshold 512) |
| Synthesis fraction | 44.0% |
| Reuse distance (median / p90) | 5 / 44 requests |

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 672,567 |
| Post-prefix chunk tokens (diagnostic) | 630,384 |
| Hit tokens under budget | 524,432 (78.0% of post-prefix) |
| Hit share of chunks only | 83.2% |
| Miss tokens | 105,952 |
| Evictions | 0 |
| Peak resident | 13.89 GB |

## Decision implication

Synthetic demand clears G0. This **does not** authorize product build or GPU spend by itself. Next: complete rent-gate checklist in [gpu-runbook.md](gpu-runbook.md), obtain quotes, then smoke-test on a rented 80 GB GPU. Replace this result with a real serving trace before calling G0 final.
