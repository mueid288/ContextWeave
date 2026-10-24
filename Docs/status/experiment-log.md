# Experiment Log

## Current verdict (update when it changes)

- **Research:** **ARCHIVED** — `Docs/status/closeout-phase0-1.md`
- **Product desk:** canonical chunk-order **PASS** (`by_frequency_desc` C1 amplification) — `Docs/product/canonical-order.md`
- G0 provisional PASS · G2/H3 FAIL · H4 MFU consistency only · FP conformance only
- Planner: **C1 else C0** + prefer frequency chunk order upstream
- Phase 2 / ResolventKV: **closed**; Colab idle
- Scoped writeup: `Docs/Reports/phase01-negative-results.md`

## Final verdict (scoped claims)

On A100-40GB, **Qwen3-8B**, vLLM 0.18 + lmcache 0.4.2 in-process blend (~12k,
chunk_sep, **4 shims**): BAC cached **7705**/11520 (Gate R bar **8063**, formal
miss ~66.9%); CBA ~0; blend BAC TTFT ~**622 ms** vs native reorder **924** /
CBA ~**1065**; mean ~**1.10×** hides quality loss on the fast order. Gate D bac
quality **0.67** (**N=12**). Report negative **for this config only**.

On **Mistral-7B** with EPIC LegoLink-8 **Python overlay** on vLLM 0.7.0 @~12k:
C3 is **faster** (~2–4× TTFT) but mean quality **0.70** (N=20) / **0.50** (N=12)
under reorder; oracle fallback to C0 → **no p95 upside** (G2 FAIL). Order-blind
multi-fact quality PASS is **superseded** for non-prefix quality claims.

Neither order nor (order, fact-type) predictors transferred across filler seeds.
H4 at 450 TFLOP/s was **misspecified**; measured C0 (~177–182 TFLOP/s) is
**consistent with** peak **312 × MFU 40–65%** — not a cost-model validation
(prior post hoc / wide; C0-only). FP suites = coded refusal only. G0 never saw
a real partner trace. Literature vs harness quality gap remains **unresolved**.

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
- Added `synthetic_rag_longctx` workload; baseline runner registry (`scripts/workloads/run_baseline.py`).
- Docs: `docs/runtime-pins.md` updated rent-gate checklist.

## 2026-10-11 — Real-trace importer + cost model (CPU)

- Added partner_v1 / text_approx importer (`scripts/workloads/import_trace.py`, `docs/trace-schema.md`).
- Added PRD §7.5 break-even cost model (`scripts/workloads/cost_model.py`).
- Still no GPU / no local model loads.
- Next human step: obtain a real partner JSONL (hashes + token counts or token ids).

## 2026-10-11 — Path C corpus replay

- Added `scripts/workloads/build_corpus_trace.py` + sample corpus under `benchmarks/corpora/sample_docs/`.
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
- Guide: `docs/cloud-gpu-rental.md`. Remote smoke script: `scripts/smoke/smoke_remote.sh`.
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
- Updated: `Docs/core/prior-art.md` (SAFE-KV / ATTUNER / Irminsul contracts), `Docs/core/assumptions.md`,
  `Docs/core/architecture.md`, `Docs/runbooks/gpu-runbook.md` Tier-1 quality slice
- Decision: keep Phase 0 path = smoke → CacheBlend/EPIC; ResolventKV is post-G1 candidate

## 2026-10-21 — Colab A100 smoke PASS

- Provider: Google Colab (Google AI Pro), session ephemeral
- GPU: **NVIDIA A100-SXM4-40GB** (driver 580.82.07, CUDA 13.0)
- Stack: vLLM **0.32.0**, torch 2.13.0, model `Qwen/Qwen3-8B`, max_model_len 4096
- Command: `CONTEXTWEAVE_ALLOW_MODEL_LOAD=1 bash scripts/smoke/smoke_remote.sh`
- Result: **SMOKE_PASS** (output contained `smoke-ok`; model load ~15.3 GiB, KV budget ~19.6 GiB)
- Decision: open G1 step 1 (`scripts/g1/cacheblend/g1_ttft_bench.py` — full vs prefix TTFT). CacheBlend deferred until step 1 saved.

## 2026-10-21 — G1 step 1 TTFT (short prefix; provisional)

- Command: `python scripts/g1/cacheblend/g1_ttft_bench.py --json` (defaults: `--doc-chars 3500`, max_model_len 4096)
- Shared prefix: **~1500 chars** (too short for a strong prefix-cache signal)
- full_prefill p50: **443.6 ms** (n=3)
- prefix_cache p50: **423.4 ms** (n=3)
- Speedup: **1.05×** (noise-level; not evidence for or against G1)
- Decision: re-run with token-budget sizing before interpreting; then CacheBlend

## 2026-10-21 — G1 step 1 TTFT (6k shared prefix) PASS

