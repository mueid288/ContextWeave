# G1 step 4 — EPIC (LegoLink)

EPIC ([DerekHJH/epic](https://github.com/DerekHJH/epic)) is a **vLLM ~0.7 fork**
(torch **2.5.1** build), not an LMCache plugin. It cannot share a Colab pin that
already ran CacheBlend (different torch/vLLM).

## Dedicated EPIC session

Fresh A100 Colab (or other GPU). Expect a long CUDA extension build.

**Python:** EPIC / torch 2.5.1 need **3.10–3.12**. Colab’s system Python is often
**3.13** — that is fine. `scripts/g1_epic_install.sh` bootstraps an isolated
**CPython 3.11** via [`uv`](https://github.com/astral-sh/uv) at `/content/epic-venv`
and installs EPIC there (does not require changing Colab’s runtime).

```bash
# local — NEW session (do not reuse CacheBlend session)
colab new -s cw-epic --gpu A100

# on the VM
cd /content && git clone https://github.com/mueid288/ContextWeave.git
cd ContextWeave
git pull

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1
export SMOKE_MODEL=Qwen/Qwen3-8B   # or Mistral-7B-Instruct-v0.2 (paper default)

bash scripts/g1_epic_install.sh
# → probe JSON; epic_fork_detected must be true

source /content/epic-venv/bin/activate   # if install created the uv venv
python scripts/g1_epic_bench.py --json | tee g1_epic.json
```

**Success:** `pass_heuristic: true` (LegoLink-8 ≥15% faster than full prefill **and**
both answers contain gold `Karachi`).  
**Fail / abort:** uv/python bootstrap fails, CUDA build dies, fork markers missing,
OOM, or quality fail → log and stop; do not expand matrix.

## Legacy note (stock Colab pin probe)

On an old CacheBlend session you can still run `python scripts/g1_epic_probe.py`
expecting `epic_fork_detected: false`. Do **not** `pip install -e` EPIC into that
system 3.13 env.

## Why this split

| Stack | Role |
|---|---|
| Colab vLLM 0.18 + lmcache 0.4.2 (system Py3.13) | CacheBlend matched G1 (closed) |
| `/content/epic-venv` Py3.11 + DerekHJH/epic | LegoLink `cache_fuse_metadata` / `hack_kv` |
