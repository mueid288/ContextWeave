# G1 on Google Colab (after smoke)

**Prereq:** smoke PASS on A100 (`SMOKE_PASS`). Keep the session only while actively measuring.

## Step 1 — Full prefill vs native prefix TTFT (now)

On the Colab GPU shell (repo at `/content/ContextWeave`):

```bash
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1

# Pull latest harness (after you push from the Mac), OR upload scripts/g1/cacheblend/g1_ttft_bench.py
git pull
# if pull is not available yet, copy scripts/g1/cacheblend/g1_ttft_bench.py onto the VM

python scripts/g1/cacheblend/g1_ttft_bench.py --json | tee g1_ttft_qwen3.json
```

**Success:** JSON with `full_prefill` and `prefix_cache` p50 ms, and `prefix_vs_full_p50_speedup` > 1 on shared-prefix prompts.

Save `g1_ttft_qwen3.json` (download / Drive) before `colab stop`.

## Step 2 — Quality slice (run on the working vLLM stack — no LMCache)

After Step 1 (and while CacheBlend is blocked on this pin):

```bash
cd /content/ContextWeave
git fetch origin && git reset --hard origin/main

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
python scripts/g1/cacheblend/g1_quality_bench.py --json | tee g1_quality.json
```

**Success:** `pass_heuristic: true` (full finds gold on ≥2/3 cases; prefix agrees with full on ≥2/3).

## Step 2b — Reorder gap (no LMCache; run while CacheBlend is blocked)

Shows that **reordered** docs stay correct under full compute but lose the warm
prefix-cache TTFT win — the gap CacheBlend is supposed to close.

```bash
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
python scripts/g1/cacheblend/g1_reorder_gap_bench.py --json | tee g1_reorder_gap.json
```

**Success:** `pass_heuristic: true` (both orders contain gold; BCA ≥15% slower than warm ABC).

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
python scripts/g1/cacheblend/g1_cacheblend_bench.py --json | tee g1_cacheblend.json
```

**Success:** `pass_heuristic: true` (warm reordered prompts ≥15% faster than cold A-B-C).  
**Fail / abort:** times ≈ equal → #3238-class pin failure; log it, do not expand matrix yet.

**2026-10-21 Colab result (vLLM 0.32.0 + lmcache 0.5.6, in-process):** **BLOCKED** —
`IndexError` in `batched_from_gpu` (dim 4).

**2026-10-21 Colab result (same pins, MP blend):** **provisional latency / quality FAIL** —
cold 1005 ms → warm p50 821 ms (**1.22×**); outputs wrong / separator echo. Do not expand matrix on this.

```bash
# Already run; only re-run after pin change
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
bash scripts/g1/cacheblend/g1_cacheblend_mp.sh
```

Next session: EPIC, or matched `lmcache/vllm-openai` image for a quality-gated CacheBlend check
(see `Docs/runbooks/runtime-pins.md`). Stop idle Colab: `colab stop -s cw-smoke`.

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

EPIC is a **vLLM ~0.7 fork**, not compatible with this Colab pin. Full procedure:
[`Docs/gates/g1/g1-epic.md`](g1-epic.md).

On the **current** session (bank documented BLOCK):

```bash
cd /content/ContextWeave && git pull
python scripts/g1/epic/g1_epic_probe.py --json | tee g1_epic_probe.json
```

Expected: `epic_fork_detected: false`. Then stop Colab. Optional later: fresh session +
`CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1 bash scripts/g1/epic/g1_epic_install.sh`.

## Stop

When idle: `colab stop -s <session>` — VM disk is wiped; only GitHub + downloaded JSON survive.