- Env: Colab A100-40GB, vLLM 0.32.0, `Qwen/Qwen3-8B`, max_model_len 8192
- Command: `python scripts/g1/cacheblend/g1_ttft_bench.py --target-prefix-tokens 6000 --max-model-len 8192 --json`
- Shared prefix: **6000 tokens** (~22007 chars)
- full_prefill p50: **638.7 ms** (n=3)
- prefix_cache p50: **248.9 ms** (n=3)
- Speedup: **2.57×**
- Decision: native prefix baseline is real on this stack. Next = LMCache CacheBlend (non-prefix) + answer-preservation slice.

## 2026-10-21 — G1 quality slice (first run; scorer too strict)

- Command: `python scripts/g1/cacheblend/g1_quality_bench.py --json`
- **modes_agree_rate: 1.0** (full vs prefix identical on all 3 cases) ← main preservation signal
- contains_rate reported 0.33 because scorer only looked at the first line; gold `2019` appeared later in the output
- Decision: treat agreement as provisional PASS for prefix answer preservation; fix scorer and re-score / re-run

## 2026-10-21 — G1 quality slice PASS

- Command: `python scripts/g1/cacheblend/g1_quality_bench.py --json` (fixed scorer)
- Env: Colab A100-40GB, vLLM 0.32.0, Qwen3-8B
- full_contains_rate: **1.0** / prefix_contains_rate: **1.0**
- modes_agree_rate: **0.67** (gamma both contain `2019` but normalized strings differ slightly)
- **pass_heuristic: true**
- Decision: prefix reuse preserves planted-fact answers on this stack. CacheBlend still blocked on pin.

## 2026-10-21 — G1 reorder gap PASS

- Command: `python scripts/g1/cacheblend/g1_reorder_gap_bench.py --json`
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
- Harness: `scripts/g1/epic/g1_epic_probe.py` (pin check), `g1_epic_install.sh` + `g1_epic_bench.py`
  (dedicated session only) — see `Docs/gates/g1/g1-epic.md`

## 2026-10-21 — G1 EPIC probe BLOCKED (Colab vLLM 0.32)

- Command: `python scripts/g1/epic/g1_epic_probe.py --json`
- Env: Colab A100, vLLM **0.32.0** (`/usr/local/lib/python3.13/dist-packages/vllm`)
- Result: `epic_fork_detected: false`; 2879 files scanned; no `cache_fuse_metadata` / `hack_kv`
- Decision: **documented pin BLOCK** (runbook stop condition). Do not reinstall EPIC on this session.
  Stop Colab. Optional later: fresh session per `Docs/gates/g1/g1-epic.md`.

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
- Fix in `scripts/g1/matched/g1_matched_ttft_bench.py`: seed ABC once → warm_abc → bac/cba
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
- Harness: `Docs/gates/g1/g1-matched-colab.md` + runbook in `Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`
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

**Next GPU (one session, pick one):** matched `lmcache/vllm-openai` quality-gated CacheBlend, **or** dedicated DerekHJH/epic install (`Docs/gates/g1/g1-epic.md`).

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
- Harness: `scripts/g1/matched/g1_matched_ttft_bench.py` `prompt_format=chunk_sep`; runner `scripts/g1/matched/g1_matched_ttft_chunk_e.sh`
- Prior markdown Gate E FAILs remain valid as no-reuse evidence; do not delete
- Next: same-session `bash scripts/g1/matched/g1_matched_ttft_chunk_e.sh` → bank `*_12k_chunks.json`

## 2026-10-22 — Gate E @12k chunk_sep FAIL (reuse still absent)

- Native: warm **250** / reorder **1173** / cold **1175**; gap **4.68×**; harness_ok True; `chunk_tokens=3981`
- Blend: warm **776** / reorder **1503** / cold **1507**; polluted False; reorder≈cold (**no CacheBlend hit**)
- Gate E: blend 1503 vs native 1173 → **0.78×** (**FAIL**)
- Conclusion on this pin: chunk+sep format did not unlock non-prefix reuse vs native; stop chasing E here; EPIC needs a **new** session

## 2026-10-22 — Antigravity Round-2 remediation (CPU)

- Review: `Docs/Reviews/antigravity_contextweave-deep-review-v2.md` — prior Gate D/E **confounded**
- Fixed: CRIT-5 `hash_build_context` (no chunk body); CRIT-4 blend.sh `--control-json`; CRIT-3 TTFT `max_tokens=1` + matched `enforce_eager` + CV; CRIT-2 blend client env + 256-aligned chunks; CRIT-1 quality `chunk_sep` + per-case ABC seed + multi-hop; MAJ-2 cold nonce after BOS; MAJ-4 scoring `<thinking>`/word-boundary; MAJ-6 install requires `VLLM_PIN`; MAJ-7/8 smoke+collect; MIN-1/5 hygiene
- **Status:** CacheBlend G1 evidence remains **CONFOUNDED** until a new GPU session re-runs fixed C/D/E on a true matched `VLLM_PIN`+blend stack
- Do not cite pre-remediation Gate D PASS / Gate E FAIL as algorithm verdicts

