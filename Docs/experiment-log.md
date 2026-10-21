# Experiment Log

## 2026-10-11 — Phase 0 harness bootstrap (CPU)

- Scaffolded research repo layout from PRD Section 19 (minimal subset).
- Implemented synthetic RAG generator + exact-prefix cache simulator + G0 metrics.
- No GPU used.
- Ran default synthetic workload (`seed=42`, 500 requests).
- **Provisional G0 PASS:** recurring non-prefix share 75.9%, median chunk 900 tokens.
- Artifacts: `docs/g0-provisional-synthetic.md`, `benchmarks/reports/g0_synthetic_rag_default.md`.
- Prior-art desk matrix + GPU runbook written. Quote GPU; rent only after smoke checklist.

## 2026-10-11 — Phase 0B desk deepening (CPU)

- Fetched Qwen3-8B official `config.json`; Llama-3.1 Instruct via NousResearch mirror (official HF gated 401).
- Finding: Llama uses `rope_scaling.rope_type=llama3` factor 8; Qwen3 has `rope_scaling: null` — prefer Qwen3 for Case A/B.
- Candidate pins: LMCache **v0.5.2** + vLLM **≥ 0.26.0**; EPIC Apache-2.0 confirmed.
- Added `synthetic_rag_longctx` workload; baseline runner registry (`scripts/run_baseline.py`).
- Docs: `docs/runtime-pins.md` updated rent-gate checklist.

## 2026-10-11 — Real-trace importer + cost model (CPU)

- Added partner_v1 / text_approx importer (`scripts/import_trace.py`, `docs/trace-schema.md`).
- Added PRD §7.5 break-even cost model (`scripts/cost_model.py`).
- Still no GPU / no local model loads.
- Next human step: obtain a real partner JSONL (hashes + token counts or token ids).

## 2026-10-11 — Path C corpus replay

- Added `scripts/build_corpus_trace.py` + sample corpus under `benchmarks/corpora/sample_docs/`.
- Documents are real local files; request mix simulated; token counts via chars/4.
- G0 from this path stays provisional (see `docs/path-c-corpus-replay.md`).

## 2026-10-11 — Path C on user corpus (`my_corpus`)

- Corpus: 11 files → 127 chunks (WhatsApp Lead Qualifier PRD/tech docs, etc.).
- Provisional G0 **PASS**: recurring non-prefix **74.6%**, median chunk **783**, prefix-cache share 45.3%.
- Report: `benchmarks/reports/g0_my_corpus.md`.
- Still provisional (simulated request mix; chars/4 tokenization; all requests under 8k).

## 2026-10-11 — Fingerprint / provenance schema

- Implemented FR-01/02/04/13 dataclasses + validation + trust boundaries (CPU-only).
- Docs: `docs/fingerprints.md`, partner ask: `docs/partner-ask.md`.

## 2026-10-11 — Cloud GPU rental decision

- Plan: rent **Runpod RTX 4090** for ≤2h smoke with **Qwen3-8B** (~$2–5 cap).
- A100 80GB deferred until smoke passes.
- Guide: `docs/cloud-gpu-rental.md`. Remote smoke script: `scripts/smoke_remote.sh`.
- Pending human: HF account/token, Runpod deploy, terminate pod after smoke.

## 2026-10-12 — Runpod agent setup (Cursor)

- Followed https://docs.runpod.io/agent-setup.md
- Skills installed under `~/.agents/skills/` and symlinked into `~/.cursor/skills/`
- MCP config written: `~/.cursor/mcp.json` + project `.cursor/mcp.json` (hosted API + docs)
- Pending user: restart Cursor / reload MCP, Sign in with Runpod (OAuth) on first tool use
- `submit_feedback` unavailable until `runpod-docs` MCP is connected in-session

## 2026-10-14 — Gemini review gaps closed (CPU)

- Accepted all 7 Gemini findings → `Docs/prd/contextweave_prd_v2.1_amendments.md`
- Response: `Docs/Reviews/Gemini_1_response.md`
- Code: G0 LRU `--cache-budget-gb` / `--require-working-set`; repair HBM roofline;
  boundary token assembly; Mode A build-mode enforcement; block-size padding
- Phase 0 GPU planning buffer raised to 350–400 hours in amendments

## 2026-10-20 — Research brief ingested (ResolventKV)

