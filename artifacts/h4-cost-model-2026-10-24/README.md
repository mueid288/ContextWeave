# H4 cost model — 2026-10-24

**Pre-reg:** `Docs/pre-reg/pre-reg-h4-cost-model.md`  
**Verdict:** **FAIL** (primary)

Default 450 TFLOP/s Mistral-7B `prefill_time_s(12k)` ≈ **457 ms**; measured C0 ≈
**1130–1165 ms** → relative error **~60%** on all four banked suites.

| Suite | Meas mean C0 | Pred | Rel err |
|---|---|---|---|
| Phase1 oracle | 1148 ms | 457 ms | 0.60 |
| H3 confirm 99 | 1129 ms | 457 ms | 0.60 |
| Keydev 99 | 1165 ms | 457 ms | 0.61 |
| Keydev 100 | 1163 ms | 457 ms | 0.61 |

**Secondary (not a pass bar):** calibrate TFLOP on confirm 99 → ~182 TFLOP/s;
seed 100 rel err **~2.9%**. A calibrated rate transfers across filler; the
**PRD default** does not.

**Implication:** do not use §7.5 450-TFLOP tables as measured TTFT.
