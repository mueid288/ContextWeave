# G1 on Google Colab (after smoke)

**Prereq:** smoke PASS on A100 (`SMOKE_PASS`). Keep the session only while actively measuring.

## Step 1 — Full prefill vs native prefix TTFT (now)

On the Colab GPU shell (repo at `/content/ContextWeave`):

```bash
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1

# Pull latest harness (after you push from the Mac), OR upload scripts/g1_ttft_bench.py
git pull
# if pull is not available yet, copy scripts/g1_ttft_bench.py onto the VM

python scripts/g1_ttft_bench.py --json | tee g1_ttft_qwen3.json
```

**Success:** JSON with `full_prefill` and `prefix_cache` p50 ms, and `prefix_vs_full_p50_speedup` > 1 on shared-prefix prompts.

Save `g1_ttft_qwen3.json` (download / Drive) before `colab stop`.

## Step 2 — Quality slice (next session OK)

Answer preservation vs full prefill on a multi-hop / Path C doc set. Not required to finish Step 1.

## Step 3 — LMCache + CacheBlend

Install LMCache only after Step 1 numbers are saved. Pins: `Docs/runtime-pins.md`.  
Abort if non-prefix hits stay zero (issue #3238 class failure).

## Step 4 — EPIC

1-week time-box; document failure if pins break on vLLM 0.32.

## Stop

When idle: `colab stop -s <session>` — VM disk is wiped; only GitHub + downloaded JSON survive.
