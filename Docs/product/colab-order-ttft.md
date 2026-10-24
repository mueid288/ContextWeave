# Colab: Live C1 TTFT proof (canonical vs shuffled)

Session: **`cw-order-ttft`** · A100 · 90 min  
Pre-reg: `Docs/pre-reg/pre-reg-product-live-ttft.md`

This is the **real product proof**: same docs, shuffled order vs frequency-stable
order, with vLLM **prefix caching** on. Quality Part B alone is not enough.

## Laptop

```bash
colab new -s cw-order-ttft --gpu A100
```

## Colab — install (reuse pattern from order-quality)

```bash
cd /content
git clone --depth 1 https://github.com/mueid288/ContextWeave.git || true
cd ContextWeave && git pull origin main

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11
uv venv /content/cw-venv --python 3.11
source /content/cw-venv/bin/activate
uv pip install --python /content/cw-venv/bin/python "vllm>=0.6.0" huggingface_hub
uv pip install --python /content/cw-venv/bin/python -e /content/ContextWeave
python -c "import vllm; print(vllm.__version__)"
```

## Start server **with prefix caching**

```bash
source /content/cw-venv/bin/activate
# kill any old server
pkill -f 'vllm.entrypoints|vllm serve' || true

nohup python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 8192 \
  --enable-prefix-caching \
  > /tmp/vllm-openai.log 2>&1 &

for i in $(seq 1 90); do curl -sf http://127.0.0.1:8000/v1/models && echo OK && break; sleep 10; done
tail -n 20 /tmp/vllm-openai.log
```

OOM → `--max-model-len 4096` and/or `--filler-chars 1200` on the eval.

## Run TTFT A/B

```bash
cd /content/ContextWeave
mkdir -p artifacts/product-order-ttft-2026-10-24
python scripts/product/eval_order_ttft.py \
  --base-url http://127.0.0.1:8000 \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --filler-chars 2500 \
  --warm-trials 8 \
  --out artifacts/product-order-ttft-2026-10-24/report.json --json \
  | tee artifacts/product-order-ttft-2026-10-24/console.txt
```

Pass: `speedup_shuffled_over_frequency >= 1.15` and frequency contains ≥ 0.8.

Then download artifacts / paste report; `colab stop -s cw-order-ttft`.
