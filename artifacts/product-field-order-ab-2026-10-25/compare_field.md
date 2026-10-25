# Chunk-order compare — `artifacts/cw-field-g0-2026-10-25-field/trace.jsonl`

Requests: **27** (multi-doc ≥2 chunks: **27**)

## Overall `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens | recurring_non_prefix |
|---|---:|---:|---:|
| `natural` | 30.9% | 37,786 | 42.0% |
| `by_doc_id` | 30.9% | 37,786 | 42.0% |
| `by_sha256_doc_id` | 27.9% | 39,450 | 44.4% |
| `by_frequency_desc` | 36.6% | 34,698 | 36.8% |

## Multi-doc (`len(chunks)≥2`) `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens |
|---|---:|---:|
| `natural` | 30.9% | 37,786 |
| `by_doc_id` | 30.9% | 37,786 |
| `by_sha256_doc_id` | 27.9% | 39,450 |
| `by_frequency_desc` | 36.6% | 34,698 |

## Deltas vs `natural` (product KPIs)

| Mode | overall Δpp | overall post_prefix ↓% | multi-doc Δpp | multi-doc post_prefix ↓% |
|---|---:|---:|---:|---:|
| `by_doc_id` | +0.00 | +0.0% | +0.00 | +0.0% |
| `by_sha256_doc_id` | -3.04 | -4.4% | -3.04 | -4.4% |
| `by_frequency_desc` | +5.64 | +8.2% | +5.64 | +8.2% |

**Pre-reg (`by_frequency_desc`):** `pass_heuristic=False`
Bar: by_frequency_desc: ≥+10pp share_prefix_cached (overall or multi-doc) OR ≥20% multi-doc post_prefix reduction

Drops in `share_recurring_non_prefix` mean recurrence was absorbed into native prefix cache (C1) — not a G0 product failure.
