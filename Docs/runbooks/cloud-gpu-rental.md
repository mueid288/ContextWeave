# Cloud GPU rental — start here

**Laptop stays model-free** ([local-safety.md](local-safety.md)).  
Rent → work only on the cloud box → **stop the pod** when done.

**Agent setup (done on this Mac):** Runpod skills + MCP wired for Cursor per [agent-setup](https://docs.runpod.io/agent-setup.md). After you **Sign in with Runpod** in Cursor MCP settings, you can ask the agent to list/create Pods instead of only using the web console.

## Recommendation (first smoke, minimal spend)

| Choice | Pick |
|---|---|
| Provider | **[RunPod](https://www.runpod.io/)** Secure or Community Cloud |
| GPU for smoke | **1× RTX 4090 24GB** (enough for 8B + short context) |
| Approx rate | ~**$0.34–0.74 / hr** (Community cheaper, Secure more stable) |
| Smoke budget | **$2–5** wall-clock cap (≤2 hours including installs) |
| First model | **`Qwen/Qwen3-8B`** (usually ungated) — switch to Llama-3.1 after HF license |
| Do **not** start with | Month reservation, multi-GPU, H100 |

Upgrade to **A100 80GB** (~$1.2–1.6/hr) only after smoke works and you start the Tier-1 matrix.

### Quote snapshot (indicative, Oct 2026 — re-check at checkout)

| Provider | SKU | ~$/hr | Use for |
|---|---|---|---|
| RunPod Community | RTX 4090 24GB | ~0.34 | **Smoke (recommended)** |
| RunPod Secure | RTX 4090 24GB | ~0.69–0.74 | Smoke if Community flaky |
| RunPod Community | A100 80GB PCIe | ~1.19–1.39 | Full Phase 0B matrix |
| Lambda | A100 80GB | ~1.29 | Alternative A100 |
| Vast.ai | RTX 4090 | ~0.25–0.50 | Cheapest; more host churn |

Sources: RunPod pricing page / public 2026 comparisons. **Confirm live price before deploy.**

---

## Before you pay (10 minutes on the laptop)

1. Create accounts: [RunPod](https://www.runpod.io/), [Hugging Face](https://huggingface.co/).
2. On HF: accept **Qwen3-8B** terms (and Llama-3.1 if you want it later).
3. Create an HF **read** token (`Settings → Access Tokens`).
4. Optional: push this repo to GitHub/GitLab so the pod can `git clone`.
5. Decide a hard stop: e.g. **stop pod at $5** spent.

---

## Rent on RunPod (click path)

1. **Deploy → Pods → + Deploy**
2. GPU: **RTX 4090** (24 GB). Template: **RunPod PyTorch** (CUDA 12.x) or official PyTorch 2.x + CUDA 12.4 image.
3. Disk: **≥ 80 GB** container disk (model weights + venv).
4. Expose nothing public unless you need SSH/Jupyter; prefer **SSH** or web terminal.
5. Start pod → open terminal → **immediately** note `$/hr` and start a phone timer for 2 hours.

---

## On the pod (paste sequence)

```bash
# 0) Safety: only on the rented GPU host
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1

# 1) System check
nvidia-smi

# 2) Get the repo (pick one)
git clone <YOUR_REPO_URL> context-weave && cd context-weave
# OR upload a zip from your laptop

# 3) Python env (do NOT reuse the laptop .venv)
python3 -m venv .venv-gpu
source .venv-gpu/bin/activate
pip install -U pip

# 4) Install inference stack (pins: docs/runtime-pins.md)
# Confirm latest compatible pair on https://docs.lmcache.ai/getting_started/installation.html
pip install "vllm>=0.26.0" "lmcache==0.5.2" huggingface_hub

# 5) HF login (paste token — do not commit it)
huggingface-cli login

# 6) Smoke: Qwen3-8B short generate (proves GPU + weights)
python - <<'PY'
from vllm import LLM, SamplingParams
llm = LLM(model="Qwen/Qwen3-8B", max_model_len=4096, trust_remote_code=True)
out = llm.generate(["Say hello in one short sentence."], SamplingParams(max_tokens=32, temperature=0))
print(out[0].outputs[0].text)
PY
```

If that works, record driver/CUDA/vLLM versions in `Docs/status/experiment-log.md`, then try LMCache/CacheBlend per [gpu-runbook.md](gpu-runbook.md).

**When stuck or done: Stop / terminate the pod.** Idle pods still bill.

---

## Cost control

| Rule | Why |
|---|---|
| Cap smoke at **2 hours** | Install + one model load is enough |
| Prefer **4090** for smoke | ~3–5× cheaper than A100 |
| Use **Qwen3** first | Avoid Llama gate delay |
| Terminate, don’t just close tab | Billing continues if pod runs |
| No month reserve yet | G1 not proven |

Rough smoke cost: **~$1–3** if you finish in under 2 hours on a 4090.

---

## After smoke passes

1. Note exact pins in `docs/runtime-pins.md` (replace “candidate”).
2. Either stop and resume later, or resize/redeploy to **A100 80GB** for the Tier-1 matrix.
3. Keep `CONTEXTWEAVE_ALLOW_MODEL_LOAD` **unset** on your Mac.
