# G1 step 4 — EPIC (LegoLink)

EPIC ([DerekHJH/epic](https://github.com/DerekHJH/epic)) is a **vLLM ~0.7 fork**
with LegoLink hooks (`cache_fuse_metadata` / `hack_kv`). Demo focuses on
**functionality**; authors say full production system is still closed-source.

Do **not** install EPIC into a CacheBlend Colab session (different torch/vLLM).

**Next fair-scale attempt (if any):** use the parked pre-reg
[`Docs/pre-reg-epic-12k.md`](pre-reg-epic-12k.md) — not an ad-hoc toy rerun.

## Choose a path (speed)

| Path | Time on Colab A100 | When |
|---|---|---|
| **A. Fast (recommended)** | ~10–20 min | `vllm==0.7.0` **wheel** + overlay EPIC `*.py` (no nvcc) |
| **B. Full source build** | 1–3+ hours | Fast path probe fails; or you need EPIC’s exact `_C.so` |
| **C. High-CPU host** | ~20–40 min compile | RunPod/etc. with many vCPUs if A fails and B is too slow |
| **D. Skip EPIC** | 0 | Close G1 non-prefix; CacheBlend already D✓ E✗ fair |

Colab’s bottleneck is **CPU cores for nvcc**, not the GPU. Path A avoids that.

### Path A — fast install

```bash
colab new -s cw-epic --gpu A100

cd /content && git clone https://github.com/mueid288/ContextWeave.git
cd ContextWeave && git pull

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1
bash scripts/g1_epic_install_fast.sh

source /content/epic-venv/bin/activate
# Demo fork patches llama-family attention; paper uses Mistral — not Qwen3.
export SMOKE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
python scripts/g1_epic_bench.py --json | tee g1_epic.json
```

### Path B — full CUDA build (slow)

Same session flags, then `bash scripts/g1_epic_install.sh`  
(already pins `TORCH_CUDA_ARCH_LIST=8.0` + `MAX_JOBS=4` on A100).

### Path C — faster full build elsewhere

Use a machine with **16–32+ vCPUs**, same scripts, `MAX_JOBS=8`–`16`.  
Optionally build a wheel once and reuse it.

## Success / fail

**Success:** `pass_heuristic: true` (LegoLink-8 ≥15% faster than full prefill **and**
answers contain gold `Karachi`).

**Fail / abort:** fast overlay probe fails and you decline a long compile; OOM;
quality fail → log and stop; do not expand matrix.

## Notes

- System Colab Python may be **3.13**; installers bootstrap **uv + CPython 3.11**.
- Prefer **Mistral-7B-Instruct-v0.2** for the demo fork (llama attention hooks).
  `Qwen3-8B` is unlikely to hit `hack_kv` paths in this open demo.
