# Chunk-order compare — `benchmarks/workloads/my_corpus/trace.jsonl`

Requests: **300** (multi-doc ≥2 chunks: **153**)

## Overall `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens | recurring_non_prefix |
|---|---:|---:|---:|
| `natural` | 44.9% | 345,330 | 75.3% |
| `by_doc_id` | 52.5% | 297,698 | 71.3% |
| `by_sha256_doc_id` | 48.4% | 323,090 | 73.6% |
| `by_frequency_desc` | 53.9% | 288,882 | 70.4% |

## Multi-doc (`len(chunks)≥2`) `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens |
|---|---:|---:|
| `natural` | 30.8% | 313,775 |
| `by_doc_id` | 44.7% | 250,367 |
| `by_sha256_doc_id` | 37.1% | 285,087 |
| `by_frequency_desc` | 46.3% | 243,455 |

## Deltas vs `natural` (product KPIs)

| Mode | overall Δpp | overall post_prefix ↓% | multi-doc Δpp | multi-doc post_prefix ↓% |
|---|---:|---:|---:|---:|
| `by_doc_id` | +7.60 | +13.8% | +13.99 | +20.2% |
| `by_sha256_doc_id` | +3.55 | +6.4% | +6.33 | +9.1% |
| `by_frequency_desc` | +9.01 | +16.3% | +15.52 | +22.4% |

**Pre-reg (`by_frequency_desc`):** `pass_heuristic=True`
Bar: by_frequency_desc: ≥+10pp share_prefix_cached (overall or multi-doc) OR ≥20% multi-doc post_prefix reduction

Drops in `share_recurring_non_prefix` mean recurrence was absorbed into native prefix cache (C1) — not a G0 product failure.
