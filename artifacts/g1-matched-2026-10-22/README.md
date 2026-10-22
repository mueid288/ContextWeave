# G1 matched-pin CacheBlend artifacts (2026-10-22)

Colab A100 session `cw-matched`. Stack: vLLM **0.32.0**, lmcache **0.5.3**, `Qwen/Qwen3-8B`.

| File | Role |
|---|---|
| `g1_matched_env.json` | Recorded package versions |
| `g1_matched_control.json` | Gate C PASS (`contains=1.0`) |
| `g1_matched_blend_abc.json` / `g1_matched_blend_bac.json` | Gate D PASS (`agree=1.0` on bac) |
| `g1_matched_ttft_*.json` | Gate E FAIL (short filler) |
| `g1_matched_ttft_*_long.json` | Gate E FAIL (filler=4500; native had no reorder gap) |

Narrative: `Docs/experiment-log.md` (2026-10-22 matched-pin entries).  
Runbook: `Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`.
