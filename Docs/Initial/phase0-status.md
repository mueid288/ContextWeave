# Phase 0 status

Updated: 2026-10-23 — **PAUSED** (`Docs/pause.md`)

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
- [x] G1 step 2b: reorder gap — **PASS** (1.25× slower on reorder; answers OK)
- [x] G1 step 3 CacheBlend MP — **provisional latency** (1.22× warm reorder) / **quality FAIL**; in-process still BLOCKED
- [x] G1 step 4: EPIC — **documented pin BLOCK** on Colab vLLM 0.32 (`g1_epic_probe.json`); dedicated fork session optional
- [x] G1 Colab pin closeout — `cw-smoke` stopped; residual = pin gap (see experiment-log)
- [x] G1 matched-pin Stage A harness — benches/scripts/pre-reg (`Docs/g1-matched-colab.md`)
- [x] G1 matched-pin B–E — prior runs **CONFOUNDED** (antigravity Round-2); harness remediation landed
- [x] G1 matched re-run (vLLM 0.18 / lmcache 0.4.2) — data banked; verdict **INCONCLUSIVE** (no engagement proof; reorder≈cold)
- [x] G1 EPIC fast path — **INCONCLUSIVE (toy scale)**; not a fair close
- [x] Offline FIX-1/2/3 — Gate R + alignment audit + log relabel (`claude_g1_remaining_gaps…`)
- [x] G1-DIAG #1/#2 — engagement proven on in-process blend; **G1 CacheBlend CLOSED**
  (no quality-preserving ≥15% TTFT win; Gate D bac 0.67; see experiment-log)
- [x] Post-G1 desk pivot (first cut): thesis restatement `Docs/g1-closeout-thesis.md` +
  planner v0 `contextweave.planner.v0` (refuses C4 on G1 calibration)
- [x] Cost-model note: measured A100 anchors folded into `Docs/cost_model_8b.md` (not H4)
- [x] Phase 0 exit decision — `Docs/phase0-exit-decision.md` (**PIVOT**; Phase 1/G2/G3 not opened)
- [x] Prior-art matrix updated with measured CacheBlend/EPIC gaps (2026-10-23)
- [ ] Partner log optional (`Docs/partner-ask.md`) — **no partner yet**; non-blocking
- [x] Optional EPIC@12k pre-reg parked — `Docs/pre-reg-epic-12k.md` (not started)
- [x] Intentional pause — `Docs/pause.md`


## Explicitly not started

ResolventKV kernels, repair product, API, distributed cache, RoPE CUDA, Phase 1
oracle (G2), Phase 2 risk-signal/H4 (G3). Planner **v0** exists (CPU rules only).

## Laptop safety

- [x] No local model loads — `docs/local-safety.md` + `CONTEXTWEAVE_ALLOW_MODEL_LOAD` gate
- Do not `pip install torch/vllm/transformers` in the laptop `.venv`
