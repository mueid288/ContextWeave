# Phase 0A Demand Analysis (Gate G0)

- Trace: `/home/harborsoft/Mueid/ContextWeave/artifacts/cw-field-g0-2026-10-25/trace.jsonl`
- Requests: 82
- Provisional: **True**
- Gate G0: **FAIL**
- Rationale: G0 FAIL: median chunk 250 < 512. Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 64,669 |
| Served by native prefix cache | 7,957 (12.3%) |
| Post-prefix prefill tokens | 56,712 |
| Cold / uncovered system-prefix tokens | 4,565 |
| Recurring non-prefix tokens (unconstrained) | 25,634 (45.2% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 25,704 |
| Query tokens (post-prefix) | 809 |
| Post-prefix bucket sum (must match) | 56,712 |
| Median chunk length (tokens) | 250 |
| Synthesis request fraction | 98.8% |
| Requests ≥8k / ≥32k / ≥100k | 0.0% / 0.0% / 0.0% |
| Reuse distance (requests) | median=1, p90=8, mean=3.5 |

- Prefix-cache token budget: 183,105 (evictions=0)

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 56,712 |
| Post-prefix chunk tokens (diagnostic) | 51,338 |
| Hit tokens under budget | 25,634 (45.2% of post-prefix) |
| Hit share of chunks only | 49.9% |
| Miss tokens | 25,704 |
| Evictions | 0 |
| Peak resident | 3.37 GB |

### Context length buckets

- <8k: 82
- 8k-32k: 0
- 32k-100k: 0
- >=100k: 0

### Top-10 document popularity

- `Assignment_201::chunk-000`: 8
- `Assignment_201::chunk-001`: 8
- `Evaluating_TypeSafe_Jev_to_Reduce_AI_Costs_in_the_OpenClaw_Email_Order_Agent_pdf::chunk-000`: 7
- `BS-Computer-Science-3::chunk-000`: 6
- `Assignment_201_docx::chunk-000`: 6
- `Assignment_201_docx::chunk-001`: 6
- `Essentials_of_Plaint::chunk-000`: 5
- `Essentials_of_Plaint::chunk-003`: 5
- `Essentials_of_Plaint::chunk-004`: 5
- `Evaluating_TypeSafe_Jev_to_Reduce_AI_Costs_in_the_OpenClaw_Email_Order_Agent::chunk-002`: 5

## Interpretation

G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the declared GB budget also ≥ 30% (same post-prefix denominator).

Unconstrained recurrence is an upper bound; working-set hits are the decision metric for achievable cache value. Replace Path C / synthetic traces with a serving log before treating G0 as final.
