# G1 matched-pin CacheBlend on Colab

**Goal:** Fair quality-gated CacheBlend on a **pip-matched** pin (`lmcache==0.5.3` era), not the broken vLLM 0.32 + lmcache 0.5.6 stack.

Full agent law: [`Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`](Reviews/claude_g1_cacheblend_matched_image_runbook.md)  
Design: [`Docs/plans/2026-10-22-g1-matched-cacheblend-design.md`](plans/2026-10-22-g1-matched-cacheblend-design.md)

## Fresh session (≤90 min GPU)

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
# If Gate D PASS:
RUN_TTFT=1 bash scripts/g1_matched_blend.sh # or run ttft benches once
# Or:
# python scripts/g1_matched_ttft_bench.py --backend native_prefix --runs 10 --out g1_matched_ttft_native.json
# python scripts/g1_matched_ttft_bench.py --backend blend --runs 10 --out g1_matched_ttft_blend.json

bash scripts/g1_collect_artifacts.sh
# download the tarball, then:
colab stop -s <session>
```

## Gates

| Gate | Pass |
|---|---|
| B smoke | coherent `smoke-ok`-like output |
| C control | `contains_rate ≥ 0.9`, `garbage_rate ≤ 0.05` |
| D blend | C bars + `agree_with_control_rate ≥ 0.9` on reorder |
| E latency | blend warm-reorder p50 ≥15% faster than same-session native reorder |

**Never cite latency if Gate D failed.**
