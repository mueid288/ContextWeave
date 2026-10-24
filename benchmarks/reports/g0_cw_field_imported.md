# Phase 0A Demand Analysis (Gate G0)

- Trace: `benchmarks/workloads/cw_field_imported/trace.jsonl`
- Requests: 3
- Provisional: **True**
- Gate G0: **FAIL**
- Rationale: G0 FAIL: unconstrained share 11.0% < 30%; median chunk 250 < 512; working-set hit share 11.0% < 30% (budget=128 GB). Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 2,278 |
| Served by native prefix cache | 0 (0.0%) |
| Post-prefix prefill tokens | 2,278 |
| Cold / uncovered system-prefix tokens | 0 |
| Recurring non-prefix tokens (unconstrained) | 250 (11.0% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 2,000 |
| Query tokens (post-prefix) | 28 |
| Post-prefix bucket sum (must match) | 2,278 |
| Median chunk length (tokens) | 250 |
| Synthesis request fraction | 100.0% |
| Requests ≥8k / ≥32k / ≥100k | 0.0% / 0.0% / 0.0% |
| Reuse distance (requests) | median=1, p90=1, mean=1.0 |

- Prefix-cache token budget: 183,105 (evictions=0)

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 2,278 |
| Post-prefix chunk tokens (diagnostic) | 2,250 |
| Hit tokens under budget | 250 (11.0% of post-prefix) |
| Hit share of chunks only | 11.1% |
| Miss tokens | 2,000 |
| Evictions | 0 |
| Peak resident | 0.26 GB |

### Context length buckets

- <8k: 3
- 8k-32k: 0
- 32k-100k: 0
- >=100k: 0

### Top-10 document popularity

- `contextweave-deep-review-v2::chunk-029`: 2
- `contextweave_post_archive_review::chunk-007`: 1
- `contextweave_post_archive_review::chunk-008`: 1
- `contextweave_post_archive_review::chunk-012`: 1
- `contextweave-deep-review-v2::chunk-019`: 1
- `contextweave_post_archive_review::chunk-001`: 1
- `contextweave-deep-review-v2::chunk-007`: 1
- `contextweave_post_archive_review::chunk-003`: 1

## Interpretation

G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the declared GB budget also ≥ 30% (same post-prefix denominator).

Unconstrained recurrence is an upper bound; working-set hits are the decision metric for achievable cache value. Replace Path C / synthetic traces with a serving log before treating G0 as final.
