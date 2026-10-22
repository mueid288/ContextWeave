# G1 step 4 — EPIC (LegoLink)

EPIC ([DerekHJH/epic](https://github.com/DerekHJH/epic)) is a **vLLM ~0.7 fork**
(torch **2.5.1** build), not an LMCache plugin. It cannot share the Colab pin
that already passed smoke / TTFT / quality (vLLM **0.32.0**).

## On the current Colab pin (vLLM 0.32) — probe only

```bash
cd /content/ContextWeave && git pull
python scripts/g1_epic_probe.py --json | tee g1_epic_probe.json
```

Expected: `epic_fork_detected: false`, exit code **3** → bank as **documented pin BLOCK**.
Do **not** `pip install -e` EPIC on top of the working 0.32 stack.

Then stop the idle session: `colab stop -s cw-smoke`.

## Dedicated EPIC session (optional, 1-session time-box)

Fresh A100 Colab (or other GPU). Expect a long CUDA extension build.

**Python gate (do this first):** EPIC pins `torch==2.5.1`, which has **no Py3.13 wheels**.
**Colab default is 3.13 (2026-10-22) → documented BLOCK** — do not burn install time there.
Need a host with **Python 3.10–3.12** (e.g. RunPod template / custom image), then the steps below.

```bash
# local: start a NEW session (do not reuse cw-g1-r2)
colab new -s cw-epic   # add your usual GPU/accelerator flags if any

cd /content && git clone https://github.com/mueid288/ContextWeave.git
cd ContextWeave
python -V   # must be 3.10–3.12; abort on 3.13

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1
export SMOKE_MODEL=Qwen/Qwen3-8B   # or Mistral-7B-Instruct-v0.2 (paper default)

chmod +x scripts/g1_epic_install.sh
bash scripts/g1_epic_install.sh

# Only if probe says epic_fork_detected:
python scripts/g1_epic_bench.py --json | tee g1_epic.json
```

**Success:** `pass_heuristic: true` (LegoLink-8 ≥15% faster than full prefill **and** both answers contain gold `Karachi`).  
**Fail / abort:** Python 3.13 / torch pin, install dies, fork markers missing, OOM, or quality fail → log and stop; do not expand matrix.

## Why this split

| Stack | Role |
|---|---|
| Colab vLLM 0.32 + lmcache 0.5.6 | Smoke, prefix TTFT, quality, reorder gap, CacheBlend MP (provisional) |
| DerekHJH/epic fork | Only path to real `cache_fuse_metadata` / `hack_kv` LegoLink |
