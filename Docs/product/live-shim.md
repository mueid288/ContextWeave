# Live product path: canonical-order shim

**CPU shim** that reorders RAG documents before they hit a chat model, so native
prefix cache (C1) can hit more often. Optional forward to any OpenAI-compatible
upstream (vLLM on a GPU host).

Quality vs relevance order is **not** validated yet (see Part B of
`Docs/pre-reg/pre-reg-product-live-shim.md`).

## One-shot (no server)

```bash
cat > /tmp/req.json <<'EOF'
{
  "model": "mistral",
  "messages": [{"role": "user", "content": "What is the city?"}],
  "cw_documents": [
    {"document_id": "rare", "content": "..."},
    {"document_id": "hot", "content": "..."}
  ],
  "cw_chunk_order": "by_frequency_desc"
}
EOF
cw-serve-order --reorder-json /tmp/req.json --cold-start-n 0
```

## Server (dry-run or upstream)

```bash
# Dry-run on laptop (rewrites only; fake completion)
cw-serve-order --port 8080

# On GPU host, point at vLLM OpenAI server
CW_UPSTREAM_URL=http://127.0.0.1:8000 cw-serve-order --host 0.0.0.0 --port 8080
```

Endpoints:

| Path | Role |
|---|---|
| `GET /health` | prior stats |
| `POST /v1/cw/reorder` | rewrite only |
| `POST /v1/chat/completions` | rewrite + forward (or dry-run) |

Client fields: `cw_documents`, `cw_chunk_order`. Response / rewrite includes `cw_meta`.

## Cold start

Until `CW_COLD_START_N` observations (default 32), `by_frequency_desc` falls back
to `by_doc_id` natural sort.

## Part B — quality (GPU)

```bash
python scripts/product/eval_order_quality.py \
  --base-url http://127.0.0.1:8000 \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --out artifacts/product-order-quality/report.json --json
```

Pre-reg: `Docs/pre-reg/pre-reg-product-live-shim.md` Part B — **PASS**
(2026-10-24, frequency contains 1.0 on needle suite). Default
`CW_CHUNK_ORDER=by_frequency_desc` is OK for this bar; still not a claim about
arbitrary RAG relevance tradeoffs.

## Live C1 latency proof (required for “product works”)

Sim lift + needle quality are not enough. Measure warm TTFT with prefix caching:

- Pre-reg: `Docs/pre-reg/pre-reg-product-live-ttft.md`
- Colab: `Docs/product/colab-order-ttft.md`
- Harness: `scripts/product/eval_order_ttft.py`

Until that PASSes, do **not** claim live C1 amplification — only sim + quality.
