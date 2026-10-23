# G1 CacheBlend Matched-Image Session: Agent Runbook

**Project:** ContextWeave (non-prefix KV cache reuse for RAG)
**Goal of this session:** Get ONE fair, quality-gated CacheBlend run on a matched `lmcache/vllm-openai` image, so we can tell whether CacheBlend actually preserves answers and gives a real TTFT win on non-prefix (reordered) context.
**Not the goal:** Debugging pin issues live, trying EPIC, or touching ResolventKV kernels.

---

## 0. Context (read first)

### What is already established (do not redo)
Env of previous runs: Colab A100-40GB, vLLM 0.32.0, lmcache 0.5.6, `Qwen/Qwen3-8B`.

| Step | Result |
|---|---|
| Smoke | PASS |
| Full prefill vs native prefix cache TTFT | PASS, 2.57x at ~6k shared prefix tokens (638.7 ms vs 248.9 ms, n=3) |
| Answer preservation, prefix reuse | PASS (contains_rate 1.0 for both modes) |
| Reorder gap, native prefix cache | PASS, ABC warm 330 ms vs BCA reorder 412 ms = 1.25x slower; answers correct |
| CacheBlend in-process (`LMCacheConnectorV1`) | BLOCKED: `IndexError: Dimension out of range` in `batched_from_gpu` (KV layout mismatch vs vLLM 0.32) |
| CacheBlend MP (`lmcache server --engine-type blend` + `LMCacheMPConnector`) | Latency 1.22x (warm p50 821 ms vs cold 1005 ms) but **quality FAIL** (echo / `# #` garbage, invented questions) |
| EPIC | BLOCKED: needs DerekHJH/epic vLLM ~0.7 fork (torch 2.5.1), incompatible with the 0.32 stack |

### How to interpret the above
- The 1.22x blend number is **NOT valid evidence**. Decode corruption can fake a latency win. Never cite it as a result.
- The reorder gap (1.25x) is the thing CacheBlend/EPIC are meant to close. It is real on this workload.
- Prior failures look like pin/environment mismatch, not proof that CacheBlend fails. This session exists to test that fairly.

### Known weaknesses to fix in this session
- n=3 for p50s is too thin. Use n >= 10 after a discarded warmup.
- Quality bench was only 3 cases and used a first-line scorer, then raw normalized string compare (gave a misleading 0.67 agree rate). Use answer extraction, more cases.
- Colab port 8080 was already in use. Use `--http-port 18080` (or another free port) for any `lmcache server`.
- `lmcache server` blend init is slow. Poll up to ~90 s for ready; the ready line is `LMCache ZMQ cache server is running`. Do not kill a server that is still initializing.
- MP mode needs `--supported-transfer-mode lmcache_driven` (previously used).

---

## 1. Rules for the agent

1. **Do not `pip install` over a working stack.** Everything runs inside the pinned container image. If a package is missing, stop and log it.
2. **Stages are gates.** Do not proceed to the next stage if the current gate fails. Log and stop.
3. **Do not debug live on GPU time.** GPU time is for measurement. If something fails twice with no new idea, log it as a BLOCK and stop.
4. **Log everything** using the template in section 9, including failures. Negative results are results.
5. **Never claim a latency number if quality failed.**
6. **Hard time cap: 90 minutes** of GPU session. At the cap, save artifacts, log status, terminate.
7. **Always terminate the GPU instance at the end** and confirm it is stopped. Report this explicitly.
8. Do not modify gate thresholds mid-run. If a threshold seems wrong, finish the run, then propose a change in the log.
9. Don't invent results. If a command wasn't run, say "not run".

---

## 2. Stage A: Pre-session prep (CPU only, no GPU, free)

Do all of this BEFORE starting a GPU session.

### A1. Choose and record the image pin
- Identify the `lmcache/vllm-openai` image tag to use. Prefer a tag whose bundled vLLM and lmcache versions are documented together.
- Check LMCache docs / GitHub issues/examples for a CacheBlend example that matches that tag (flags, env vars, model support). Record the link.
- **Warning sign:** if no CacheBlend example exists for that tag, or the docs say blending requires a different vLLM version, pick a different tag or log a BLOCK before renting.
- Write into the experiment log, before launching:
  - Image tag (full digest if possible)
  - vLLM version, lmcache version, torch version, CUDA version
  - Exact blend flags/env vars from the docs (e.g. `LMCACHE_ENABLE_BLENDING`, blend engine type, transfer mode)
  - Model: `Qwen/Qwen3-8B` (Qwen3 has `rope_scaling: null`, which is why it is preferred)

