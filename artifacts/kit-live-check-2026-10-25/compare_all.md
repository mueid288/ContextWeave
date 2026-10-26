# Chunk-order compare — `artifacts/kit-live-check-2026-10-25/partner_v1.jsonl`

Requests: **31** (multi-doc ≥2 chunks: **0**)

## Overall `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens | recurring_non_prefix |
|---|---:|---:|---:|
| `natural` | 0.0% | 0 | 0.0% |
| `by_doc_id` | 0.0% | 0 | 0.0% |
| `by_sha256_doc_id` | 0.0% | 0 | 0.0% |
| `by_frequency_desc` | 0.0% | 0 | 0.0% |

## Multi-doc (`len(chunks)≥2`) `share_prefix_cached`

| Mode | share_prefix_cached | post_prefix_tokens |
|---|---:|---:|
| `natural` | 0.0% | 0 |
| `by_doc_id` | 0.0% | 0 |
| `by_sha256_doc_id` | 0.0% | 0 |
| `by_frequency_desc` | 0.0% | 0 |

## Deltas vs `natural` (product KPIs)

| Mode | overall Δpp | overall post_prefix ↓% | multi-doc Δpp | multi-doc post_prefix ↓% |
|---|---:|---:|---:|---:|
| `by_doc_id` | +0.00 | +0.0% | +0.00 | +0.0% |
| `by_sha256_doc_id` | +0.00 | +0.0% | +0.00 | +0.0% |
| `by_frequency_desc` | +0.00 | +0.0% | +0.00 | +0.0% |

**Pre-reg (`by_frequency_desc`):** `pass_heuristic=False`
Bar: by_frequency_desc: ≥+10pp share_prefix_cached (overall or multi-doc) OR ≥20% multi-doc post_prefix reduction

Drops in `share_recurring_non_prefix` mean recurrence was absorbed into native prefix cache (C1) — not a G0 product failure.
