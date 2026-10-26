# GPU runbook (ContextWeave)

**Hard rule:** never load models on the laptop —
[local-safety.md](local-safety.md).

## Current paid job: Gate R1

1. Prefer Colab A100: [../product/colab-r1-oracle.md](../product/colab-r1-oracle.md)
2. `export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1` **on the GPU host only**
3. vLLM + `--enable-prefix-caching` for C0/C1; LMCache CacheBlend for C3
4. Collect with `scripts/r1/collect_oracle_http.py`
5. Bank artifacts, then stop the session

## Older product proofs (still valid)

- C1 TTFT: [../product/colab-order-ttft.md](../product/colab-order-ttft.md)
- C1 quality: [../product/colab-order-quality.md](../product/colab-order-quality.md)

## Spend discipline

Cap first R1 session (~$ budget you set). If vLLM cannot serve 7B after one
install cycle, stop and fix offline — do not burn idle GPU hours.