### A2. Upgrade the quality bench (`scripts/g1/cacheblend/g1_quality_bench.py`)
Requirements:
- At least **10 cases** (target 12-20).
- Each case: several documents with distinct ids (e.g. `DOC-A7`) and planted facts; a question whose gold answer is a short extractable string (a year, city name, doc id).
- Include cases that **require citing the document id**, because prior blend output failed exactly there (echo / garbage instead of ids).
- **Answer extraction, not raw string compare:** normalize (lowercase, strip punctuation/whitespace), and score via `gold in output` plus an exact-match-on-extracted-answer metric. Handle thinking tags (`<think>`) if Qwen3 emits them: either disable thinking or strip it before scoring.
- Use temperature 0 / greedy decoding, fixed max_tokens.
- Output JSON with per-case: prompt order, raw output, extracted answer, gold, contains, agrees_with_control.
- Metrics reported: `contains_rate`, `agree_with_control_rate` (extracted-answer agreement vs control), `garbage_rate` (outputs that are empty, pure echo, or contain no gold and no coherent answer).
- Must support a `--mode` flag: `control` (LMCache connected, blending OFF) and `blend` (blending ON), plus ability to run documents in original order and reordered.

### A3. Upgrade the TTFT bench (`scripts/g1/cacheblend/g1_reorder_gap_bench.py` or new)
- Measure TTFT with streaming (time to first token), not total latency.
- Scenarios, each with **1 discarded warmup + n >= 10 measured runs**, report p50 and p90:
  1. Cold ABC (first time, nothing cached)
  2. Warm ABC (exact prefix hit)
  3. Warm BAC (reorder)
  4. Warm CBA (reorder)
- Use distinct document sets per repetition where needed so a single cached item does not contaminate repeated measurements; document how cache state is managed between runs.
- Shared context ~6000 tokens total (matches the earlier prefix benchmark), `max_model_len 8192`.
- Also support a native-prefix-cache-only mode (no LMCache) to re-measure the 1.25x baseline with n >= 10 in the same session, so comparisons are apples to apples.
- Output JSON.

### A4. Scripts to prepare
- `scripts/g1/matched/g1_matched_smoke.sh`: launches the container's vLLM, waits for ready (poll, timeout 120 s), sends one request, checks sane output.
- `scripts/g1/matched/g1_matched_blend.sh`: launches with blend flags per the docs; polls readiness up to 90 s; refuses to continue if the server process dies; kills nothing that is still initializing.
- A single `scripts/g1/matched/g1_collect_artifacts.sh` that tars all JSON outputs + logs into one file for download.
- Dry-run the Python scripts on CPU where possible (syntax, argument parsing, scorer unit tests with fabricated outputs, including a garbage-output case that must score as failure).

### A5. Pre-registration (write before the run)
Write in the log, before any GPU time, what outcome means what. Suggested:
- Control quality < 90% contains: connector/image problem; stop (Stage C gate).
- Blend agreement with control >= 90% and garbage_rate ~ 0: quality PASS, proceed to latency.
- Blend agreement < 90% or any systematic garbage: **real quality result on this image**, log it as such; do not tune blend params to rescue it during this session.
- Latency PASS heuristic: warm BAC/CBA p50 at least 15% faster than the native-prefix reorder p50 measured in the same session.

---

## 3. Stage B: Launch and smoke

1. Start the GPU instance (A100 40GB acceptable for Qwen3-8B at 8k context; 80GB only if memory errors appear). Record: GPU model, driver, CUDA.
2. Pull/run the pinned image. Record `vllm --version`, `pip show lmcache`, `python -c "import torch; print(torch.__version__)"`.
3. Run `g1_matched_smoke.sh` (plain vLLM, prefix caching on, no LMCache).
   - **Gate B:** server ready, one request returns coherent output (e.g. contains `smoke-ok` or a sane answer). If not, stop and log BLOCK.
4. Record model load size and KV cache budget from the logs.

---

## 4. Stage C: Control (LMCache connected, blending OFF)

Purpose: determine whether LMCache connector itself produces sane output on this image. This isolates the connector from blending.

1. Start vLLM with the LMCache connector as documented, **blending disabled**.
2. Run the upgraded quality bench in `--mode control`, original document order.
3. Record contains_rate and garbage_rate.

**Gate C:** `contains_rate >= 0.9` and `garbage_rate` ≈ 0.
- Pass: continue to Stage D.
- Fail: the connector is broken or misconfigured on this image. **Stop.** Log as pin/config BLOCK with raw outputs. Do not try blend.

---

## 5. Stage D: Blend quality (the main gate)

1. Restart with **blending enabled**, per the pinned docs. Use `--http-port 18080` or another free port for any lmcache server. Poll readiness up to 90 s. Confirm the server stays alive.
2. Run the quality bench in `--mode blend`:
   - Pass 1: cold order ABC-style (populates cache).
   - Pass 2: reordered (BAC / CBA style), which is the actual non-prefix reuse case.
3. Compute, per case, agreement of the extracted answer versus the control run's extracted answer for the same prompt, plus contains vs gold.

**Gate D:** `agree_with_control_rate >= 0.9`, `contains_rate >= 0.9`, `garbage_rate` ≈ 0.

