# Product live C1 TTFT proof — 2026-10-24 (Colab A100)

Session: `cw-order-ttft`  
Stack: vLLM OpenAI + `--enable-prefix-caching`, Mistral-7B-Instruct-v0.2  
Harness: `scripts/product/eval_order_ttft.py` (`filler_chars=2500`, warm_trials=8)

| Mode | warm p50 | contains |
|---|---:|---:|
| shuffled | **95.6 ms** | 1.0 |
| frequency | **53.6 ms** | 1.0 |

**Speedup** shuffled/frequency = **1.79×** · **`pass_heuristic: true`** (≥1.15)

This is the live evidence that stable frequency order amplifies native prefix-cache hits.
