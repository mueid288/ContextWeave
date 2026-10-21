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

## Step 3 — LMCache + CacheBlend (non-prefix)

After Step 1 JSON is saved:

```bash
cd /content/ContextWeave
git fetch origin && git reset --hard origin/main

# Prefer not ripping out the working vLLM/torch stack
pip install lmcache
python -c "import lmcache; print('lmcache', lmcache.__version__)"

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export PYTHONHASHSEED=0
export VLLM_WORKER_MULTIPROC_METHOD=spawn
python scripts/g1_cacheblend_bench.py --json | tee g1_cacheblend.json
```

**Success:** `pass_heuristic: true` (warm reordered prompts ≥15% faster than cold A-B-C).  
**Fail / abort:** times ≈ equal → #3238-class pin failure; log it, do not expand matrix yet.

**2026-10-21 Colab result (vLLM 0.32.0 + lmcache 0.5.6):** **BLOCKED** after engine start —
`IndexError` in `batched_from_gpu` / `single_layer_kv_transfer` (dim 4). Do **not** keep
retrying this pair tonight. Next attempt: official `lmcache/vllm-openai` image or an older
documented vLLM↔LMCache pair (see `Docs/runtime-pins.md`).

**Known friction (handled in the bench script):** stock vLLM never calls
`VLLMModelTracker.register_model` (LMCache [#4131](https://github.com/LMCache/LMCache/issues/4131)).
Our script monkeypatches `GPUModelRunner.load_model` and sets
`VLLM_ENABLE_V1_MULTIPROCESSING=0` so blending can start.

If `import lmcache` breaks CUDA symbols against the installed torch, try:

```bash
pip install lmcache --no-deps
# then install any missing pure-Python deps the traceback names
```

## Step 4 — EPIC

1-week time-box; document failure if pins break on vLLM 0.32.

## Stop

When idle: `colab stop -s <session>` — VM disk is wiped; only GitHub + downloaded JSON survive.
