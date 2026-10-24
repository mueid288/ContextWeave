# Phase 0A Demand Analysis (Gate G0)

- Trace: `/home/harborsoft/Mueid/ContextWeave/artifacts/cw-field-g0-2026-10-24/trace.jsonl`
- Requests: 30
- Provisional: **True**
- Gate G0: **FAIL**
- Rationale: G0 FAIL: median chunk 250 < 512. Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 22,729 |
| Served by native prefix cache | 7,957 (35.0%) |
| Post-prefix prefill tokens | 14,772 |
| Cold / uncovered system-prefix tokens | 249 |
| Recurring non-prefix tokens (unconstrained) | 4,612 (31.2% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 9,649 |
| Query tokens (post-prefix) | 262 |
| Post-prefix bucket sum (must match) | 14,772 |
| Median chunk length (tokens) | 250 |
| Synthesis request fraction | 100.0% |
| Requests ≥8k / ≥32k / ≥100k | 0.0% / 0.0% / 0.0% |
| Reuse distance (requests) | median=1, p90=3, mean=2.1 |

- Prefix-cache token budget: 183,105 (evictions=0)

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 14,772 |
| Post-prefix chunk tokens (diagnostic) | 14,261 |
| Hit tokens under budget | 4,612 (31.2% of post-prefix) |
| Hit share of chunks only | 32.3% |
| Miss tokens | 9,649 |
| Evictions | 0 |
| Peak resident | 1.26 GB |

### Context length buckets

- <8k: 30
- 8k-32k: 0
- 32k-100k: 0
- >=100k: 0

### Top-10 document popularity

- `Assignment_201::chunk-000`: 8
- `Assignment_201::chunk-001`: 8
- `BS-Computer-Science-3::chunk-000`: 6
- `Essentials_of_Plaint::chunk-000`: 5
- `Essentials_of_Plaint::chunk-003`: 5
- `Essentials_of_Plaint::chunk-004`: 5
- `Muhammad_Faraz_Khan_CV__4_::chunk-001`: 4
- `2023f-mulbscs-223_B_6::chunk-000`: 3
- `2023f-mulbscs-223_B_6::chunk-001`: 3
- `Muhammad_Faraz_Khan_CV__4_::chunk-002`: 3

## Interpretation

G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the declared GB budget also ≥ 30% (same post-prefix denominator).

Unconstrained recurrence is an upper bound; working-set hits are the decision metric for achievable cache value. Replace Path C / synthetic traces with a serving log before treating G0 as final.
