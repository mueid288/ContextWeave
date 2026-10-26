# Phase 0A Demand Analysis (Gate G0)

- Trace: `/Users/apple/Code/Context Weave/artifacts/cw-field-g0-kit-frequency/trace.jsonl`
- Requests: 15
- Provisional: **True**
- Gate G0: **FAIL**
- Rationale: G0 FAIL: median chunk 256 < 512. Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 13,337 |
| Served by native prefix cache | 5,952 (44.6%) |
| Post-prefix prefill tokens | 7,385 |
| Cold / uncovered system-prefix tokens | 96 |
| Recurring non-prefix tokens (unconstrained) | 3,072 (41.6% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 4,080 |
| Query tokens (post-prefix) | 137 |
| Post-prefix bucket sum (must match) | 7,385 |
| Median chunk length (tokens) | 256 |
| Synthesis request fraction | 66.7% |
| Requests ≥8k / ≥32k / ≥100k | 0.0% / 0.0% / 0.0% |
| Reuse distance (requests) | median=2, p90=7, mean=3.3 |

- Prefix-cache token budget: 183,105 (evictions=0)

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 7,385 |
| Post-prefix chunk tokens (diagnostic) | 7,152 |
| Hit tokens under budget | 3,072 (41.6% of post-prefix) |
| Hit share of chunks only | 43.0% |
| Miss tokens | 4,080 |
| Evictions | 0 |
| Peak resident | 0.53 GB |

### Context length buckets

- <8k: 15
- 8k-32k: 0
- 32k-100k: 0
- >=100k: 0

### Top-10 document popularity

- `contextweave_post_archive_review::chunk-012`: 10
- `contextweave_post_archive_review::chunk-000`: 9
- `contextweave-deep-review-v2::chunk-001`: 4
- `contextweave_post_archive_review::chunk-007`: 3
- `contextweave-deep-review-v2::chunk-005`: 3
- `contextweave_post_archive_review::chunk-004`: 3
- `contextweave-deep-review-v2::chunk-029`: 2
- `contextweave_post_archive_review::chunk-008`: 2
- `contextweave_post_archive_review::chunk-011`: 2
- `contextweave_post_archive_review::chunk-001`: 2

## Interpretation

G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the declared GB budget also ≥ 30% (same post-prefix denominator).

Unconstrained recurrence is an upper bound; working-set hits are the decision metric for achievable cache value. Replace Path C / synthetic traces with a serving log before treating G0 as final.
