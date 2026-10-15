# Phase 0 status

Updated: 2026-10-15

## Done (CPU week)

- [x] Research harness scaffold (`pyproject.toml`, `src/contextweave`, scripts, tests)
- [x] Synthetic RAG workload generator
- [x] Exact-prefix cache simulator + Section 2.2 / G0 metrics
- [x] Prior-art desk matrix stub + model RoPE check notes
- [x] GPU quote criteria + smoke-first runbook

## Next

- [x] Run default synthetic G0 report and attach numbers to experiment log
- [x] Real-trace importer + sample (`docs/trace-schema.md`, `scripts/import_trace.py`)
- [x] Cost model §7.5 (`scripts/cost_model.py`, `docs/cost_model_8b.md`)
- [x] Path C corpus replay (`scripts/build_corpus_trace.py`, sample docs)
- [x] Path C on user `my_corpus` (provisional G0 PASS — unconstrained = working-set **76.3%** @ 128 GB)
- [x] Fingerprint + provenance schema (FR-01/13)
- [x] Gemini review gaps → PRD v2.1 / v2.1.1 amendments + G0 LRU / cost roofline / Mode A
- [x] `my_corpus` G0 with `--require-working-set` @ 128 GB: PASS (76.3% LRU hits; matched denom)
- [ ] Send `docs/partner-ask.md` / get serving-log JSONL when possible
- [ ] Obtain GPU quotes when budget exists (do not rent until rent-gate checklist)
- [ ] Pin exact vLLM version on GPU day; accept model licenses then

## Explicitly not started

Planner, repair product, API, distributed cache, RoPE kernels.

## Laptop safety

- [x] No local model loads — `docs/local-safety.md` + `CONTEXTWEAVE_ALLOW_MODEL_LOAD` gate
- Do not `pip install torch/vllm/transformers` in the laptop `.venv`
