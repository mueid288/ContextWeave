# Live kit dogfood — 2026-10-26 (Layer 1)

**Procedure:** [Docs/product/cw-field-kit-dogfood.md](../../Docs/product/cw-field-kit-dogfood.md)  
**Stack:** local Docker cw-field @ ContextWeave `4686c3ba…` / kit `v0.2.0-c1-kit`  
**Arms:** `ORDER_MODE=natural` then `frequency` with `COLD_START_N=0`; N=15 asks each on bob’s corpus  
**Imported arms:** `artifacts/cw-field-g0-kit-natural/`, `artifacts/cw-field-g0-kit-frequency/`

## Primary KPI (counterfactual on frequency-arm imported trace)

**Not** a live cross-arm comparison of served natural vs served frequency.
Measurement: `cw-analyze-trace --compare-chunk-order` on
`cw-field-g0-kit-frequency/trace.jsonl` only (same method as field Layer 1 sim).

| Mode | share_prefix_cached | Δpp vs natural | post_prefix ↓% |
|---|---:|---:|---:|
| natural (sim) | 44.6% | — | — |
| by_frequency_desc (sim) | 61.9% | **+17.28** | **+31.2%** |

- **Desk bar (≥ +2 pp):** PASS  
- **Analyzer pre-reg (≥ +10 pp or ≥20% multi-doc cut):** PASS (`pass_heuristic_frequency=true`)

Live stamps on that arm: all 15 rows `order_mode=frequency`,
`order_mode_effective=by_frequency_desc`. Natural-arm bank exists for procedure
sanity (+1.92 pp on that arm’s compare only).

## Notes

- Gate G0 on these short arms is **FAIL** (median chunk 256 &lt; 512); dogfood
  measures **order-policy plumbing**, not final G0. Tokens remain provisional (chars/4).
- Do **not** claim live head-to-head prefix-share or TTFT from this bank.
- Not Layer 2 TTFT (DeepSeek has no prefix cache).
