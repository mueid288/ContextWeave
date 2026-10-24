# Chunk-order compare — `benchmarks/workloads/synthetic_rag_default/trace.jsonl`

Requests: **500** (multi-doc ≥2 chunks: **220**)

## Overall `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens | recurring_non_prefix |
|---|---:|---:|---:|
| `natural` | 47.3% | 657,175 | 77.5% |
| `by_doc_id` | 55.6% | 554,252 | 73.4% |
| `by_sha256_doc_id` | 49.3% | 632,185 | 76.7% |
| `by_frequency_desc` | 55.6% | 554,332 | 73.4% |

## Multi-doc (`len(chunks)≥2`) `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens |
|---|---:|---:|
| `natural` | 31.4% | 578,197 |
| `by_doc_id` | 45.8% | 456,517 |
| `by_sha256_doc_id` | 36.7% | 533,237 |
| `by_frequency_desc` | 45.8% | 456,629 |

## Deltas vs `natural` (product KPIs)

| Mode | overall Δpp | overall post_prefix ↓% | multi-doc Δpp | multi-doc post_prefix ↓% |
|---|---:|---:|---:|---:|
| `by_doc_id` | +8.25 | +15.7% | +14.45 | +21.0% |
| `by_sha256_doc_id` | +2.00 | +3.8% | +5.34 | +7.8% |
| `by_frequency_desc` | +8.24 | +15.6% | +14.43 | +21.0% |

**Pre-reg (`by_frequency_desc`):** `pass_heuristic=True`
Bar: by_frequency_desc: ≥+10pp share_prefix_cached (overall or multi-doc) OR ≥20% multi-doc post_prefix reduction

Drops in `share_recurring_non_prefix` mean recurrence was absorbed into native prefix cache (C1) — not a G0 product failure.
