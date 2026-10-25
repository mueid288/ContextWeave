# Closeout — Product v0 (canonical-order C1 amplification)

**Date:** 2026-10-24  
**Tag context:** after research archive `v0.1.0-phase01-archive` + product desk

## What shipped

| Piece | Evidence |
|---|---|
| Chunk reorder library (`by_frequency_desc`, sha256, doc_id) | `src/contextweave/trace_analysis/chunk_order.py` |
| G0 sim prefix-hit lift | `artifacts/product-canonical-order-2026-10-24/` (PASS) |
| Rolling `FrequencyPrior` + chat rewrite | `src/contextweave/product/` |
| OpenAI shim `cw-serve-order` | dry-run + mock-upstream forward tests |
| Needle quality | `artifacts/product-order-quality-2026-10-24/` (freq 1.0) |
| **Live C1 TTFT** | `artifacts/product-order-ttft-2026-10-24/` (**1.79×** vs shuffled, prefix caching on) |

## Intended effect (verified)

Stabilize retrieved-document order → native prefix cache hits → lower warm latency,
without non-prefix PIC. Measured on Colab A100 / Mistral-7B / vLLM +
`--enable-prefix-caching`.

## How to run

See `Docs/product/live-shim.md` and `Docs/product/canonical-order.md`.

```bash
CW_UPSTREAM_URL=http://127.0.0.1:8000 cw-serve-order --port 8080
# clients send cw_documents + optional cw_chunk_order
```

## Scoped claims / non-claims

**Can claim:** on this stack/suite, frequency-stable order yields ~1.8× warm p50
vs per-request shuffle with prefix caching; needle answers preserved in the quality suite.

**Cannot claim:** production multi-tenant product; arbitrary RAG relevance parity;
partner-trace G0; PIC/C3 wins.

## Field follow-up (2026-10-25) — closed

Real traffic via cw-field + provisional field G0 PASS
(`artifacts/cw-field-g0-2026-10-25-field`). Layer 1 order A/B on that trace:
`by_frequency_desc` vs `natural` → **+5.64 pp** `share_prefix_cached`, **8.2%**
post-prefix cut (`artifacts/product-field-order-ab-2026-10-25/`). Clears desk ≥2 pp
bar; does **not** clear pre-reg ≥10 pp bar. **Layer 2 TTFT skipped.**

**Decision:** keep frequency order as cw-field default (already shipped). No live
field TTFT claim. No further product lane required for this question.

**Can claim (add):** on banked field retrieves (N=27), frequency order lifts
simulated prefix-cache share ~5.6 pp vs natural.

**Still cannot claim:** field warm TTFT win; final (non-provisional) partner G0.

## Default next

**Stop.** Frequency default on cw-field; CW product v0 evidence set is closed for
order-on-field until someone explicitly opens Layer 2 GPU.
