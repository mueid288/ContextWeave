# Colab: Part B order-quality (90 min)

Session: **`cw-order-quality`** · GPU: **A100** · Model: **Mistral-7B-Instruct-v0.2**  
Pre-reg: `Docs/pre-reg/pre-reg-product-live-shim.md` Part B  
Harness: `scripts/product/eval_order_quality.py` (HTTP → vLLM OpenAI)

No EPIC / CacheBlend. Stock vLLM OpenAI server only.

## 0. Laptop — start session

```bash
colab new -s cw-order-quality --gpu A100
```

## 1. Colab — clone + venv (Python 3.11)

```bash
cd /content
git clone --depth 1 https://github.com/mueid288/ContextWeave.git
cd ContextWeave && git pull origin main

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11
uv venv /content/cw-venv --python 3.11
source /content/cw-venv/bin/activate
uv pip install -U pip
uv pip install "vllm>=0.6.0" huggingface_hub
uv pip install -e /content/ContextWeave
```

If the model is gated:

```bash
huggingface-cli login   # paste HF token once
```

## 2. Colab — start OpenAI server (background)

```bash
source /content/cw-venv/bin/activate
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
nohup python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 4096 \
  --dtype auto \
  > /tmp/vllm-openai.log 2>&1 &

# wait until healthy
for i in $(seq 1 60); do
  curl -sf http://127.0.0.1:8000/v1/models && break
  sleep 10
done
tail -n 30 /tmp/vllm-openai.log
```

OOM? Drop to `--max-model-len 2048` or `Qwen/Qwen2.5-7B-Instruct`.

## 3. Colab — run quality A/B

```bash
source /content/cw-venv/bin/activate
cd /content/ContextWeave
mkdir -p artifacts/product-order-quality-2026-10-24

python scripts/product/eval_order_quality.py \
  --base-url http://127.0.0.1:8000 \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --out artifacts/product-order-quality-2026-10-24/report.json \
  --json | tee artifacts/product-order-quality-2026-10-24/console.txt

python -m pip freeze > artifacts/product-order-quality-2026-10-24/pip_freeze.txt
```

## 4. Collect then stop

Download / copy out `artifacts/product-order-quality-2026-10-24/` **before** stop.

```bash
colab stop -s cw-order-quality
```

Paste `report.json` (or `pass_heuristic` + per-mode rates) back into chat.
