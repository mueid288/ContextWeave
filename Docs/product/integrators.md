# Integrator guide — Canonical Order C1 (v0.2)

10-minute path for inference / RAG platform engineers. Claims:
[`CLAIMS.md`](CLAIMS.md). Deep dive: [`canonical-order.md`](canonical-order.md),
[`live-shim.md`](live-shim.md).

## Install

```bash
git clone https://github.com/mueid288/ContextWeave.git
cd ContextWeave
git checkout v0.2.0-c1-kit
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

CPU only. Do not install torch/vLLM into a laptop venv — see
`Docs/runbooks/local-safety.md`.

## Library (in-process)

```python
from contextweave.product import FrequencyPrior, reorder_documents

prior = FrequencyPrior(cold_start_n=32)  # falls back to by_doc_id while cold

docs = [
    {"document_id": "doc_a", "content": "..."},
    {"document_id": "doc_b", "content": "..."},
]

ordered = reorder_documents(docs, "by_frequency_desc", prior=prior, observe=True)
# assemble prompt from ordered; send to your engine with prefix caching ON
```

Recommended policy: `by_frequency_desc` (hottest docs toward the shared prefix).

## Sidecar (OpenAI-compatible)

Point `cw-serve-order` at vLLM (or any OpenAI-compatible upstream) with prefix
caching enabled on the engine:

```bash
# GPU host example
CW_UPSTREAM_URL=http://127.0.0.1:8000 \
CW_CHUNK_ORDER=by_frequency_desc \
cw-serve-order --host 0.0.0.0 --port 8080
```

Clients send retrieved docs on the chat body:

```json
{
  "model": "mistral",
  "messages": [{"role": "user", "content": "What is the SLA?"}],
  "cw_documents": [
    {"document_id": "sla", "content": "..."},
    {"document_id": "pricing", "content": "..."}
  ],
  "cw_chunk_order": "by_frequency_desc"
}
```

- `POST /v1/cw/reorder` — rewrite only  
- `POST /v1/chat/completions` — reorder + forward  
- `GET /health` — prior stats  

One-shot dry run (no server): see [`live-shim.md`](live-shim.md).

## Measure (CPU)

Replay a JSONL trace of requests with document ids / token structure:

```bash
cw-analyze-trace --trace path/to/trace.jsonl \
  --compare-chunk-order \
  --report /tmp/compare_chunk_order.md \
  --metrics-json /tmp/compare_chunk_order.json
```

Primary KPIs: `share_prefix_cached` lift and `post_prefix_prefill_tokens`
reduction for `by_frequency_desc` vs `natural`. Do **not** use Gate G0 PASS/FAIL
as the product score (C1 can absorb recurrence into the prefix).

## When it helps / when it will not

| Helps | Will not help |
|---|---|
| Multi-query RAG, shared documents across requests | Single-shot unique contexts |
| Engine **prefix caching** enabled | Prefix cache off |
| Stable doc ids across requests | Random ids every call |
| Enough traffic to leave cold start (`CW_COLD_START_N`, default 32) | Tiny N stuck in cold `by_doc_id` fallback |

## Dogfood on cw-field

Live A/B (natural vs frequency) against the homeserver app:
[`cw-field-kit-dogfood.md`](cw-field-kit-dogfood.md).

## Next after a positive desk lift

Reproduce warm TTFT on your stack (harness pattern:
`scripts/product/eval_order_ttft.py`, Colab notes in
`Docs/product/colab-order-ttft.md`). Bank your own numbers before production
defaults.
