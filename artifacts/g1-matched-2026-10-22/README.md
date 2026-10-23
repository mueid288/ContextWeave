# G1 matched-pin CacheBlend artifacts (2026-10-22)

## Authoritative (post antigravity Round-2)

Session `cw-g1-r2`. Stack: Python **3.13**, vLLM **0.18.0**, lmcache **0.4.2**, torch **2.10+cu128**, `Qwen/Qwen3-8B`.

Dir: `post-remediation-20261022/` (also `g1_matched_artifacts_20261022T173602Z.tar.gz`).

| Result | Detail |
|---|---|
| Gate C | **PASS** `contains=1.0` |
| Gate D | **PASS** `agree=1.0` on bac |
| Gate E @12k chunk_sep | **FAIL** native reorder **928** ms / blend **948** ms (**0.98×**; need ≤0.85×) |

Cite these files for CacheBlend G1. Older root-level JSONs below are pre-remediation / confounded — do not cite as algorithm verdicts.

## Legacy (pre-remediation; confounded)

Colab session `cw-matched`. Stack: vLLM **0.32.0**, lmcache **0.5.3**.

| File | Role |
|---|---|
| `g1_matched_env.json` | Recorded package versions |
| `g1_matched_control.json` | Gate C PASS (`contains=1.0`) |
| `g1_matched_blend_abc.json` / `g1_matched_blend_bac.json` | Gate D PASS (`agree=1.0` on bac) |
| `g1_matched_ttft_*.json` | Gate E FAIL (short filler) |
| `g1_matched_ttft_*_long.json` | Gate E FAIL (filler=4500; native had no reorder gap) |
| `g1_ttft_native_fixed.json` | Native TTFT harness PASS (~6k; reorder≈2.57× warm ABC) |
| `g1_ttft_blend_fixed.json` | Gate E FAIL vs that baseline (blend reorder slower, 0.91×) |
| `g1_ttft_native_12k.json` | Native @~12k PASS (reorder≈3.79×) |
| `g1_ttft_blend_12k.json` | **VOID** — polluted p50 (self-hits); do not cite |
| `g1_ttft_blend_12k_salted.json` | Gate E FAIL fair (blend 1391 vs native 1055; 0.76×) |
| `g1_ttft_native_12k_chunks.json` | Native `chunk_sep` @~12k PASS (reorder≈4.68×) |
| `g1_ttft_blend_12k_chunks.json` | Gate E FAIL fair (blend 1503≈cold; 0.78× vs native 1173) |

Narrative: `Docs/status/experiment-log.md`. Runbook: `Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`.
