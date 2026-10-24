# Pre-registration: Live C1 TTFT proof (canonical order → prefix cache)

**Status:** `READY` (GPU, 90 min)  
**Depends on:** Part A shim PASS · Part B quality PASS  
**Not a PIC reopen.**

## One question

On Colab A100 with **vLLM OpenAI + `--enable-prefix-caching`**, does a stream of
requests that always use **`by_frequency_desc`** document order show **≥15% lower
warm p50 wall latency** than a stream that uses **per-request shuffled** order
on the **same** doc set and question (n≥8 warm trials each after 1 warmup)?

That is the intended product effect: shared order → shared prefix → real C1 reuse.

## Pass / fail

| Outcome | Next |
|---|---|
| PASS (≥15% warm p50) | Product claim allowed: live C1 amplification measured |
| FAIL (&lt;15% but engages) | Keep shim; claim only sim+quality, not live latency |
| No prefix caching / flat latency | Fix vLLM flags once; else FAIL as unreproducible on this stack |

## Fixed

| Item | Value |
|---|---|
| Session | `cw-order-ttft` |
| Cap | **90 min** |
| Model | `mistralai/Mistral-7B-Instruct-v0.2` |
| Server | `--enable-prefix-caching --max-model-len 8192` (drop to 4096 on OOM) |
| Harness | `scripts/product/eval_order_ttft.py` |
| Warm trials | ≥8 per mode after 1 discard |
| Pass | `speedup = natural_warm_p50 / freq_warm_p50 ≥ 1.15` |

## Procedure

See `Docs/product/colab-order-ttft.md`.
