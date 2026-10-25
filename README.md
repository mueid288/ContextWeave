# ContextWeave

**Product (v0.2):** Canonical Order **C1** evaluation kit — reorder retrieved RAG
chunks so shared documents form a stable prefix, raising native **prefix-cache**
hits and cutting repeated prefill on multi-query workloads.

| Start | Link |
|---|---|
| Claims (can / cannot) | [Docs/product/CLAIMS.md](Docs/product/CLAIMS.md) |
| Integrator guide (10 min) | [Docs/product/integrators.md](Docs/product/integrators.md) |
| Live shim (`cw-serve-order`) | [Docs/product/live-shim.md](Docs/product/live-shim.md) |
| Ship note | [Docs/status/ship-v0.2-c1-kit.md](Docs/status/ship-v0.2-c1-kit.md) |

**Tag:** `v0.2.0-c1-kit` · Policy: prefer `by_frequency_desc`.

Research PIC / Phase 0–1 is **archived** ([closeout](Docs/status/closeout-phase0-1.md)).
Product desk closeout: [Docs/status/closeout-product-v0.md](Docs/status/closeout-product-v0.md).

**Laptop policy:** never download or run models on this machine. See
[Docs/runbooks/local-safety.md](Docs/runbooks/local-safety.md).

## Quick start — C1 kit (CPU)

```bash
git checkout v0.2.0-c1-kit   # or main at/after that tag
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Library
python -c "
from contextweave.product import FrequencyPrior, reorder_documents
prior = FrequencyPrior(cold_start_n=0)
print(reorder_documents(
    [{'document_id': 'b', 'content': 'B'}, {'document_id': 'a', 'content': 'A'}],
    'by_frequency_desc', prior=prior))
"

# Measure order A/B on a trace
cw-analyze-trace --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --compare-chunk-order --report /tmp/compare_chunk_order.md

# OpenAI-compatible reorder shim (optional upstream)
cw-serve-order --reorder-json /path/to/req.json --cold-start-n 0
# CW_UPSTREAM_URL=http://gpu:8000 cw-serve-order --port 8080
```

Full integrator path: [Docs/product/integrators.md](Docs/product/integrators.md).

## Research / demand tooling (secondary)

```bash
# Synthetic G0
python scripts/workloads/generate_workload.py --config configs/workloads/synthetic_rag_default.yaml
python scripts/workloads/analyze_trace.py --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --report benchmarks/reports/g0_synthetic_rag_default.md \
  --cache-budget-gb 128 --require-working-set

# Import partner_v1
python scripts/workloads/import_trace.py \
  --input benchmarks/trace_analysis/examples/partner_v1_sample.jsonl \
  --out benchmarks/workloads/imported_sample/trace.jsonl \
  --analyze --report benchmarks/reports/g0_imported_sample.md

# cw-field live pull → G0 (dogfood app; not the lab kit)
# export CW_FIELD_URL=http://127.0.0.1:8787 CW_FIELD_ADMIN_TOKEN=...
cw-field-g0

cw-plan-demo --json
cw-rag-demo index   # own-corpus demo; see Docs/product/colab-own-rag-demo.md
```

## Docs & scripts

| Path | Purpose |
|---|---|
| [Docs/product/CLAIMS.md](Docs/product/CLAIMS.md) | **Outbound claims** |
| [Docs/product/integrators.md](Docs/product/integrators.md) | **Lab integrate guide** |
| [Docs/product/](Docs/product/) | C1 product docs |
| [Docs/status/](Docs/status/) | Closeouts, ship notes, pause |
| [Docs/prd/](Docs/prd/) | Research charter (archive context) |
| [scripts/workloads/](scripts/workloads/) | G0 CPU CLIs |
| [artifacts/](artifacts/) | Banked evidence |

## Layout

```text
configs/           model and workload YAML
Docs/              product/, status/, core/, gates/, pre-reg/, …
src/contextweave/  product/ (C1) + research packages
benchmarks/        generated traces, reports
scripts/           workloads/, product/, g1/, …
tests/             unit tests (CPU)
artifacts/         banked evidence
```

## Gates (honest)

- **G0:** provisional PASS on synthetic / corpus paths; **provisional partner-field PASS**
  banked (`artifacts/cw-field-g0-2026-10-25-field/`). Not final tokenizer G0.
- **G1:** CacheBlend closed; EPIC@12k PASS (historical).
- **G2 / G3:** not opened.
- **Product C1:** scoped COMPLETE — TTFT suite + field desk A/B; see CLAIMS.
