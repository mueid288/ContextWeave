# Phase 0A Demand Analysis (Gate G0)

- Trace: `/home/harborsoft/Mueid/ContextWeave/artifacts/cw-field-g0-2026-10-25-chunk2048/trace.jsonl`
- Requests: 3
- Provisional: **True**
- Gate G0: **PASS**
- Rationale: G0 PASS: unconstrained recurring non-prefix=65.3% (≥30%); median chunk=512 (≥512); LRU hit share=65.3% @ 128 GB (≥30% required). Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 12,543 |
| Served by native prefix cache | 0 (0.0%) |
| Post-prefix prefill tokens | 12,543 |
| Cold / uncovered system-prefix tokens | 249 |
| Recurring non-prefix tokens (unconstrained) | 8,192 (65.3% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 4,096 |
| Query tokens (post-prefix) | 6 |
| Post-prefix bucket sum (must match) | 12,543 |
| Median chunk length (tokens) | 512 |
| Synthesis request fraction | 100.0% |
| Requests ≥8k / ≥32k / ≥100k | 0.0% / 0.0% / 0.0% |
| Reuse distance (requests) | median=1, p90=1, mean=1.0 |

- Prefix-cache token budget: 183,105 (evictions=0)

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 12,543 |
| Post-prefix chunk tokens (diagnostic) | 12,288 |
| Hit tokens under budget | 8,192 (65.3% of post-prefix) |
| Hit share of chunks only | 66.7% |
| Miss tokens | 4,096 |
| Evictions | 0 |
| Peak resident | 0.54 GB |

### Context length buckets

- <8k: 3
- 8k-32k: 0
- 32k-100k: 0
- >=100k: 0

### Top-10 document popularity

- `2023f-mulbscs-223_B_6_docx::chunk-000`: 3
- `2023f-mulbscs-223_B_6_docx::chunk-001`: 3
- `Engagement-Metrics-Architecture-v3_docx_md::chunk-000`: 3
- `Engagement-Metrics-Architecture-v3_docx_md::chunk-006`: 3
- `Evidence-Based_Sleep_Quality_Optimization_md::chunk-000`: 3
- `Evidence-Based_Sleep_Quality_Optimization_md::chunk-001`: 3
- `contextweave_post_archive_review_md::chunk-000`: 3
- `contextweave_post_archive_review_md::chunk-001`: 3

## Interpretation

G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the declared GB budget also ≥ 30% (same post-prefix denominator).

Unconstrained recurrence is an upper bound; working-set hits are the decision metric for achievable cache value. Replace Path C / synthetic traces with a serving log before treating G0 as final.