## 2026-10-22 — Colab Py3.13 blocks legacy vLLM 0.6.6.post1

- `pip install vllm==0.6.6.post1` fails on Colab Python 3.13 (`torchvision==0.20.1` unavailable)
- Install script now auto-selects `vllm==0.18.0` + `lmcache==0.4.2` on Py≥3.13

## 2026-10-22 — Post-remediation matched re-run (vLLM 0.18.0 / lmcache 0.4.2)

- **Status:** `INCONCLUSIVE` (engagement unproven) — supersedes prior “quality OK / latency miss”
- Env: Colab A100, Python 3.13, `Qwen/Qwen3-8B`; CuPy dual-wheel fixed; heartbeat 60s; `lmcache_driven`
- Engagement evidence: **none recorded** (no retrieved/cached token counts)
- Gate B: **PASS** (smoke `/no_think`)
- Gate C: control quality OK; Gate D “PASS” is **vacuous** without reuse proof
- Gate E @12k: native warm **39** / reorder **928** / cold **932**; blend warm **190** /
  reorder **948** / cold **953** — reorder≈cold≈native miss ⇒ **NO_REUSE pattern**
- Decision: do not interpret as algorithm latency miss; run G1-DIAG with Gate R

## 2026-10-22 — G1 EPIC on Colab via nested Python 3.11 (not a hard BLOCK)

- Fresh session: system Python **3.13** rejected by first install gate (torch 2.5.1)
- Workaround: `g1_epic_install.sh` bootstraps `/content/epic-venv` with **uv + CPython 3.11**,
  installs `torch==2.5.1+cu124`, then editable DerekHJH/epic (CUDA build)
- Do not install EPIC into system 3.13; activate venv before `g1_epic_bench.py`
- Status: pending GPU re-run with updated installer

## 2026-10-23 — EPIC full CUDA build too slow on Colab; prefer fast overlay

- Full `pip install -e epic` reached `[3/242]` (paged_attention) after long waits; Colab
  CPU-bound nvcc; session stopped for the day
- Mitigations already in full installer: `TORCH_CUDA_ARCH_LIST=8.0`, `MAX_JOBS=4`, nvcc apt
- **New preferred path:** `scripts/g1/epic/g1_epic_install_fast.sh` — install prebuilt `vllm==0.7.0`
  wheel, overlay EPIC `*.py` (LegoLink hooks are Python; fork tracks vLLM 0.7.0)
- Bench default model for EPIC: **Mistral-7B-Instruct-v0.2** (demo patches llama-family;
  Qwen3 unlikely)
- Fallback if fast probe fails: high-CPU host full build, or skip EPIC / close G1

## 2026-10-23 — G1 EPIC fast-path bench: quality OK / latency FAIL

- **Status:** `INCONCLUSIVE (toy scale)` — not a fair algorithm close
- Env: Colab A100, uv Py3.11 venv, `vllm==0.7.0` wheel + EPIC `*.py` overlay,
  `transformers<4.50`, `Mistral-7B-Instruct-v0.2`, recomp=8, n=5, filler≈2000 chars (~500 tok)
- full_prefill ~**235 ms**; kvlink-8 ~**332 ms**; speedup **0.71×**; gold OK
- Decision: do not cite as EPIC latency negative; only rerun at ≥6k/12k with same-stack
  native baseline **after** CacheBlend G1-DIAG, if still needed

## 2026-10-23 — Offline: FIX-1/2/3 + log relabel (CPU)

- **Status:** `VALID` (harness work)
- Relabeled Current verdict → INCONCLUSIVE; filled §6 project decision in review doc
- Added `scripts/g1/common/g1_engagement.py` (Gate R), `scripts/g1/common/g1_blend_alignment_audit.py` (FIX-2)
- TTFT bench records per-trial `num_cached_tokens` when exposed; `g1_matched_ttft_chunk_e.sh`
  skips Gate E interpretation unless Gate R is `REUSE_OK`
- Next GPU: **G1-DIAG** only (60 min cap) — engagement on reorder

## 2026-10-23 — Offline: CacheBlend Qwen3 support on lmcache 0.4.2

