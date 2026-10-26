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
| Field G0 final / real tokenizer IDs | **Missing** | Explicit non-claim |
| Field Layer 2 live TTFT | **Missing** | Explicit non-goal this tag |
| PyPI publish | **Missing** | Explicit non-goal |
| Own-RAG warm ≥1.15× | **Not met** | FAIL banked (`artifacts/own-rag-demo-2026-10-24/`) |
| Multi-tenant SaaS / PIC planner | **Out of scope** | Research archived |

## Verdict

The **evaluation kit is ready for lab outbound**: clone → CLAIMS → integrators →
measure on *their* prefix-caching stack.

It is **not** a production SaaS, **not** “final G0”, and **not** proven on live
field TTFT. Default next: outbound; open Layer 2 or PyPI only on explicit ask.

## Integrator checklist

1. Engine has **native prefix caching** enabled.  
2. Multiple requests share documents.  
3. Wire `cw_documents` + `cw-serve-order` (or call `reorder_documents`).  
4. A/B with `cw-analyze-trace --compare-chunk-order` on a real replay.  
5. Do not claim wins without that measurement.

## Owner checklist (this repo)

- [x] Product surface minimized on `main`  
- [x] Research on archive tag/branch  
- [x] CLAIMS + ship note current  
- [ ] Optional: PyPI / Layer 2 when requested  
