# Benchmark reports

Generated G0 and later baseline reports land here (gitignored except this README).

Example:

```bash
python scripts/generate_workload.py
python scripts/analyze_trace.py \
  --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --report benchmarks/reports/g0_synthetic_rag_default.md \
  --metrics-json benchmarks/reports/g0_synthetic_rag_default.json
```
