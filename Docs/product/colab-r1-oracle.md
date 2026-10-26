# Colab: Gate R1 oracle collect (control plane falsification)

Session: **`cw-r1-oracle`** · GPU: **A100** · wall budget: **120 min**  
Harness: [../plans/2026-10-26-r1-oracle-harness.md](../plans/2026-10-26-r1-oracle-harness.md)  
**C3 pin first:** [../plans/2026-10-26-r1-c3-pin.md](../plans/2026-10-26-r1-c3-pin.md) — do **not** use vLLM 0.32 + LMCache 0.5.6.  
Laptop policy: [../runbooks/local-safety.md](../runbooks/local-safety.md)

**C0/C1** need vLLM with **prefix caching**. **C3** needs a second LMCache
CacheBlend server (`--c3-base-url`). Without C3, `r1_pass` cannot succeed
(`feasible=false` on C3 + no gate-need from blend failures).

## Laptop — start session

```bash
colab new -s cw-r1-oracle --gpu A100
```

Push or ensure `main` includes `scripts/r1/collect_oracle_http.py` before clone.

## Colab — install

```bash
cd /content
git clone --depth 1 https://github.com/mueid288/ContextWeave.git || true
cd ContextWeave && git fetch origin && git checkout main && git pull origin main

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11
uv venv /content/cw-venv --python 3.11
source /content/cw-venv/bin/activate
uv pip install --python /content/cw-venv/bin/python "vllm>=0.6.0" huggingface_hub
# LMCache for C3 (pin may need bump — record pip freeze in artifacts)
uv pip install --python /content/cw-venv/bin/python lmcache || echo "LMCache install failed — C1-only smoke"
uv pip install --python /content/cw-venv/bin/python -e /content/ContextWeave
python -c "import vllm; print('vllm', vllm.__version__)"
```

## Start prefix-caching server (C0/C1)

```bash
source /content/cw-venv/bin/activate
pkill -f 'vllm.entrypoints|vllm serve' || true

nohup python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 8192 \
  --enable-prefix-caching \
  > /tmp/vllm-prefix.log 2>&1 &

for i in $(seq 1 90); do curl -sf http://127.0.0.1:8000/v1/models && echo OK && break; sleep 10; done
```

OOM → `--max-model-len 4096` and/or `--filler-chars 1200` on collect.

## Optional C3 — LMCache CacheBlend server (port 8001)

Follow current LMCache + vLLM CacheBlend docs for your pin. Goal: OpenAI-compatible
endpoint on `http://127.0.0.1:8001` that reuses non-prefix chunk KV with selective
recompute (~15%). If you cannot bring this up in-session, run C0/C1 smoke only and
bank trials with C3 `feasible=false` — **do not** claim Gate R1 pass.

## Collect

```bash
cd /content/ContextWeave
mkdir -p artifacts/r1-oracle-$(date -u +%Y-%m-%d)
OUT=artifacts/r1-oracle-$(date -u +%Y-%m-%d)

# Full R1 when C3 is up:
python scripts/r1/collect_oracle_http.py \
  --base-url http://127.0.0.1:8000 \
  --c3-base-url http://127.0.0.1:8001 \
  --model Qwen/Qwen2.5-7B-Instruct \
  --n-requests 40 --runs 3 --cold-start-n 0 \
  --out $OUT/oracle_trials.jsonl \
  --report $OUT/oracle_report.json --json \
  | tee $OUT/console.txt

# C0/C1 smoke only (no R1 pass expected):
# omit --c3-base-url
```

CPU re-check on laptop after download:

```bash
cw-r1-oracle --input artifacts/r1-oracle-YYYY-MM-DD/oracle_trials.jsonl \
  --report /tmp/r1_upside.json --json
```

Bank `pip freeze`, trials, report **before** `colab stop -s cw-r1-oracle`.

## Pass / fail

See Gate R1 table in the harness plan. Exit code `4` from the collector means
`r1_pass=false` (expected until C3 quality/latency frontier is real).
