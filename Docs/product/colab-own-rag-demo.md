# Colab: Own-corpus RAG demo (C1 via cw-serve-order)

Session: **`cw-own-rag-demo`** · A100 · ≤90 min  
Pre-reg: `Docs/pre-reg/pre-reg-own-rag-demo.md`  
Harness: `cw-rag-demo bench`

End-to-end: index sample/own docs → lexical top‑k → **`cw-serve-order`** →
vLLM with **`--enable-prefix-caching`** → A/B warm latency
(frequency vs shuffled chunk order).

Honest label: demo corpus ≠ partner production traffic.

## Laptop (CPU only)

```bash
cd "/Users/apple/Code/Context Weave"
source .venv/bin/activate
cw-rag-demo index
cw-rag-demo retrieve "What monthly uptime does Acme target?"
cw-rag-demo bench --dry-build
# ask against local dry-run shim (no GPU):
cw-serve-order --port 8080 --cold-start-n 0 &
cw-rag-demo ask "What monthly uptime does Acme target for the Inference API?"
```

Corpus default: Own-corpus if it has `.md`/`.txt` content docs; else
`benchmarks/corpora/sample_docs`. Override with `--corpus /path` or
`CW_RAG_CORPUS`.

## Colab — create session

```bash
colab new -s cw-own-rag-demo --gpu A100
```

## Colab — install (prefer git, not tarball)

```bash
cd /content
rm -rf ContextWeave
git clone --depth 1 https://github.com/mueid288/ContextWeave.git
cd ContextWeave && git pull origin main && git log -1 --oneline

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11
uv venv /content/cw-venv --python 3.11
source /content/cw-venv/bin/activate
# Install into the venv explicitly (avoid system Python)
uv pip install --python /content/cw-venv/bin/python "vllm>=0.6.0" huggingface_hub pyyaml
uv pip install --python /content/cw-venv/bin/python -e /content/ContextWeave
which python; python -V
python -c "import vllm, contextweave; print('vllm', vllm.__version__, 'cw', contextweave.__version__)"
```

## Start vLLM **with prefix caching**

```bash
source /content/cw-venv/bin/activate
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

OOM → `--max-model-len 4096`, smaller `-k`, or shorter `--chunk-chars`.

## Start cw-serve-order (shim)

```bash
source /content/cw-venv/bin/activate
pkill -f 'cw-serve-order|serve_order' || true
sleep 1

# Prefer CLI flags (env alone can race with import-time config)
nohup cw-serve-order \
  --host 127.0.0.1 --port 8080 \
  --upstream http://127.0.0.1:8000 \
  --cold-start-n 0 \
  > /tmp/cw-serve-order.log 2>&1 &
sleep 2
cat /tmp/cw-serve-order.log
curl -sf http://127.0.0.1:8080/health || (echo FAIL; tail -n 40 /tmp/cw-serve-order.log; exit 1)
```

## Index + bench

```bash
cd /content/ContextWeave
source /content/cw-venv/bin/activate
mkdir -p artifacts/own-rag-demo-2026-10-24

cw-rag-demo index --corpus benchmarks/corpora/sample_docs
cw-rag-demo bench \
  --base-url http://127.0.0.1:8080 \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --warm-trials 8 \
  --out artifacts/own-rag-demo-2026-10-24/report.json --json \
  | tee artifacts/own-rag-demo-2026-10-24/console.txt
```

Pass: `speedup_shuffled_over_frequency >= 1.15` (or bank FAIL with numbers).  
Functional: ≥5 gold substring hits on the question suite.

Optional smoke:

```bash
cw-rag-demo ask "What monthly uptime does Acme target for the Inference API?"
```

## Bank + stop

1. Download / paste `artifacts/own-rag-demo-2026-10-24/` into the laptop repo  
2. Update `Docs/pre-reg/pre-reg-own-rag-demo.md` → PASS or FAIL with p50 numbers  
3. One line in `Docs/status/experiment-log.md`  
4. `colab stop -s cw-own-rag-demo`

**Then stop.** Do not reopen PIC/EPIC/H3.