- Source: `Docs/Research/Foundational AI Technology Research.md`
- Adoption map: `Docs/Research/ResolventKV-adoption.md` (insights now; kernels after G1 only)
- Updated: `Docs/prior-art.md` (SAFE-KV / ATTUNER / Irminsul contracts), `Docs/assumptions.md`,
  `Docs/architecture.md`, `Docs/gpu-runbook.md` Tier-1 quality slice
- Decision: keep Phase 0 path = smoke → CacheBlend/EPIC; ResolventKV is post-G1 candidate

## 2026-10-21 — Colab A100 smoke PASS

- Provider: Google Colab (Google AI Pro), session ephemeral
- GPU: **NVIDIA A100-SXM4-40GB** (driver 580.82.07, CUDA 13.0)
- Stack: vLLM **0.32.0**, torch 2.13.0, model `Qwen/Qwen3-8B`, max_model_len 4096
- Command: `CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 bash scripts/smoke_remote.sh`
- Result: **SMOKE_PASS** (output contained `smoke-ok`; model load ~15.3 GiB, KV budget ~19.6 GiB)
- Decision: open G1 step 1 (`scripts/g1_ttft_bench.py` — full vs prefix TTFT). CacheBlend deferred until step 1 saved.

## 2026-10-21 — G1 step 1 TTFT (short prefix; provisional)

- Command: `python scripts/g1_ttft_bench.py --json` (defaults: `--doc-chars 3500`, max_model_len 4096)
- Shared prefix: **~1500 chars** (too short for a strong prefix-cache signal)
- full_prefill p50: **443.6 ms** (n=3)
- prefix_cache p50: **423.4 ms** (n=3)
- Speedup: **1.05×** (noise-level; not evidence for or against G1)
- Decision: re-run with token-budget sizing before interpreting; then CacheBlend

## 2026-10-21 — G1 step 1 TTFT (6k shared prefix) PASS

- Env: Colab A100-40GB, vLLM 0.32.0, `Qwen/Qwen3-8B`, max_model_len 8192
- Command: `python scripts/g1_ttft_bench.py --target-prefix-tokens 6000 --max-model-len 8192 --json`
- Shared prefix: **6000 tokens** (~22007 chars)
- full_prefill p50: **638.7 ms** (n=3)
- prefix_cache p50: **248.9 ms** (n=3)
- Speedup: **2.57×**
- Decision: native prefix baseline is real on this stack. Next = LMCache CacheBlend (non-prefix) + answer-preservation slice.

## 2026-10-21 — G1 quality slice (first run; scorer too strict)

- Command: `python scripts/g1_quality_bench.py --json`
- **modes_agree_rate: 1.0** (full vs prefix identical on all 3 cases) ← main preservation signal
- contains_rate reported 0.33 because scorer only looked at the first line; gold `2019` appeared later in the output
- Decision: treat agreement as provisional PASS for prefix answer preservation; fix scorer and re-score / re-run

## 2026-10-21 — G1 quality slice PASS

- Command: `python scripts/g1_quality_bench.py --json` (fixed scorer)
- Env: Colab A100-40GB, vLLM 0.32.0, Qwen3-8B
- full_contains_rate: **1.0** / prefix_contains_rate: **1.0**
- modes_agree_rate: **0.67** (gamma both contain `2019` but normalized strings differ slightly)
- **pass_heuristic: true**
- Decision: prefix reuse preserves planted-fact answers on this stack. CacheBlend still blocked on pin.

## 2026-10-21 — G1 step 3 CacheBlend BLOCKED (pin)

- Env: Colab A100-40GB, vLLM **0.32.0**, lmcache **0.5.6**, `Qwen/Qwen3-8B`
- Path: in-process `LMCacheConnectorV1` + `LMCACHE_ENABLE_BLENDING` / layerwise
- Got past: CUDA spawn, `VLLMModelTracker.register_model` monkeypatch (LMCache #4131)
- Fail: first `generate` → `save_kv_layer` → `batched_from_gpu` →
  `IndexError: Dimension out of range (expected [-4, 3], but got 4)`
- Interpretation: KV-layout / layerwise GPU connector mismatch vs vLLM 0.32 (not a ContextWeave bug)
- Decision: **abort CacheBlend on this pin** (matches runbook stop condition). Keep G1 step 1.
  Next session: try matched image (`lmcache/vllm-openai`) or older documented pair
  (e.g. vLLM ~0.26 + LMCache 0.5.2), or MP `--engine-type blend` — 1-session time-box.

## Template for future entries

```
## YYYY-MM-DD — <title>
- Hypothesis / gate:
- Environment (CPU/GPU, drivers, pins):
- Command:
- Result:
- Decision:
```
