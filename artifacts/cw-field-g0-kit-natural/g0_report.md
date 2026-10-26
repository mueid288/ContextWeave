# Phase 0A Demand Analysis (Gate G0)

- Trace: `/Users/apple/Code/Context Weave/artifacts/cw-field-g0-kit-natural/trace.jsonl`
- Requests: 15
- Provisional: **True**
- Gate G0: **FAIL**
- Rationale: G0 FAIL: unconstrained share 19.2% < 30%; median chunk 256 < 512; working-set hit share 19.2% < 30% (budget=128 GB). Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 13,337 |
| Served by native prefix cache | 8,000 (60.0%) |
| Post-prefix prefill tokens | 5,337 |
| Cold / uncovered system-prefix tokens | 96 |
| Recurring non-prefix tokens (unconstrained) | 1,024 (19.2% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 4,080 |
| Query tokens (post-prefix) | 137 |
| Post-prefix bucket sum (must match) | 5,337 |
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
| Post-prefix prefill tokens (decision denom) | 5,337 |
| Post-prefix chunk tokens (diagnostic) | 5,104 |
| Hit tokens under budget | 1,024 (19.2% of post-prefix) |
| Hit share of chunks only | 20.1% |
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
- `contextweave_post_archive_review::chunk-004`: 3
- `contextweave-deep-review-v2::chunk-005`: 3
- `contextweave-deep-review-v2::chunk-029`: 2
- `contextweave_post_archive_review::chunk-011`: 2
- `contextweave_post_archive_review::chunk-008`: 2
- `contextweave_post_archive_review::chunk-001`: 2

## Interpretation

G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the declared GB budget also ≥ 30% (same post-prefix denominator).

Unconstrained recurrence is an upper bound; working-set hits are the decision metric for achievable cache value. Replace Path C / synthetic traces with a serving log before treating G0 as final.
