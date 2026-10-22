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

## 2026-10-21 — G1 reorder gap PASS

- Command: `python scripts/g1_reorder_gap_bench.py --json`
- ABC warm (prefix hit): **330 ms**; BCA reorder: **412 ms**; slowdown **1.25×**
- Both orders contain gold `Karachi`
- **pass_heuristic: true** — non-prefix reorder costs latency under native prefix cache while answers stay correct
- Decision: gap that CacheBlend/EPIC target is real on this workload; unblock those on a matched pin next

## 2026-10-21 — G1 step 3 CacheBlend BLOCKED (pin)

- Env: Colab A100-40GB, vLLM **0.32.0**, lmcache **0.5.6**, `Qwen/Qwen3-8B`
- Path: in-process `LMCacheConnectorV1` + `LMCACHE_ENABLE_BLENDING` / layerwise
- Got past: CUDA spawn, `VLLMModelTracker.register_model` monkeypatch (LMCache #4131)
- Fail: first `generate` → `save_kv_layer` → `batched_from_gpu` →
  `IndexError: Dimension out of range (expected [-4, 3], but got 4)`
- Interpretation: KV-layout / layerwise GPU connector mismatch vs vLLM 0.32 (not a ContextWeave bug)
- Decision: try MP `--engine-type blend` next; keep G1 step 1–2b.

## 2026-10-21 — G1 CacheBlend MP hang (Colab port 8080)

- `lmcache server` default HTTP bind on **8080** failed (`address already in use` on Colab)
- Server then shut down; vLLM MP worker still started and hung on first generate (`mq_timeout=300`)
- Fix: `g1_cacheblend_mp.sh` now uses `--http-port 18080` and refuses to continue if server dies

## 2026-10-21 — G1 CacheBlend MP false-not-ready (Colab)

- After 18080 fix, script killed a still-alive server at ~4s: ready string not yet logged
  (blend CUDA init slower than prefix-only; ZMQ ready line is
  `LMCache ZMQ cache server is running`)
- Concurrently, prior hung client finally raised `ConnectionError` after `mq_timeout=300`
- Fix: poll up to 90s for ZMQ/ready/healthcheck; use `--supported-transfer-mode lmcache_driven`

## 2026-10-21 — G1 CacheBlend MP latency PASS / quality FAIL

- Env: Colab A100-40GB, vLLM **0.32.0**, lmcache **0.5.6**, `Qwen/Qwen3-8B`
- Path: `lmcache server --engine-type blend` + `LMCacheMPConnector` (`g1_cacheblend_mp.sh`)
- cold ABC **1005 ms**; warm BAC **825** / CBA **817**; warm p50 **821**; speedup **1.22×**
- Latency `pass_heuristic: true` (≥15% faster on reorder)
- **Quality fail:** outputs do not answer with document ids (echo/`# #` garbage; cold invents questions)
- Interpretation: MP stack runs and shows a TTFT gap, but this is **not** a clean non-prefix
  reuse proof — could be warmup/noise, and blend may be corrupting decode on this pin
- Decision: bank as **provisional latency**; do **not** claim G1 CacheBlend quality.

## 2026-10-21 — G1 EPIC path = dedicated fork (not this Colab pin)

- DerekHJH/epic is a **vLLM ~0.7 fork** (`torch==2.5.1`, `cache_fuse_metadata` / `hack_kv`)
- Incompatible with working Colab pin (vLLM **0.32.0**); installing it would wipe smoke/TTFT stack
- Harness: `scripts/g1_epic_probe.py` (pin check), `g1_epic_install.sh` + `g1_epic_bench.py`
  (dedicated session only) — see `Docs/g1-epic.md`

## 2026-10-21 — G1 EPIC probe BLOCKED (Colab vLLM 0.32)

- Command: `python scripts/g1_epic_probe.py --json`
- Env: Colab A100, vLLM **0.32.0** (`/usr/local/lib/python3.13/dist-packages/vllm`)
- Result: `epic_fork_detected: false`; 2879 files scanned; no `cache_fuse_metadata` / `hack_kv`
- Decision: **documented pin BLOCK** (runbook stop condition). Do not reinstall EPIC on this session.
  Stop Colab. Optional later: fresh session per `Docs/g1-epic.md`.

## 2026-10-22 — G1 matched-pin Gate C FAIL then PASS (bench fix)

- Env: vLLM **0.32.0**, lmcache **0.5.3**, torch **2.13.0+cu130** (still not a digest-matched image pin)
- First Gate C: `contains=0.42` — Qwen3 burned 32 tokens on meta-reasoning (not connector garbage)
- Fix: `/no_think`, max_tokens=96, stricter prompt, gold-span extract
- Gate C re-run: **PASS** `contains=1.0` `garbage=0.0`

## 2026-10-22 — G1 matched-pin Gate D PASS (blend quality)

- Blend `--engine-type blend`, reorder `bac` vs control extracted answers
- **PASS:** `contains=1.0` `garbage=0.0` `agree_with_control=1.0` (`gate_d True`)
- Decision: quality OK on this pin → proceed Stage E TTFT (n≥10); never cite prior voided 1.22×

## 2026-10-22 — G1 matched-pin Gate E FAIL (no TTFT win)

- Env: Colab A100, vLLM **0.32.0**, lmcache **0.5.3**, Qwen3-8B; n=10 after warmup
- Native warm-reorder p50 **297 ms**; blend warm-reorder p50 **326 ms** (blend **slower**, ratio 0.91)
- Native cold/warm/reorder all ~295–300 ms (no reorder gap at this prompt scale either)
- Blend cold/warm/reorder all ~323–336 ms (LMCache overhead, no reuse win visible)
- **Gate E FAIL** (need blend ≥15% faster than native reorder)
- Quality (D) PASS + latency (E) FAIL → non-prefix reuse not paying off at ~6k-ish filler scale on this pin
- Decision: bank as **G1 CacheBlend quality OK / latency miss**. Next: longer context (more filler / 80GB) **or** EPIC session — not ResolventKV kernels yet. Collect artifacts + stop Colab.

## 2026-10-22 — G1 matched-pin Gate E long FAIL (filler=4500)

- Same pin; `--filler-chars 4500`, n=10
- Native warm_abc p50 **311 ms**; warm_reorder p50 **309 ms** (ratio **0.99** — **no native reorder gap**)
- Blend warm_reorder p50 **362 ms** (slower than native; ratio 0.85 the wrong way)
- **Gate E FAIL** again. Caveat: without a native reorder penalty, Gate E is not a fair “close the gap” test — TTFT harness may not be producing prefix hits
- Decision: **stop `cw-matched`**. Offline: fix TTFT bench so native warm_abc ≪ warm_bac before another GPU latency run; else EPIC session. ResolventKV still deferred.
- Artifacts checked in: `artifacts/g1-matched-2026-10-22/`

## 2026-10-22 — Fix matched TTFT harness (offline)

- Root cause of flat Gate E: bench **seeded each order before measuring it**, so
  `warm_bac` was a self-hit, not a reorder miss; cold used a **trailing** nonce
  (still a huge prefix hit)
- Fix in `scripts/g1_matched_ttft_bench.py`: seed ABC once → warm_abc → bac/cba
  **without** seeding → cold with **leading** nonce; distinct per-doc fillers;
  report `harness_reorder_gap_ok` (reorder ≥1.15× warm ABC)
- Next GPU: native_prefix only until `harness_reorder_gap_ok`, then blend Gate E
- **Session policy:** reuse existing Colab session by default; `colab new` only on
  user request, dead session, or incompatible stack (EPIC)

## 2026-10-22 — G1 matched-pin CacheBlend pre-registration (before GPU)

- Host: **fresh Colab** (pip-match to `lmcache/vllm-openai:v0.5.3` era — not Docker digest)
- Model: `Qwen/Qwen3-8B`
- Path: MP `lmcache server` + `LMCacheMPConnector`; control=`--engine-type default`, blend=`blend`
- Flags: `--http-port 18080`, `--supported-transfer-mode lmcache_driven`, ready ≤90s
- Harness: `Docs/g1-matched-colab.md` + runbook in `Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`
- **Pre-registered outcomes:**
  - Gate C fail → pin/config BLOCK; stop; do not conclude CacheBlend quality
  - Gate D fail (C ok) → **real quality negative** on this pin; no param rescue this session
  - Gate D pass + Gate E fail → quality OK, no ≥15% reorder TTFT win at this scale
  - Both D+E pass → G1 CacheBlend provisional PASS
- Void: prior 1.22× MP latency (quality fail) — do not cite

## 2026-10-21 — G1 Colab pin closeout (`cw-smoke` stopped)

**Stack:** Colab A100-40GB, vLLM **0.32.0**, lmcache **0.5.6**, `Qwen/Qwen3-8B`

| Step | Result |
|---|---|
| Smoke | **PASS** |
| Full vs prefix TTFT | **PASS** — **2.57×** @ ~6k shared tokens |
| Answer preservation | **PASS** |
| Reorder gap (native prefix) | **PASS** — **1.25×** slower on reorder; answers OK |
| CacheBlend in-process | **BLOCKED** — `IndexError` dim 4 in `batched_from_gpu` |
| CacheBlend MP blend | **Provisional** — **1.22×** warm reorder TTFT; **quality FAIL** |
| EPIC | **BLOCKED** — stock vLLM, no LegoLink fork markers |

**Residual:** Non-prefix repair is **not** cleanly reproduced on this pin. That is a *pin/environment* gap, not proof that CacheBlend/EPIC fail after a fair run — do **not** open ResolventKV kernels yet.

**Next GPU (one session, pick one):** matched `lmcache/vllm-openai` quality-gated CacheBlend, **or** dedicated DerekHJH/epic install (`Docs/g1-epic.md`).

**Session:** `cw-smoke` stopped 2026-10-21; VM wiped — artifacts live in git + any downloaded JSON.


## 2026-10-22 — Native TTFT: prefix works; reorder median was polluted

- At ~6000 tokens: `cold_vs_warm≈2.59×` (prefix caching real); `reorder_vs_warm≈1.00` false
- Cause: after first BAC measure, trials 2..N were **BAC self-hits**; p50 hid the miss (p90 was higher)
- Fix: `reset_prefix_cache` → seed ABC → measure reorder, each trial

## 2026-10-22 — Native TTFT harness PASS (~6k tokens)

- `warm_abc` p50 **251 ms**; `warm_reorder` p50 **646–647 ms**; `cold` **658 ms**
- `reorder_vs_warm_abc≈2.57×`; `cold_vs_warm≈2.62×`; `prefix_cache_reset_ok`; **harness_ok True**
- Next: same-session blend Gate E vs this native reorder baseline

## 2026-10-22 — Matched Gate E FAIL (fixed harness, ~6k)

- Native warm_reorder p50 **646 ms**; blend warm_reorder p50 **709 ms** (ratio **0.91×**, slower)
- Blend: warm_abc **716** / reorder **707–710** / cold **967** — flat across orders; connector+eager overhead vs native warm **251**
- Gate D already PASS; **Gate E FAIL** (≥15% faster than native reorder not met)
- Runbook path: D✓ E✗ at this scale on A100-40 / vLLM 0.32 / lmcache MP blend — longer context needs ~80GB; do not open ResolventKV
- Matched CacheBlend G1 branch **closed** at ~6k; same-session follow-up: longer-context Gate E (~12k) before concluding scale

## 2026-10-22 — Gate E @12k false PASS voided (blend self-hits)

- Native @12k: warm **279** / reorder **~1055** / cold **1065**; gap **3.79×**; harness_ok True
- Blend reported gate_e True (801 vs 1055, 1.32×) but **polluted**: bac/cba trial1 **~1400** (≈cold), trials 2–10 **~800**; `reset_prefix_cache` failed (blocks not freed)
- Fair first-sample reorder **~1401** vs native **1055** → **slower**; do not cite 1.32×
- Fix: blend reorder trials use unique filler salt so LMCache cannot BAC self-hit; re-run blend @12k

## 2026-10-22 — Gate E @12k FAIL (salted harness, fair)

- Native reorder p50 **1055 ms**; blend reorder p50 **1391 ms** (ratio **0.76×**, slower)
- Blend: warm_abc **801** / reorder **~1390** / cold **1415**; `polluted False`; bac samples stable ~1376–1397
- **Gate E FAIL** at ~12k on A100-40 / this pin — non-prefix reuse not paying off vs native prefix miss
- Matched CacheBlend G1 **closed** (C/D✓ E✗ @6k and @12k fair). Optional later: EPIC on a **new** session

## 2026-10-22 — Stage E protocol fix: chunk+separator (pending GPU)

- Hypothesis: markdown concat shifted 256-token LMCache boundaries → blend reorder≈cold; fix = MP-style `" # # "` chunk join for **both** backends
- Harness: `scripts/g1_matched_ttft_bench.py` `prompt_format=chunk_sep`; runner `scripts/g1_matched_ttft_chunk_e.sh`
- Prior markdown Gate E FAILs remain valid as no-reuse evidence; do not delete
- Next: same-session `bash scripts/g1_matched_ttft_chunk_e.sh` → bank `*_12k_chunks.json`

## 2026-10-22 — Gate E @12k chunk_sep FAIL (reuse still absent)

- Native: warm **250** / reorder **1173** / cold **1175**; gap **4.68×**; harness_ok True; `chunk_tokens=3981`
- Blend: warm **776** / reorder **1503** / cold **1507**; polluted False; reorder≈cold (**no CacheBlend hit**)
- Gate E: blend 1503 vs native 1173 → **0.78×** (**FAIL**)
- Conclusion on this pin: chunk+sep format did not unlock non-prefix reuse vs native; stop chasing E here; EPIC needs a **new** session

## Template for future entries

```
## YYYY-MM-DD — <title>
- Hypothesis / gate:
- Environment (CPU/GPU, drivers, pins):
- Command:
- Result:
- Decision:
```
