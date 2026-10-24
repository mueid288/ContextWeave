# Product: Canonical chunk order (C1 amplification)

**Status:** desk utility (CPU). Research PIC / C3 remains archived.  
**Quality:** unverified — reordering can change answers via position bias.

## What it does

Before prompt assembly, reorder retrieved chunks so shared documents form a
**shared prefix**, raising native radix/prefix-cache hits (**C1**) without
non-prefix PIC.

```python
from contextweave.trace_analysis import (
    build_doc_frequency,
    reorder_chunks,
    compare_chunk_orders,
)

freq = build_doc_frequency(rows)  # or a rolling prior
row = reorder_chunks(row, "by_frequency_desc", freq=freq)
```

CLI:

```bash
cw-analyze-trace --trace benchmarks/workloads/synthetic_rag_default/trace.jsonl \
  --compare-chunk-order \
  --report artifacts/product-canonical-order/compare_synthetic.md \
  --metrics-json artifacts/product-canonical-order/compare_synthetic.json
```

## Modes

| Mode | Use |
|---|---|
| `natural` | As retrieved / shuffled |
| `by_doc_id` | Natural-sort by id (stable; **inflated** on Zipf-aligned synthetic corpora) |
| `by_sha256_doc_id` | De-correlated ids (UUID-like) |
| `by_frequency_desc` | **Recommended product policy** — hottest docs toward the prefix |

## Tension with RAG relevance order

Bundled `benchmarks/corpora/sample_docs/rag_best_practices.md` recommends placing
documents in **relevance order**. Canonical order trades that for cross-query
prefix reuse. Integrators must choose; this tool does not claim quality parity.

## KPI

Primary: `share_prefix_cached` lift and `post_prefix_prefill_tokens` reduction
(overall + multi-doc). Do **not** treat Gate G0 PASS/FAIL as the product score —
absorbing recurrence into C1 can lower `share_recurring_non_prefix`.

Pre-reg: `Docs/pre-reg/pre-reg-product-canonical-order.md`.
