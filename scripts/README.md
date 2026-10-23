# Scripts

| Folder | Contents |
|---|---|
| [`workloads/`](workloads/) | G0 CPU: generate/import/analyze traces, cost model, fingerprints, baselines |
| [`g1/epic/`](g1/epic/) | EPIC / LegoLink install + probe + bench |
| [`g1/cacheblend/`](g1/cacheblend/) | Early CacheBlend / TTFT / quality / reorder benches |
| [`g1/matched/`](g1/matched/) | Matched-pin CacheBlend Gates B–E (Colab) |
| [`g1/common/`](g1/common/) | Shared scoring, engagement, blend hooks |
| [`smoke/`](smoke/) | Remote GPU smoke (`CONTEXTWEAVE_ALLOW_MODEL_LOAD=1`) |
| [`phase1/`](phase1/) | Oracle upside CLI (CPU; JSONL → G2 report) |
| [`_paths.py`](_paths.py) | Optional `repo_root()` helper |

Run from the **repo root** (scripts locate `pyproject.toml` themselves).

```bash
# CPU G0
python scripts/workloads/generate_workload.py --config configs/workloads/synthetic_rag_default.yaml
python scripts/workloads/analyze_trace.py --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --report benchmarks/reports/g0_synthetic_rag_default.md --cache-budget-gb 128 --require-working-set

# EPIC @12k (GPU host only)
bash scripts/g1/epic/g1_epic_install_fast.sh
python scripts/g1/epic/g1_epic_bench.py --target-context-tokens 12000 --suite quality --json --out out.json
```
