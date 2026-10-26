# Scripts

| Folder | Contents |
|---|---|
| [`workloads/`](workloads/) | G0 CPU: generate / import / analyze traces; `cw_field_pipeline` |
| [`product/`](product/) | Claim reproduction: order TTFT + quality evals |
| [`ci/`](ci/) | `cpu_gate.sh` — unit tests + CLI help smoke |
| [`_paths.py`](_paths.py) | Optional `repo_root()` helper |

Phase 0/1 research scripts (`g1/`, `phase1/`, …) live on tag
`v0.1.1-phase01-full` / branch `archive/phase0-1-research`.

```bash
# CPU G0
python scripts/workloads/generate_workload.py --config configs/workloads/synthetic_rag_default.yaml
python scripts/workloads/analyze_trace.py --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --report /tmp/g0.md --cache-budget-gb 128 --require-working-set

# Field dogfood
export CW_FIELD_URL=http://127.0.0.1:8787 CW_FIELD_ADMIN_TOKEN=…
python scripts/workloads/cw_field_pipeline.py --allow-provisional-ok
```
