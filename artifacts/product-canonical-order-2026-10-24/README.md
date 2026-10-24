# Product: canonical chunk-order A/B (2026-10-24)

Pre-reg: `Docs/pre-reg/pre-reg-product-canonical-order.md`  
Product doc: `Docs/product/canonical-order.md`

| Workload | `by_frequency_desc` multi-doc Δpp | multi-doc post_prefix ↓ | pass |
|---|---:|---:|---|
| synthetic_rag_default | +14.4 | 21.0% | **true** |
| my_corpus | +15.5 | 22.4% | **true** |

`by_doc_id` ≈ frequency on these corpora (Zipf↔alpha coincidence).  
`by_sha256_doc_id` lift is smaller (+5–6 pp multi-doc) — closer to uncorrelated IDs.

Quality vs relevance/original order: **unverified**.
