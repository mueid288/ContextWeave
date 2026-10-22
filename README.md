# ContextWeave

Research harness for **modular KV-cache composition and context repair** for self-hosted LLM inference.

Phase 0 scope (approved): demand / workload analysis (0A) and prior-art / baseline preparation (0B).  
No GPU is required for Week 1 CPU work. Do **not** rent GPU time until the G0 note and reproduction runbooks exist.

**Laptop policy:** never download or run models on this machine. See [Docs/local-safety.md](Docs/local-safety.md). Baseline scripts refuse model load unless `CONTEXTWEAVE_ALLOW_MODEL_LOAD=1` on a rented GPU host.

Product requirements (Part II of the PRD) are deferred until Gate G3.

## Quick start (CPU-only)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Generate a synthetic RAG trace and analyze Gate G0 metrics
python scripts/generate_workload.py --config configs/workloads/synthetic_rag_default.yaml
python scripts/analyze_trace.py --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --report benchmarks/reports/g0_synthetic_rag_default.md \
  --cache-budget-gb 128 --require-working-set

# Import a partner/real trace (see Docs/trace-schema.md), then G0
python scripts/import_trace.py \
  --input benchmarks/trace_analysis/examples/partner_v1_sample.jsonl \
  --out benchmarks/workloads/imported_sample/trace.jsonl \
  --analyze --report benchmarks/reports/g0_imported_sample.md

# PRD §7.5 cost / break-even table (no GPU)
python scripts/cost_model.py

# Path C: corpus folder → partner_v1 → provisional G0 (no GPU, no model)
python scripts/build_corpus_trace.py --analyze

# Example FR-01 fingerprint from a model YAML (metadata only)
python scripts/fingerprint_example.py --model-config configs/models/qwen3_8b.yaml
```

## Docs

| Doc | Purpose |
|---|---|
| [Docs/project-overview.md](Docs/project-overview.md) | Plain-language + technical overview of the whole project |
| [Docs/prd/contextweave_prd_v2.md](Docs/prd/contextweave_prd_v2.md) | Research charter + deferred product requirements |
| [Docs/prd/contextweave_prd_v2.1_amendments.md](Docs/prd/contextweave_prd_v2.1_amendments.md) | Binding Gemini-gap fixes |
| [Docs/architecture.md](Docs/architecture.md) | Phase 0 system view and deferred components |
| [Docs/assumptions.md](Docs/assumptions.md) | Phase 0 locked defaults |
| [Docs/cost_model_8b.md](Docs/cost_model_8b.md) | PRD §7.5 analytical cost model & break-even estimates |
| [Docs/experiment-log.md](Docs/experiment-log.md) | Dated experiment notes |
| [Docs/prior-art.md](Docs/prior-art.md) | Tier 1/2 matrix and license notes |
| [Docs/gpu-runbook.md](Docs/gpu-runbook.md) | When and how to rent GPU for 0B |
| [Docs/runtime-pins.md](Docs/runtime-pins.md) | Candidate vLLM / LMCache pins |
| [Docs/g0-provisional-synthetic.md](Docs/g0-provisional-synthetic.md) | Latest provisional G0 result |
| [Docs/g0-provisional-corpus-replay.md](Docs/g0-provisional-corpus-replay.md) | Provisional G0 result for corpus replay |
| [Docs/trace-schema.md](Docs/trace-schema.md) | Real/partner trace import schema |
| [Docs/path-c-corpus-replay.md](Docs/path-c-corpus-replay.md) | Build provisional G0 from a docs folder |
| [Docs/fingerprints.md](Docs/fingerprints.md) | FR-01/13 fingerprint + trust schema |
| [Docs/partner-ask.md](Docs/partner-ask.md) | Short email to request a real trace |
| [Docs/cloud-gpu-rental.md](Docs/cloud-gpu-rental.md) | How to rent a cloud GPU for smoke |
| [Docs/local-safety.md](Docs/local-safety.md) | No local model loads |
| [Docs/Reviews/Gemini_1.md](Docs/Reviews/Gemini_1.md) | Gemini Review Round 1 |
| [Docs/Reviews/Gemini_1_response.md](Docs/Reviews/Gemini_1_response.md) | Review disposition (Round 1) |
| [Docs/Reviews/Gemini_2.md](Docs/Reviews/Gemini_2.md) | Gemini Review Round 2 |
| [Docs/Reviews/Gemini_2_response.md](Docs/Reviews/Gemini_2_response.md) | Review disposition (Round 2) |
| [Docs/Reviews/Gemini_3.md](Docs/Reviews/Gemini_3.md) | Gemini Review Round 3 |
| [Docs/Reviews/Gemini_3_response.md](Docs/Reviews/Gemini_3_response.md) | Review disposition (Round 3) |
| [Docs/Initial/](Docs/Initial/) | Phase 0 working notes |
| [Docs/g1-colab.md](Docs/g1-colab.md) | G1 on Colab after smoke (TTFT → CacheBlend) |
| [Docs/g1-matched-colab.md](Docs/g1-matched-colab.md) | Matched-pin CacheBlend Gates B–E (post Round-2 harness) |
| [Docs/g1-epic.md](Docs/g1-epic.md) | EPIC / LegoLink dedicated-session procedure |
| [Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md](Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md) | Quality-gated CacheBlend runbook |
| [Docs/Reviews/antigravity_contextweave-deep-review-v2.md](Docs/Reviews/antigravity_contextweave-deep-review-v2.md) | Round-2 G1 harness audit |
| [artifacts/g1-matched-2026-10-22/](artifacts/g1-matched-2026-10-22/) | Checked-in Colab A100 matched-pin JSONs |
| [scripts/g1_cacheblend_bench.py](scripts/g1_cacheblend_bench.py) | G1 step 3 non-prefix CacheBlend TTFT bench |
| [Docs/Research/ResolventKV-adoption.md](Docs/Research/ResolventKV-adoption.md) | What we take from the ResolventKV research brief (post-G1 candidate) |
| [Docs/Research/Foundational AI Technology Research.md](Docs/Research/Foundational%20AI%20Technology%20Research.md) | Full ResolventKV research brief (equations as images) |

## Layout

```text
configs/          model and workload YAML
Docs/             architecture, assumptions, prior-art, PRD
src/contextweave/ research packages (Phase 0 focuses on workloads + trace analysis)
benchmarks/       generated traces, reports
scripts/          CLI entry points
tests/            unit tests (CPU)
```

## Gates

- **G0 (provisional on synthetic):** ≥30% of post-prefix-cache prefill tokens are recurring non-prefix; median chunk length ≥512.
- **G1:** Tier-1 baselines reproduced on GPU (see `Docs/gpu-runbook.md`).
