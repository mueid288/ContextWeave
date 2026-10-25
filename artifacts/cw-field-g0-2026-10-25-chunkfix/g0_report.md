# Phase 0A Demand Analysis (Gate G0)

- Trace: `/home/harborsoft/Mueid/ContextWeave/artifacts/cw-field-g0-2026-10-25-chunkfix/trace.jsonl`
- Requests: 17
- Provisional: **True**
- Gate G0: **FAIL**
- Rationale: G0 FAIL: median chunk 250 < 512. Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 15,507 |
| Served by native prefix cache | 0 (0.0%) |
| Post-prefix prefill tokens | 15,507 |
| Cold / uncovered system-prefix tokens | 1,411 |
| Recurring non-prefix tokens (unconstrained) | 8,250 (53.2% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 5,780 |
| Query tokens (post-prefix) | 66 |
| Post-prefix bucket sum (must match) | 15,507 |
| Median chunk length (tokens) | 250 |
| Synthesis request fraction | 100.0% |
| Requests ≥8k / ≥32k / ≥100k | 0.0% / 0.0% / 0.0% |
| Reuse distance (requests) | median=1, p90=3, mean=1.5 |

- Prefix-cache token budget: 183,105 (evictions=0)

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 15,507 |
| Post-prefix chunk tokens (diagnostic) | 14,030 |
| Hit tokens under budget | 8,250 (53.2% of post-prefix) |
| Hit share of chunks only | 58.8% |
| Miss tokens | 5,780 |
| Evictions | 0 |
| Peak resident | 0.76 GB |

### Context length buckets

- <8k: 17
- 8k-32k: 0
- 32k-100k: 0
- >=100k: 0

### Top-10 document popularity

- `g1_remaining_gaps_fixes_recommendations_md::chunk-000`: 7
- `g1_remaining_gaps_fixes_recommendations_md::chunk-001`: 6
- `contextweave_post_archive_review_md::chunk-000`: 4
- `contextweave_post_archive_review_md::chunk-001`: 4
- `Evidence-Based_Sleep_Quality_Optimization_md::chunk-000`: 4
- `Evidence-Based_Sleep_Quality_Optimization_md::chunk-038`: 4
- `Evidence-Based_Sleep_Quality_Optimization_md::chunk-039`: 4
- `g1_remaining_gaps_fixes_recommendations_md::chunk-004`: 2
- `g1_remaining_gaps_fixes_recommendations_md::chunk-006`: 2
- `g1_cacheblend_matched_image_runbook_md::chunk-000`: 2

## Interpretation

G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the declared GB budget also ≥ 30% (same post-prefix denominator).

Unconstrained recurrence is an upper bound; working-set hits are the decision metric for achievable cache value. Replace Path C / synthetic traces with a serving log before treating G0 as final.