- **Status:** `VALID` (source check; no GPU)
- Hypothesis: prior “llama-only blend” claim would force a model switch for G1-DIAG
- Finding: **Qwen3 is supported on the pinned lmcache 0.4.2**
  - Issue [#1121](https://github.com/LMCache/LMCache/issues/1121) (“only llama”) closed via
    PR [#1633](https://github.com/LMCache/LMCache/pull/1633)
  - Tag `v0.4.2` ships `lmcache/v1/compute/models/qwen3.py` (`LMCQwen3Model`, q/k norm)
  - `infer_model_from_vllm` maps `Qwen3ForCausalLM` → `LMCQwen3Model` (also maps
    `Qwen2ForCausalLM` → `LMCLlamaModel`)
  - Docs: `docs/source/kv_cache_optimizations/blending.rst` + `examples/blend_kv_v1`
- Decision: **keep `Qwen/Qwen3-8B` for G1-DIAG**; do not switch to Llama/Mistral for
  model-support reasons. If Gate R still `ENGAGEMENT_FAIL`, treat as harness/config
  (alignment, `register_model`/#4131, MP vs in-worker blender), not missing Qwen3 adapter
- Next: G1-DIAG Colab ≤60 min, Gate R on reorder; record `pip freeze`

## 2026-10-23 — G1-DIAG: Gate R ENGAGEMENT_FAIL (got=0)

- **Status:** `INCONCLUSIVE` (harness/config; **not** algorithm negative)
- Env: Colab A100 `cw-g1-diag`, matched pin, `Qwen/Qwen3-8B`, chunk_sep 12k, n=10
- Gates: B PASS; D PASS (agree=1.0 — full prefill can still answer); **R FAIL**
  `got=0 need≥8063`; E correctly SKIPPED
- Engagement evidence: reorder `num_cached_tokens`/retrieved = **0**; latency agrees —
  blend warm_abc p50 **188** ms (same-order hit) vs warm_bac/cba/cold ≈ **947–955** ms
  (reorder ≡ cold miss). native_reorder ≈ 931 ms; speedup ≈ 0.98×
- polluted=False; prompt_format=chunk_sep
- Decision (pre-registered): treat as config/harness — MP `LMCacheMPConnector` +
  client `ENABLE_BLENDING` without proven in-worker `LMCBlender`/`register_model`
  (#4131). **One** fix then one DIAG re-run. Do not switch model; do not open EPIC
- Artifacts: session stopped **without** `g1_collect_artifacts.sh` — full JSONs /
  `pip freeze` unrecoverable. Banked paste reconstruction under
  `artifacts/g1-diag-2026-10-23/` (`artifact_kind=reconstructed_from_chat_paste`)
- Next: harness fix in tree → one DIAG re-run; collect tarball **before** stop

## 2026-10-23 — Harness: matched blend → in-process + register_model

- **Status:** `VALID` (harness; CPU-tested)
- Change: `scripts/g1/common/g1_blend_hooks.py`; matched quality/TTFT blend arm uses
  `LMCacheConnectorV1` + `VLLM_ENABLE_V1_MULTIPROCESSING=0` + `#4131` patch
- Shells: Gate D / Stage E no longer start `lmcache server --engine-type blend`
- Control (Gate C) still uses MP + default engine
- Next: push → Colab G1-DIAG #2 (Gate R only question); collect before stop

## 2026-10-23 — G1-DIAG #2: blender engages, then `vllm.attention` miss

- **Status:** `INCONCLUSIVE` (pin ABI; not algorithm)
- Progress vs DIAG #1: `Creating blender for vllm-instance` + import
  `LMCQwen3Model` — register_model / Qwen3 path **works**
- Block: lmcache **0.4.2** `from vllm.attention import Attention` vs vLLM **0.18**
  (Attention moved to `model_executor.layers.attention.attention`). Same error on
  quality blend and TTFT blend init
- Fix in tree: `ensure_vllm_attention_compat()` shim (lmcache ≥0.5.0 already has
  try/except). Retry blend without full reinstall after `git pull`
- Follow-on (same session): attention shim OK → next
  `ImportError: block_sparse_indices_to_vector_sparse_offsets` from eager
  `flash_infer_sparse` import in lmcache 0.4.2. Shimmed in
  `ensure_flashinfer_sparse_compat()` (sparse unused for our Gate R path)
- Risk after shims: same-class `IndexError` as 0.32 in-process (log if seen);
  if import moles continue, bump `LMCACHE_PIN=0.5.3` (lazy sparse) + reinstall
- Same session later: blender **inits**; case 1 dies
  `TypeError: Encoding objects of type ConstantList is unsupported` — exact
  LMCache [#2946](https://github.com/LMCache/LMCache/pull/2946) item. Patched
  `LMCacheLookupClient.lookup` → `list(token_ids)`; also alias
  `get_input_embeddings` → `embed_input_ids` at register_model

## 2026-10-23 — G1-DIAG #2 TTFT: engagement high, Gate R formal FAIL

- **Status:** `INCONCLUSIVE` → engagement **proven**; latency not Gate-E-eligible
- Env: Colab A100, in-process blend + shims (`a2d90a9`), Qwen3-8B, chunk_sep 12k, n=10
- Gate R: `ENGAGEMENT_FAIL` **got=7705 need≥8063** (≈**66.9%** of 3×3840=11520;
  bar is 70%). Contrast DIAG #1 got=**0**. Metric is from **warm_bac** only
- Engagement by order: bac cached_tokens_p50 **7705**; cba **19** (miss) — explains
  warm_cba p50 **1065** &gt; cold **930**
- Latency (blend): warm_abc **619**; warm_bac **622**; warm_cba **1065**; cold 930.
  native_reorder **924**; blend_reorder **844**; speedup **≈1.10×**. polluted=False
- Gate D (`blend bac`): **FAIL** contains/agree **0.67** (garbage 0) — quality hit
  when reorder engages
- Artifacts: `artifacts/g1-diag-2026-10-23/` (+ freeze + tarball); session stopped
- Decision: mechanism engaged; formal Gate R miss; CBA no-reuse + quality 0.67 are
  the binding issues. Do **not** claim Gate E
- Closeout: see following entry

## 2026-10-23 — G1 CacheBlend closeout (no recompute sweep)

- **Status:** `VALID` (project decision)
- **Scope:** this pin only (vLLM 0.18 + lmcache 0.4.2 in-process + shims listed in
  DIAG #2; Qwen3-8B; ~12k chunk_sep). Do **not** generalize to “CacheBlend fails.”
- **N:** Gate D bac quality **0.67** (small needle suite; log does not expand case
  count beyond Gate D artifacts); engagement N=10 TTFT; recompute ratio **not** swept
- **Shims:** attention import, flashinfer sparse, `ConstantList` lookup,
  `get_input_embeddings` alias (`a2d90a9`)
- Applied §6: quality fails when reuse engaged → real quality negative for this
  config; skip optional recompute-ratio curve; do not open ResolventKV / EPIC /
  further pin fishing for G1
- Report negative for: “PIC/CacheBlend wins quality-preserving TTFT on A100 @12k
  on vLLM 0.18 + lmcache 0.4.2”
- Artifacts committed under `artifacts/g1-diag-2026-10-23/`
- Pivot: fingerprint/provenance + cost-model / planner desk work

## 2026-10-23 — Desk pivot: thesis + planner v0

- **Status:** `VALID` (CPU)
- Added `Docs/status/g1-closeout-thesis.md` (H1/H2 restatement; go/pivot/stop = **pivot**)
- Added `contextweave.planner.v0` + tests: with G1 calibration, non-prefix → **C0**
  (C4 discarded for quality + &lt;15% latency bar); prefix → **C1**
- Doc: `Docs/core/planner-v0.md`

## 2026-10-23 — Cost model: measured A100 anchors

- **Status:** `VALID` (desk; not H4)
- Appended G1 TTFT ratios to `Docs/core/cost_model_8b.md` so planning tables are not
  mistaken for permission to select CacheBlend
- H4 (±20% cost-model vs measured) still deferred to Phase 2 if ever opened

## 2026-10-23 — Phase 0 exit decision (pivot)

- **Status:** `VALID` (project decision)
- Wrote `Docs/status/phase0-exit-decision.md`: **do not** open Phase 1/G2 or Phase 2/G3;
  ResolventKV remains blocked; optional GPU only under a new pre-reg
- Prior-art Tier 1 CacheBlend/EPIC rows updated with measured gaps

## 2026-10-23 — Sync README / overview / ResolventKV to pivot

- **Status:** `VALID` (docs)
- Top-level README, project-overview gates, and ResolventKV-adoption gate map
  now state **PIVOT** / kernels blocked so newcomers don’t treat G1 as “next GPU”

## 2026-10-23 — Park EPIC@12k pre-reg (no GPU)

- **Status:** `VALID` (desk)
- Wrote `Docs/pre-reg/pre-reg-epic-12k.md` — one question, 90 min cap, Mistral + fast path,
  ≥6k/12k scale; **PARKED** until owner starts a session. Partner still absent (OK)

## 2026-10-23 — Intentional project pause

- **Status:** `VALID` (project state)
- Owner accepted recommendation to **pause**. No further Phase 0 desk/GPU until a
  resume path is chosen (`Docs/status/pause.md`). Partner still none (non-blocking).

## 2026-10-23 — Resume path 2: EPIC@12k offline prep

- **Status:** `VALID` (desk)
- Pause lifted via resume path **2**. Added `--target-context-tokens` /
  `--out` / hard exit to `scripts/g1/epic/g1_epic_bench.py`; CPU tests
  `tests/unit/test_g1_epic_bench_scale.py` pass (3). Pre-reg CLI filled in.
- GPU session **not** started yet — next: `cw-epic-12k` per pre-reg.
- Supersedes: pause hold on EPIC lane only (CacheBlend stays CLOSED)

## 2026-10-23 — EPIC@12k pre-reg PASS (Colab A100)

- **Status:** `VALID`
- Session `cw-epic-12k`; Path A fast install; Mistral-7B-Instruct-v0.2;
  `--target-context-tokens 12000` → `prompt_tokens=12001`.
- Full prefill p50 **1021 ms** / p90 **1022 ms**; LegoLink-8 p50 **266 ms** /
  p90 **266 ms**; speedup **3.84×**; gold `Karachi` in both outputs;
  `pass_heuristic: true`.
- Artifacts: `artifacts/g1-epic-12k-2026-10-23/{g1_epic_12k.json,pip_freeze.txt}`.
- Planner: added **C3** calibration (`G1_EPIC_A100_12K`); C4 still refused.
- **Not** Phase 1 / ResolventKV open. Stop GPU when collect done.
- Supersedes: toy-scale EPIC INCONCLUSIVE; pre-reg PARKED/READY

## 2026-10-23 — EPIC multi-fact quality lane (desk)

- **Status:** `VALID` (desk)
- Next recommended task after push: broader EPIC quality before Phase 1.
- Added `--suite quality` (city/year/code) to `g1_epic_bench.py`; pre-reg
  `Docs/pre-reg/pre-reg-epic-quality.md`. CPU tests updated. GPU not started.
- Supersedes: “stay paused” as default next action

## 2026-10-23 — EPIC multi-fact quality PASS (Colab A100)

- **Status:** `VALID` — **order-blind; superseded by Phase 1 oracle** for non-prefix quality
- Session `cw-epic-quality`; `--suite quality` @ ~12k tokens; Mistral-7B-Instruct-v0.2.
- **N:** 3 fact cases (city/year/code); fixed chunk order (no permutations); n≥5/case
- city **3.86×**, year **2.19×**, code **1.98×**; contains_rate full/kvlink **1.0/1.0**;
  all cases latency_ok; `pass_heuristic: true`.
- Artifacts: `artifacts/g1-epic-quality-2026-10-23/`.
- Planner C3 notes + conservative ttft (1/1.98) updated. Phase 1 still not opened.
- Supersedes: quality pre-reg READY; single-gold-only C3 caveat
- Superseded by: Phase 1 oracle C3 mean_q **0.70** under order permutation (N=20)

## 2026-10-23 — Phase 1 GO (scoped) + oracle CPU harness

- **Status:** `VALID` (desk)
- Owner move → [`Docs/status/phase1-go-memo.md`](phase1-go-memo.md); G2 thresholds
  ratified; config set {C0,C1,C3}. Module `contextweave.oracle` +
  `scripts/phase1/run_oracle_study.py`; pre-reg
  `Docs/pre-reg/pre-reg-phase1-oracle.md`. GPU not started.
- Supersedes: pause-as-default after EPIC quality

## 2026-10-23 — Phase 1 oracle G2 FAIL (Colab A100)

- **Status:** `VALID`
- Session `cw-phase1-oracle`; N=20 @12k; C0 vs C3 (C1 infeasible).
- C0 mean_q **1.0**; C3 mean_q **0.70** (fails ACB_city / BAC_year ×3 each).
- Best fixed **C0**; oracle recovers q=1.0 via C0 fallback → p95 TTFT upside **0**;
  quality upside vs C0 **0** → `g2_pass: false`.
- Artifacts: `artifacts/phase1-oracle-2026-10-23/`.
- Planner: refuse C3 on quality risk (like C4); default C0 unless C1.
- **No Phase 2.** Thin policy around C0.
- Supersedes: “C3 preferred” planner calibration; EPIC as default PIC

## 2026-10-23 — Intentional pause after G2 closeout

- **Status:** `VALID` (project state)
- Stopped `cw-phase1-oracle` (was still billing). Wrote `Docs/status/closeout-g2.md`;
  parked H3 pre-reg (mean-TTFT only, not G2 redo). Default = stay paused.
- Supersedes: open-ended Phase 1 desk

## 2026-10-23 — H3 order-risk PASS (CPU replay)

- **Status:** `VALID` (desk)
- Rule: refuse C3 if `chunk_order` ∈ {ACB, BAC} else allow C3; unknown → refuse.
- On Phase1 oracle JSONL: precision/recall 1.0; policy mean_q 1.0; mean TTFT
  **40%** below always-C0. Not a G2 claim (p95 unused).
- Artifacts: `artifacts/h3-order-risk-2026-10-23/`. Module `contextweave.risk.order_signal`;
  planner `RequestView.chunk_order` wired. Phase 2 still closed.
- Supersedes: blanket C3 refuse after G2

## 2026-10-23 — H3 GPU confirm pre-reg (desk)

- **Status:** `VALID` (desk)
- Fresh golds (Lisbon/2021/BETA-4242) + filler-seed 99 collector
  `scripts/phase1/collect_h3_confirm.py`; pre-reg
  `Docs/pre-reg/pre-reg-h3-gpu-confirm.md`. GPU not started.
- Supersedes: in-sample-only H3 as final word

## 2026-10-23 — H3 GPU confirm FAIL (Colab A100)

- **Status:** `VALID`
- Session `cw-h3-confirm`; N=12; alt golds; C3 mean_q **0.5**; ACB/BAC rule
  precision **0.5** / policy mean_q **0.67** → `pass_heuristic: false`.
- Failures: CAB/CBA **code**, BAC **year**; ACB city OK (inverted vs Phase1).
- Artifacts: `artifacts/h3-confirm-2026-10-23/`. Planner reverts to blanket C3 refuse.
- Stopped Colab. **PAUSED.** No Phase 2.
- Supersedes: H3 order gate as production policy

## 2026-10-23 — H3 slice calibration PASS (CPU)

- **Status:** `VALID`
- Pre-reg `Docs/pre-reg/pre-reg-h3-slice-cal.md`. Workload-local
  `(order, fact_type)` LOO on Phase1 + confirm suites: prec **1.0**, mean_q **1.0**,
  mean TTFT red **41% / 34%**. Cross-suite transfer prec **0.33–0.50** (expected).
- Module `contextweave.risk.slice_calibration`; planner enables C3 only with table.
- Artifacts: `artifacts/h3-slice-cal-2026-10-23/`. **Unpaused** (desk). No Phase 2.
- Supersedes: “stay paused” default after order confirm FAIL

## 2026-10-23 — H3 slice-cal GPU confirm pre-reg (desk)

- **Status:** `VALID` (desk)
- Pre-reg `Docs/pre-reg/pre-reg-h3-slice-cal-gpu.md`: calibrate on seed-99 confirm
  table → serve filler-seed **100** same Lisbon/2021/BETA-4242 golds.
- Eval: `eval_h3_slice_cal.py --calibrate … --serve …`. Session `cw-h3-slice-cal`
  not started yet.
- Supersedes: slice-cal §Next “optional GPU” as unspecified

## 2026-10-23 — H3 slice-cal GPU confirm FAIL (Colab A100)

- **Status:** `VALID`
- Session `cw-h3-slice-cal`; seed 100 serve; apply seed-99 safe cells →
  prec **0.33**, policy_q **0.83**, TTFT red 28% → `pass_heuristic: false`.
- Flips: ABC/city 1→0; CAB/CBA code 0→1. Same golds ≠ transferable table.
- Artifacts: `artifacts/h3-slice-cal-gpu-2026-10-23/`. Stopped Colab. **PAUSED.**
- Supersedes: cross-filler reuse of slice-cal tables

## 2026-10-23 — H3 runtime keydev pre-reg (desk)

- **Status:** `VALID` (desk)
- Pre-reg `Docs/pre-reg/pre-reg-h3-keydev.md`: Layer-0 seam keydev (isolated vs
  joint), fit T on filler-seed 99, eval on seed 100 same Lisbon golds.
- Code: `contextweave.risk.keydev`, `collect_h3_keydev.py`, `eval_h3_keydev.py`,
  EPIC `_collect_and_link(..., return_keydev=True)`. Session not started.
- Supersedes: “stay paused” after slice-cal GPU FAIL

## 2026-10-23 — H3 runtime keydev FAIL (Colab A100)

- **Status:** `VALID`
- Session `cw-h3-keydev`; isolated-seam scores only (~3 order-tied values
  0.132–0.133); train fit **untrainable**; test prec 0.33 / TTFT red 0 → FAIL.
- Joint probe path previously CUDA-IMA’d (fixed to isolated-only). Stopped Colab.
- Artifacts: `artifacts/h3-keydev-2026-10-23/`. **PAUSED.**
- Supersedes: keydev as production C3 gate

## 2026-10-24 — H4 cost model FAIL (CPU vs banked)

- **Status:** `MISSPECIFIED, superseded`
- Pre-reg `Docs/pre-reg/pre-reg-h4-cost-model.md`. Default **450** TFLOP/s exceeds
  A100 dense bf16 peak (~312); large error was guaranteed. Pred ~457 ms vs C0
  ~1.13–1.16 s → rel err **~0.60** on 4 suites. Calibrated ~182 TFLOP/s → seed100
  ~2.9% (secondary only; same hardware family).
- Artifacts: `artifacts/h4-cost-model-2026-10-24/`.
- Supersedes: “H4 untested” in cost_model_8b.md
- Superseded by: H4 MFU-prior entry below

## 2026-10-24 — H4 MFU-prior check (CPU vs banked)

- **Status:** `VALID` — **consistent with MFU prior, not a validation** (do not label PASS)
- Pre-reg `Docs/pre-reg/pre-reg-h4-mfu.md`. Peak **312** TFLOP/s; MFU band
  **40–65%** → **[124.8, 202.8]**. Implied ≈ **177–182** TFLOP/s (MFU ~57–58%)
  on four banked C0 suites; in-band. Caveats: band chosen after ~58% seen;
  wide enough that most prefills fit; checks C0 FLOP/TTFT only (not load/C3
  break-even).
- N: 4 suites × banked C0 means (n_c0 12–20). No new GPU.
- Artifacts: `artifacts/h4-mfu-2026-10-24/`.
- Supersedes: misspecified H4 @450

## 2026-10-24 — FP planner provenance gate PASS (CPU)

- **Status:** `VALID` — **implementation conformance (self-authored)**; not security evidence
- Pre-reg `Docs/pre-reg/pre-reg-fp-planner-gate.md`. Non-prefix C3/C4 require
  FR-13 `assert_reuse_allowed` before quality clears. Tests:
  `tests/unit/test_planner_provenance_gate.py`. **PAUSED.**
- Supersedes: planner without provenance on non-prefix path

## 2026-10-24 — FP build-context poison suite PASS (CPU)

- **Status:** `VALID` — **implementation conformance (self-authored)**; not security evidence
- Pre-reg `Docs/pre-reg/pre-reg-fp-poison-suite.md`. 8/8 attacker-prefix cases
  refused (fingerprint + planner). `request_build_context_hash` wired.
- Artifacts: `artifacts/fp-poison-2026-10-24/`. **PAUSED.**
- Supersedes: planner ignoring build-hash vs provenance

## 2026-10-24 — FR fault-injection suite PASS + Phase0/1 closeout

- **Status:** `VALID` — **implementation conformance (self-authored)**; not security evidence
- Pre-reg `Docs/pre-reg/pre-reg-fp-fault-suite.md`: 7/7 faults refused; control C3 ok.
- Artifacts: `artifacts/fp-fault-2026-10-24/`. Closeout:
  `Docs/status/closeout-phase0-1.md`. **PAUSED / ARCHIVED.**
- Supersedes: open-ended FP micro-suite treadmill as default next

## 2026-10-24 — Shipped policy demo CLI (desk)

- **Status:** `VALID`
- `cw-plan-demo` / `contextweave.cli.plan_demo`: prints C1/C0/refuse-C3 scenarios
  for the archived policy. Not a gate reopen.
- Supersedes: none

## 2026-10-24 — CPU archive lock + tag

- **Status:** `VALID`
- `scripts/ci/cpu_gate.sh`: 142 unit tests + plan-demo. Tag
  `v0.1.0-phase01-archive` points at Phase 0/1 closeout. Not a gate reopen.
- Supersedes: none

## 2026-10-24 — Post-archive review gap fixes (CPU)

- **Status:** `VALID` (desk hygiene; not a gate reopen)
- Relabeled H4/FP/EPIC quality/CacheBlend; H4 MFU consistency check (not PASS);
  log template expanded; `Docs/Reports/phase01-negative-results.md`.
- Report revision: Gate D N=12; per-order TTFT; Gate R 7705/8063; oracle wording;
  pin-split native gaps; standalone can-claim; drop MFU “PASS”.
- Supersedes: overstated PASS/FAIL wording in Current verdict

## 2026-10-24 — Product: canonical chunk-order PASS (CPU)

- **Status:** `VALID`
- Pre-reg `Docs/pre-reg/pre-reg-product-canonical-order.md` (Gemini_4 fixes:
  frequency + sha256 baselines; KPI = prefix share / post_prefix; natural sort;
  multi-doc slice; lift bar ≥+10pp or ≥20% multi-doc post_prefix↓).
- `by_frequency_desc` vs natural: synthetic multi-doc **+14.4 pp** / **21%**↓;
  my_corpus **+15.5 pp** / **22.4%**↓ → `pass_heuristic: true` both.
- `by_doc_id` ≈ frequency (Zipf↔alpha coincidence); `by_sha256` multi-doc ~+5–6 pp.
- Module: `contextweave.trace_analysis.chunk_order`; CLI `--compare-chunk-order`.
- Artifacts: `artifacts/product-canonical-order-2026-10-24/`. Quality **unverified**.
- Supersedes: “R7 not run”; product desk idle

## Template for future entries

```
## YYYY-MM-DD — <title>
- Status: VALID | VOIDED | CONFOUNDED | INCONCLUSIVE | MISSPECIFIED
- Hypothesis / gate:
- Environment (CPU/GPU, drivers, pins, shims/patches applied):
- N cases / seeds / chunk orders covered:
- Engagement evidence: retrieved/cached tokens on reorder (or none)
- Command:
- Result:
- Artifacts collected before stop: yes/no (path)
- Decision:
- Supersedes: <entry or none>
```
