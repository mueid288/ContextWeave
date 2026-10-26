# Chunk-order compare — `artifacts/cw-field-g0-kit-frequency/trace.jsonl`

Requests: **15** (multi-doc ≥2 chunks: **15**)

## Overall `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens | recurring_non_prefix |
|---|---:|---:|---:|
| `natural` | 44.6% | 7,385 | 41.6% |
| `by_doc_id` | 52.3% | 6,361 | 32.2% |
| `by_sha256_doc_id` | 56.1% | 5,849 | 26.3% |
| `by_frequency_desc` | 61.9% | 5,081 | 15.1% |

## Multi-doc (`len(chunks)≥2`) `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens |
|---|---:|---:|
| `natural` | 44.6% | 7,385 |
| `by_doc_id` | 52.3% | 6,361 |
| `by_sha256_doc_id` | 56.1% | 5,849 |
| `by_frequency_desc` | 61.9% | 5,081 |

## Deltas vs `natural` (product KPIs)

| Mode | overall Δpp | overall post_prefix ↓% | multi-doc Δpp | multi-doc post_prefix ↓% |
|---|---:|---:|---:|---:|
| `by_doc_id` | +7.68 | +13.9% | +7.68 | +13.9% |
| `by_sha256_doc_id` | +11.52 | +20.8% | +11.52 | +20.8% |
| `by_frequency_desc` | +17.28 | +31.2% | +17.28 | +31.2% |

**Pre-reg (`by_frequency_desc`):** `pass_heuristic=True`
Bar: by_frequency_desc: ≥+10pp share_prefix_cached (overall or multi-doc) OR ≥20% multi-doc post_prefix reduction

Drops in `share_recurring_non_prefix` mean recurrence was absorbed into native prefix cache (C1) — not a G0 product failure.
