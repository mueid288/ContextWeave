# Product readiness — C1 kit + field dogfood

**Audience:** maintainers deciding what is “done” vs outbound vs missing.  
**Ship baseline:** [../status/ship-v0.2-c1-kit.md](../status/ship-v0.2-c1-kit.md) · Claims: [CLAIMS.md](CLAIMS.md)

## Scorecard

| Area | Status | Notes |
|------|--------|--------|
| C1 library (`FrequencyPrior`, `reorder_documents`) | **Ready** | Shipped on `main` / tag `v0.2.0-c1-kit` |
| Live shim `cw-serve-order` | **Ready** | Dry-run needs `CW_ALLOW_DRY_RUN=1` |
| Measure `cw-analyze-trace --compare-chunk-order` | **Ready** | Use **imported** traces, not raw partner_v1 |
| Lab TTFT claim (~1.79× warm p50) | **Ready (scoped)** | `artifacts/product-order-ttft-2026-10-24/` |
| Lab quality claim (needle) | **Ready (scoped)** | `artifacts/product-order-quality-2026-10-24/` |
| Field sim A/B (~5.6 pp prefix share) | **Ready (desk bar)** | Pre-reg ≥10 pp not met; soft-keep frequency |
| Field G0 dogfood pipeline | **Ready** | Provisional synthetic tokens |
| Kit dogfood Layer 1 (sim on frequency arm) | **Ready (scoped)** | `product-kit-dogfood-2026-10-26/` (+17 pp counterfactual; N=15; G0 FAIL) |
| Field G0 final / real tokenizer IDs | **Missing** | Explicit non-claim |
| Field Layer 2 live TTFT | **Missing** | Explicit non-goal this tag |
| PyPI publish | **Missing** | Explicit non-goal |
| Own-RAG warm ≥1.15× | **Not met** | FAIL banked (`artifacts/own-rag-demo-2026-10-24/`); harness removed |
| Multi-tenant SaaS | **Out of scope** | — |
| Control plane (planner) | **R0 done / R1 open** | Thesis approved; oracle CPU ready; GPU collect pending |

## Verdict

The **C1 evaluation kit is ready for lab outbound**: clone → CLAIMS → integrators →
measure on *their* prefix-caching stack.

**Product north star (approved):** fail-closed reuse control plane —
[control-plane-north-star.md](control-plane-north-star.md). Next falsification:
Gate **R1** ([../plans/2026-10-26-r1-oracle-harness.md](../plans/2026-10-26-r1-oracle-harness.md)).

It is **not** a production SaaS, **not** “final G0”, and **not** proven on live
field TTFT. C1 outbound and R1 can proceed in parallel.

## Integrator checklist

1. Engine has **native prefix caching** enabled.  
2. Multiple requests share documents.  
3. Wire `cw_documents` + `cw-serve-order` (or call `reorder_documents`).  
4. A/B with `cw-analyze-trace --compare-chunk-order` on a real replay.  
5. Do not claim wins without that measurement.

## Prioritized gaps

See [../status/gaps.md](../status/gaps.md) for definitions and gated tracks (M1 final
G0, M2 Layer 2 TTFT, M3 PyPI). Soft honesty gaps (own-RAG FAIL, desk-only field
A/B) stay documented there too.

## Owner checklist (this repo)

- [x] Product surface minimized on `main`  
- [x] Research on archive tag/branch  
- [x] CLAIMS + ship note current  
- [x] Gap memo (`Docs/status/gaps.md`)  
- [x] Live kit dogfood Layer 1 banked  
- [ ] Optional: PyPI / Layer 2 / final G0 when requested (M1/M2/M3 — see gaps.md)  
