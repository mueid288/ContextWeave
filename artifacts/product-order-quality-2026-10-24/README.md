# Product order-quality Part B — 2026-10-24 (Colab A100)

Session: `cw-order-quality`  
Stack: vLLM **0.32.0**, `mistralai/Mistral-7B-Instruct-v0.2`, max_model_len 4096  
Harness: `scripts/product/eval_order_quality.py`

| Mode | contains_rate |
|---|---:|
| relevance | ~0.67 (ratio implies; see report.json) |
| natural | **1.0** |
| frequency | **1.0** |

`frequency_vs_relevance_ratio` ≈ **1.5** · **`pass_heuristic: true`**

Bar: frequency ≥ 0.80 and ≥ 0.90 × relevance.

Replace/augment `report.json` with the Colab copy if you download the full file.
