# R1 oracle bank — 2026-10-26 (C0/C1 smoke)

**Gate R1:** **FAIL / not opened** (`r1_pass=false`).  
**Harness:** [Docs/plans/2026-10-26-r1-oracle-harness.md](../../Docs/plans/2026-10-26-r1-oracle-harness.md)

## What ran

| Arm | Stack | Result |
|---|---|---|
| **C0** | vLLM prefix server, salted prompts | feasible 40/40; mean_q **0.80**; med TTFT ~126 ms |
| **C1** | same + frequency order | feasible 40/40; mean_q **0.90**; med TTFT ~126 ms; **best fixed** |
| **C3** | LMCache CacheBlend (`enable_blending`) on `:8001` | **0 feasible** — serve starts, first generate fatals |

## Oracle summary (C0/C1 only; C3 infeasible)

From `oracle_report.json` / local `cw-r1-oracle` re-check:

| Field | Value |
|---|---|
| best_fixed | C1 |
| quality_upside_points | ~2.5 (`r1_quality_pass`) |
| ttft_reduction_fraction | ~0.003 (`r1_ttft_pass` false) |
| gate_need_slices | [] |
| r1_pass | **false** |

## C3 blocker (do not retry same pin blindly)

- Colab A100 · `vllm` ~0.32 · `lmcache` 0.5.6 · Qwen2.5-7B-Instruct  
- Startup needed `VLLMModelTracker.register_model` monkeypatch (known LMCache gap).  
- First `/v1/chat/completions` then crashed in layerwise store:

```text
lmcache ... batched_from_gpu → single_layer_kv_transfer
IndexError: Dimension out of range (expected to be in range of [-4, 3], but got 4)
```

**Not** a ContextWeave collector bug. Next C3 attempt needs a **documented compatible pin** (or offline blend example), not another unpinned Colab serve.

## Files

| File | Role |
|---|---|
| `oracle_trials.jsonl` | C0/C1 timed rows; C3 rows were `feasible=false` in the first collect |
| `oracle_report.json` | Oracle upside on that JSONL |
| `console.txt` | Collect stdout |
| `pip_freeze.txt` | Environment freeze from the C0/C1 session |

## Claims

- **May say:** C0/C1 smoke banked; C1 best fixed on this suite; Gate R1 not passed.  
- **Must not say:** CacheBlend C3 measured; control-plane proven; R1 pass.
