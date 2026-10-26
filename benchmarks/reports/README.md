# Benchmark reports

Generated G0 / compare reports land here (gitignored except this README).

```bash
cw-generate-workload --config configs/workloads/synthetic_rag_default.yaml
cw-analyze-trace \
  --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --report benchmarks/reports/g0_synthetic_rag_default.md \
  --metrics-json benchmarks/reports/g0_synthetic_rag_default.json \
  --cache-budget-gb 128 --require-working-set
```

Large `benchmarks/workloads/*/` trees are regenerable and gitignored — delete
locally anytime to reclaim disk.
