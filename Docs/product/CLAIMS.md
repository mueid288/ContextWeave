# ContextWeave C1 — claims sheet (v0.2)

**Job to be done:** On multi-query RAG with shared documents and an engine that
has **native prefix caching**, stabilize retrieved-chunk order so more prefill
hits the prefix cache — fewer repeated tokens, lower warm TTFT.

**Product:** Canonical Order C1 kit (`reorder_documents` / `cw-serve-order`).  
**Tag:** `v0.2.0-c1-kit` · **Not** a multi-tenant SaaS · **Not** cw-field.

---

## Can claim

| Claim | Evidence |
|---|---|
| Frequency-stable order yields ~**1.79×** warm p50 TTFT vs per-request shuffle when prefix caching is on (scoped stack/suite) | `artifacts/product-order-ttft-2026-10-24/` |
| Needle-style answer quality preserved under frequency order on the quality suite | `artifacts/product-order-quality-2026-10-24/` (freq contains 1.0) |
| On banked live field retrieves (N=27), frequency lifts simulated `share_prefix_cached` by **~5.6 pp** vs natural and cuts post-prefix tokens ~8% | `artifacts/product-field-order-ab-2026-10-25/` |
| Live multi-user field traffic shows provisional Gate G0 PASS (reuse exists) | `artifacts/cw-field-g0-2026-10-25-field/` |
| Desk G0-sim prefix-hit lift for canonical order | `artifacts/product-canonical-order-2026-10-24/` |

## Cannot claim

- Universal token reduction on all prompts / all workloads  
- Field **live** warm TTFT win (Layer 2 not run)  
- Final (non-provisional) partner-trace G0 / real tokenizer IDs  
- Parity with relevance-first RAG ranking for arbitrary corpora  
- Benefit without engine **prefix caching** enabled  
- Production multi-tenant product or “drops into any foundation model weights”  
- PIC / non-prefix KV reuse (research archived)

---

## Integrator expectation

Measure on **your** RAG replay with prefix caching on. Expect lift when many
requests share documents; expect little or none on single-shot or fully unique
contexts. Start at [`integrators.md`](integrators.md).