- **If Gate D fails: STOP. Do not run latency.** Save raw outputs for 3-5 failing cases. Log as "CacheBlend quality FAIL on matched image". This is a legitimate negative result, not a pin issue (control passed).
- Do not tune blend ratio / recompute ratio etc. to rescue it in this session. Log which parameters were used and suggest sweeps for a later session.
- Optional, only if time remains and Gate D failed: one single run with the most conservative blend parameter documented (highest recompute ratio), to see if quality is recoverable at all. Log it separately, clearly labeled exploratory.

---

## 6. Stage E: Latency (only if Gate D passed)

Run the upgraded TTFT bench, n >= 10 per scenario after 1 discarded warmup:

| Scenario | Config |
|---|---|
| Cold ABC | blend on |
| Warm ABC | blend on |
| Warm BAC | blend on |
| Warm CBA | blend on |
| Warm ABC / BAC / CBA | native prefix cache only (re-measure baseline in same session) |

Report p50 and p90 for each. Compute:
- Blend reorder speedup vs blend cold.
- Blend reorder vs native-prefix reorder (the meaningful comparison).
- Slowdown of native reorder vs native warm prefix (re-check the 1.25x).

**Gate E (latency heuristic):** blend warm reorder p50 at least 15% lower than native-prefix reorder p50. Also report variance; if p90/p50 spread is large, say the result is noisy.

Run a **post-latency quality spot check**: re-run a subset (e.g. 5 cases) of the quality bench after the latency runs to confirm outputs didn't degrade over time/cache pressure.

---

## 7. Stage F: Closeout

1. Run `g1_collect_artifacts.sh`, download the tarball (JSON, logs, scripts, environment dump). Verify the download completed before terminating.
2. **Terminate the instance**; confirm status is stopped/terminated. Record end time and approx cost.
3. Fill the log entry (section 9) and the summary table (section 8).
4. Recommend exactly one next step (see section 10).

---

## 8. Final summary table (fill in)

| Item | Value |
|---|---|
| Image tag / digest | |
| vLLM / lmcache / torch / CUDA | |
| GPU | |
| Smoke | PASS / FAIL |
| Control contains_rate / garbage_rate | |
| Blend contains_rate / agree_with_control / garbage_rate | |
| Gate D | PASS / FAIL |
| Native prefix warm (p50, p90, n) | |
| Native prefix reorder (p50, p90, n) | |
| Blend warm ABC / BAC / CBA (p50, p90, n) | |
| Blend reorder vs native reorder | % |
| Gate E | PASS / FAIL / NOT RUN |
| Session length, approx cost, instance terminated? | |

---

## 9. Log entry template (append to Experiment Log)

```
## YYYY-MM-DD: G1 matched-image CacheBlend
- Hypothesis / gate: CacheBlend preserves answers (Gate D) and cuts reorder TTFT >=15% vs native prefix (Gate E) on a matched image.
- Environment: GPU, driver, CUDA, image tag/digest, vLLM, lmcache, torch, model
- Blend flags / env vars:
- Commands:
- Smoke (Gate B):
- Control quality (Gate C): contains / garbage
- Blend quality (Gate D): contains / agree_with_control / garbage; failing-case notes
- Latency (Gate E): table with p50/p90/n, or NOT RUN (reason)
- Native prefix baseline re-measure:
- Anomalies / errors (with exact messages):
- Decision:
- Instance terminated: yes/no, time
```

---

## 10. Decision tree (after the session)

- **Gate C failed** (control broken): image/config problem. Next: try a different matched tag, or the dedicated EPIC fork session (`Docs/gates/g1/g1-epic.md`). Do not conclude anything about CacheBlend.
- **Gate D failed** (control OK, blend garbage/disagrees): real negative result for CacheBlend as shipped on Qwen3-8B. Next: decide whether to (a) sweep blend recompute ratio in one more session, (b) go to EPIC, or (c) report the negative result and reconsider ResolventKV as a post-G1 candidate. **Decide the project impact of this outcome before the run, not after.**
- **Gate D passed, Gate E failed** (quality OK, no real speedup): non-prefix reuse isn't paying off at this scale on this stack; consider longer contexts (needs 80GB) before concluding.
- **Both passed:** G1 CacheBlend provisional PASS. Next: scale n, more documents, longer contexts, then proceed per the PRD's gate sequence. ResolventKV kernels still only after G1 is formally closed.

---

## 11. Common failure notes (from prior sessions)

- `IndexError: Dimension out of range (expected [-4, 3], but got 4)` in `batched_from_gpu` during `save_kv_layer`: KV layout / layerwise connector mismatch vs the vLLM version. Fix by using a matched image, not by monkeypatching.
- `address already in use` on port 8080: use `--http-port 18080`.
- Server killed ~4 s after launch because ready string wasn't logged yet: poll up to 90 s; ready line is `LMCache ZMQ cache server is running`.
- vLLM MP worker hangs on first generate (`mq_timeout=300`) when the lmcache server died: check the server process is alive before sending requests, fail fast.
- Do not install the EPIC fork into this environment; it requires vLLM ~0.7 / torch 2.5.1.
