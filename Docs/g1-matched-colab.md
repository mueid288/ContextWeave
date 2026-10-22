# G1 matched-pin CacheBlend on Colab

**Goal:** Fair quality-gated CacheBlend on a **pip-matched** pin (`lmcache==0.5.3` era), not the broken vLLM 0.32 + lmcache 0.5.6 stack.

Full agent law: [`Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`](Reviews/claude_g1_cacheblend_matched_image_runbook.md)  
Design: [`Docs/plans/2026-10-22-g1-matched-cacheblend-design.md`](plans/2026-10-22-g1-matched-cacheblend-design.md)

## Session policy (default)

**Reuse the same Colab session** whenever possible. Creating a new VM forces a full
`pip`/model reinstall. Only call `colab new` when the user asks, the old session is
gone/`not found`, or the requirement forces a different stack (e.g. EPIC fork).

```bash
colab sessions                    # see what is alive
colab console -s cw-matched       # reconnect (name may differ)
cd /content/ContextWeave && git pull
# skip g1_matched_install.sh if vllm/lmcache already match g1_matched_env.json
```

Stop only when idle for a long break or switching to an incompatible pin:
`colab stop -s <session>`.

## Fresh session (only if needed; ≤90 min GPU)

```bash
cd /content && git clone https://github.com/mueid288/ContextWeave.git
cd ContextWeave

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export CONTEXTWEAVE_ALLOW_MATCHED_REINSTALL=1
export SMOKE_MODEL=Qwen/Qwen3-8B
export PYTHONHASHSEED=0

chmod +x scripts/g1_matched_*.sh scripts/g1_collect_artifacts.sh
bash scripts/g1_matched_install.sh          # writes g1_matched_env.json
bash scripts/g1_matched_smoke.sh            # Gate B
bash scripts/g1_matched_blend.sh            # Gate C then D
# If Gate D PASS — Stage E uses **chunk+separator** prompts (not markdown concat):
bash scripts/g1_matched_ttft_chunk_e.sh
# Writes g1_ttft_native_12k_chunks.json + g1_ttft_blend_12k_chunks.json
# Gate E: blend warm_reorder ≤ 0.85 × native warm_reorder; polluted must be False

bash scripts/g1_collect_artifacts.sh
# download the tarball, then:
colab stop -s <session>
```

## Stage E / D prompt format (post antigravity Round-2)

- Quality + TTFT use **fixed token chunks** joined by `" # # "`, with
  `LMCACHE_ENABLE_BLENDING` / `LMCACHE_BLEND_SPECIAL_STR` on the **client** for blend.
- Chunk lengths are multiples of **256**. TTFT defaults to `--max-tokens 1` and the
  same `--enforce-eager` on both native and blend arms.
- Quality: each case does `reset → seed ABC → measure order+question` (no shared-body
  prefix hits across cases). Includes multi-hop cases.
- Install: `VLLM_PIN` is required (default `0.6.6.post1` with `lmcache==0.5.3`); do not
  leave Colab’s stock `vllm==0.32`.
- Pre-remediation artifacts under `artifacts/g1-matched-2026-10-22/` are **confounded** —
  re-run Gates C–E after `git pull` on a fresh matched install before citing results.

## Gates

| Gate | Pass |
|---|---|
| B smoke | coherent `smoke-ok`-like output |
| C control | `contains_rate ≥ 0.9`, `garbage_rate ≤ 0.05` |
| D blend | C bars + `agree_with_control_rate ≥ 0.9` on reorder |
| E latency | blend warm-reorder p50 ≥15% faster than same-session native reorder (chunk_sep) |

**Never cite latency if Gate D failed.**
