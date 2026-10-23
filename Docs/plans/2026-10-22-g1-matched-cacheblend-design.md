# G1 Matched-Pin CacheBlend — Design

**Date:** 2026-10-22  
**Status:** Approved (Approach 1: Colab pip-match to `lmcache/vllm-openai:v0.5.3` era)  
**Runbook:** `Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`

## Goal

One fair, quality-gated CacheBlend measurement on Colab using a **pip-matched** pin (`lmcache==0.5.3` + recorded sibling vLLM/torch), so G1 can close CacheBlend without citing the voided 1.22× quality-fail result.

## Non-goals

- Docker on Colab (optional 5‑min probe only; not required)
- EPIC fork install
- ResolventKV kernels
- Mid-session blend-param sweeps to rescue Gate D

## Architecture

```text
Stage A (CPU)          Stage B–F (Colab A100, ≤90 min)
  upgrade benches  →     B smoke (no LMCache)
  install/smoke/blend    C control (LMCache, blend OFF)
  scripts + pre-reg      D blend quality (reorder) ──fail→ STOP
                         E latency (only if D pass)
                         F collect + stop session
```

**Blend path:** `lmcache server --engine-type blend` + `LMCacheMPConnector`, `--http-port 18080`, `--supported-transfer-mode lmcache_driven`, ready poll ≤90s for `LMCache ZMQ cache server is running`.

**Label:** results are **matched pin on Colab**, not digest-pinned container. Record exact versions before measuring.

## Gates (pre-registered)

| Gate | Pass |
|---|---|
| C control | `contains_rate ≥ 0.9`, `garbage_rate ≈ 0` |
| D blend | same + `agree_with_control_rate ≥ 0.9` |
| E latency | blend warm-reorder p50 ≥15% faster than **same-session** native-prefix reorder p50 |

**Decisions:** C fail → pin BLOCK. D fail (C ok) → real quality negative. Never cite latency if D failed.

## Deliverables (Stage A)

- `scripts/g1/matched/g1_matched_quality_bench.py` — ≥10 cases, extract/score, control|blend
- `scripts/g1/matched/g1_matched_ttft_bench.py` — streaming TTFT, n≥10, p50/p90
- `scripts/g1/matched/g1_matched_install.sh`, `g1_matched_smoke.sh`, `g1_matched_blend.sh`, `g1_collect_artifacts.sh`
- Unit tests for scorer/garbage
- Experiment-log pre-registration + `Docs/gates/g1/g1-matched-colab.md`
