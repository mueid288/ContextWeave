# Own-corpus RAG demo — 2026-10-24 (Colab A100)

Session: `cw-own-rag-demo`  
Stack: vLLM OpenAI + `--enable-prefix-caching`, `mistralai/Mistral-7B-Instruct-v0.2`  
Shim: `cw-serve-order` on **:18080** (Colab `:8080` is system `node`)  
Corpus: `benchmarks/corpora/sample_docs` (53 chunks)  
Harness: `cw-rag-demo bench --warm-trials 8`

| Mode | warm p50 | gold_ok (warm) |
|---|---:|---:|
| shuffled | **265 ms** | 1.0 |
| frequency | **357 ms** | 1.0 |

`speedup_shuffled_over_frequency` = **0.74** · **`pass_heuristic: false`**  
`pass_functional: true` (8/10 gold substring hits)

Smoke ask (uptime): correct `99.9%` answer via shim.

**Interpretation:** Latency bar failed on this multi-question RAG suite
(different retrieved sets → weak shared prefix across trials). Product v0
fixed-prompt TTFT (`artifacts/product-order-ttft-2026-10-24/`, **1.79×**)
is unchanged. No PIC/EPIC reopen.
