# Phase 0 status

Updated: 2026-10-21

## Done (CPU week)

- [x] Research harness scaffold (`pyproject.toml`, `src/contextweave`, scripts, tests)
- [x] Synthetic RAG workload generator
- [x] Exact-prefix cache simulator + Section 2.2 / G0 metrics
- [x] Prior-art desk matrix stub + model RoPE check notes
- [x] GPU quote criteria + smoke-first runbook
- [x] ResolventKV research brief ingested → adoption map + prior-art / G1 quality contracts

## Next

- [x] Run default synthetic G0 report and attach numbers to experiment log
- [x] Real-trace importer + sample (`docs/trace-schema.md`, `scripts/import_trace.py`)
- [x] Cost model §7.5 (`scripts/cost_model.py`, `docs/cost_model_8b.md`)
- [x] Path C corpus replay (`scripts/build_corpus_trace.py`, sample docs)
- [x] Path C on user `my_corpus` (provisional G0 PASS — unconstrained = working-set **76.3%** @ 128 GB)
- [x] Fingerprint + provenance schema (FR-01/13)
- [x] Gemini review gaps → PRD v2.1 / v2.1.1 amendments + G0 LRU / cost roofline / Mode A
- [x] `my_corpus` G0 with `--require-working-set` @ 128 GB: PASS (76.3% LRU hits; matched denom)
- [x] HF token + **Colab A100-40GB smoke** (`scripts/smoke_remote.sh` → **SMOKE_PASS**)
- [x] G1 step 1: full vs prefix TTFT — **2.57×** at 6k shared tokens (`g1_ttft_long.json`)
- [x] G1 step 2: answer preservation — **PASS** (contains 1.0/1.0, agree 0.67, `pass_heuristic`)
- [ ] G1 step 3 CacheBlend — **BLOCKED** on vLLM 0.32 + lmcache 0.5.6; retry matched pins later
- [ ] G1 step 4: EPIC
- [ ] Partner log optional (`docs/partner-ask.md`)

## Explicitly not started

Planner, ResolventKV kernels, repair product, API, distributed cache, RoPE CUDA.

## Laptop safety

- [x] No local model loads — `docs/local-safety.md` + `CONTEXTWEAVE_ALLOW_MODEL_LOAD` gate
- Do not `pip install torch/vllm/transformers` in the laptop `.venv`
