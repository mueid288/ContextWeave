# R1 — Gate oracle collect

| Piece | Role |
|---|---|
| `workload.py` | Zipfian lookup/synthesis requests (CPU) |
| `collect_oracle_http.py` | GPU HTTP collect → JSONL + oracle report |
| `cw-r1-oracle` | CPU re-analysis of banked trials |

## Laptop (allowed)

```bash
python scripts/r1/collect_oracle_http.py --dry-workload --n-requests 40 \
  --out /tmp/r1_workload.json
cw-r1-oracle --input path/to/oracle_trials.jsonl --report /tmp/r1.json --json
pytest tests/unit/test_r1_workload.py tests/unit/test_oracle_upside.py -q
```

## GPU / Colab

Follow [Docs/product/colab-r1-oracle.md](../../Docs/product/colab-r1-oracle.md).

```bash
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1   # GPU host only
python scripts/r1/collect_oracle_http.py \
  --base-url http://127.0.0.1:8000 \
  --c3-base-url http://127.0.0.1:8001 \
  --out artifacts/r1-oracle-WIP/oracle_trials.jsonl \
  --report artifacts/r1-oracle-WIP/oracle_report.json
```

Do **not** install torch/vllm/lmcache on the laptop
([Docs/runbooks/local-safety.md](../../Docs/runbooks/local-safety.md)).
