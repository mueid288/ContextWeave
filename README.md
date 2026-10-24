# ContextWeave

Research harness for a **validity-checked planner** over modular KV-cache reuse
(prefix, existing PIC/repair methods, or full prefill) for self-hosted LLM inference.

**Status (2026-10-24): PAUSED / ARCHIVED** —
[Docs/status/closeout-phase0-1.md](Docs/status/closeout-phase0-1.md),
[Docs/status/pause.md](Docs/status/pause.md),
[Docs/Reports/phase01-negative-results.md](Docs/Reports/phase01-negative-results.md).  
G0 provisional PASS · G2/H3 FAIL · H4 misspecified→MFU consistency only · FP = conformance only.
Planner: **C1 else C0**.

**Laptop policy:** never download or run models on this machine. See
[Docs/runbooks/local-safety.md](Docs/runbooks/local-safety.md). Baseline scripts refuse
model load unless `CONTEXTWEAVE_ALLOW_MODEL_LOAD=1` on a rented GPU host.

Product requirements (Part II of the PRD) stay deferred (need G3 if Phase 2 ever opens).

## Quick start (CPU-only)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Generate a synthetic RAG trace and analyze Gate G0 metrics
python scripts/workloads/generate_workload.py --config configs/workloads/synthetic_rag_default.yaml
python scripts/workloads/analyze_trace.py --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --report benchmarks/reports/g0_synthetic_rag_default.md \
  --cache-budget-gb 128 --require-working-set

# Import a partner/real trace (see Docs/core/trace-schema.md), then G0
python scripts/workloads/import_trace.py \
  --input benchmarks/trace_analysis/examples/partner_v1_sample.jsonl \
  --out benchmarks/workloads/imported_sample/trace.jsonl \
  --analyze --report benchmarks/reports/g0_imported_sample.md

# PRD §7.5 cost / break-even table (no GPU)
python scripts/workloads/cost_model.py

# Path C: corpus folder → partner_v1 → provisional G0 (no GPU, no model)
python scripts/workloads/build_corpus_trace.py --analyze

# Example FR-01 fingerprint from a model YAML (metadata only)
python scripts/workloads/fingerprint_example.py --model-config configs/models/qwen3_8b.yaml

# Shipped policy demo (CPU)
cw-plan-demo --json

# Planner v0 (CPU)
python -c "from contextweave.planner import plan, RequestView; print(plan(RequestView(has_validated_nonprefix_artifacts=True)).to_dict())"
```

## Docs & scripts

| Path | Purpose |
|---|---|
| [Docs/README.md](Docs/README.md) | Doc folder index |
| [Docs/status/closeout-phase0-1.md](Docs/status/closeout-phase0-1.md) | **Phase 0/1 closeout** |
| [Docs/status/pause.md](Docs/status/pause.md) | Current project state |
| [Docs/status/experiment-log.md](Docs/status/experiment-log.md) | Dated experiment notes |
| [Docs/status/phase0-exit-decision.md](Docs/status/phase0-exit-decision.md) | Phase 0 pivot (no Phase 1) |
| [Docs/pre-reg/pre-reg-epic-quality.md](Docs/pre-reg/pre-reg-epic-quality.md) | EPIC multi-fact quality (**PASS**) |
| [artifacts/g1-epic-quality-2026-10-23/](artifacts/g1-epic-quality-2026-10-23/) | Quality suite banked JSON |
| [Docs/prd/](Docs/prd/) | Research charter + amendments |
| [scripts/README.md](scripts/README.md) | Script folder index |
| [scripts/workloads/](scripts/workloads/) | G0 CPU CLIs |
| [scripts/g1/epic/](scripts/g1/epic/) | EPIC install + bench |
| [artifacts/g1-epic-12k-2026-10-23/](artifacts/g1-epic-12k-2026-10-23/) | EPIC@12k PASS artifacts |

## Layout

```text
configs/           model and workload YAML
Docs/              status, core, gates, pre-reg, runbooks, Reviews, …
src/contextweave/  research packages
benchmarks/        generated traces, reports
scripts/           workloads/, g1/{epic,cacheblend,matched,common}/, smoke/
tests/             unit tests (CPU)
artifacts/         banked GPU JSON + freezes
```

## Gates

- **G0:** PASS (provisional on `my_corpus` / synthetic; partner trace optional).
- **G1:** CacheBlend **closed**; EPIC@12k **PASS** (single gold); multi-fact quality next.
- **G2 / G3:** **not opened** (see phase0-exit-decision).
